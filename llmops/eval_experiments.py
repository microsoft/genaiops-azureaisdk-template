"""Experiment evaluation module."""
import argparse
import asyncio
import datetime
import importlib
import inspect
import os
import re
import sys
from typing import Dict, Optional
import logging
import requests
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from llmops.experiment import load_experiment

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        # Log to console
        logging.StreamHandler(),
        # Also log to a file, keeping track of all runs
        logging.FileHandler('experiment_execution.log')
    ]
)
logger = logging.getLogger(__name__)


def extract_run_id(url):
    """Extract run ID from Azure ML studio URL."""
    match = re.search(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', url)
    return match.group(0) if match else None


def update_run_tags(
    subscription_id: str,
    resource_group_name: str,
    workspace_name: str,
    workspace_location: str,
    run_id: str,
    tags: Dict[str, str],
    credential: Optional[object] = None
):
    """Workaround to update tags since the SDK is not supporting it yet."""
    try:
        if credential is None:
            credential = DefaultAzureCredential()

        token = credential.get_token("https://management.azure.com/.default").token

        url = (f"https://{workspace_location}.api.azureml.ms/history/v1.0"
               f"/subscriptions/{subscription_id}"
               f"/resourceGroups/{resource_group_name}"
               f"/providers/Microsoft.MachineLearningServices"
               f"/workspaces/{workspace_name}"
               f"/runs/{run_id}")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "tags": tags
        }

        response = requests.patch(url, headers=headers, json=payload)

        if response.status_code != 200:
            raise RuntimeError(f"API request failed with status {response.status_code}: {response.text}")
        logger.info("Successfully updated tags for run ID: %s", run_id)

    except Exception as e:
        logger.error("Failed to update run tags: %s", str(e))


def set_environment_variables(env_dict):
    """
    Set environment variables from a dictionary.

    Args:
        env_dict (dict): Dictionary for env variable names and values
    """
    for key, value in env_dict.items():
        os.environ[key] = str(value)


def prepare_and_execute(
    exp_filename: Optional[str] = None,
    base_path: Optional[str] = None,
    env_name: Optional[str] = None,
    report_dir: Optional[str] = None,
    eval_to_exec: Optional[str] = "*",
):
    """Prepare and execute the evaluations for the given experiment."""
    load_dotenv(override=True)
    logger.debug("Environment variables loaded")

    results = []

    try:
        experiment = load_experiment(
            filename=exp_filename, base_path=base_path, env=env_name
        )
        experiment_name = experiment.name
        logger.info("Loaded experiment: %s", experiment.name)

        eval_flows = experiment.evaluators
        logger.info("Found %d evaluators to process", len(eval_flows))

        set_environment_variables(experiment.resolved_env_vars)
        logger.debug("Set experiment-level environment variables")

        if report_dir:
            if not os.path.exists(report_dir):
                logger.info("Creating report directory: %s", report_dir)
                os.makedirs(report_dir, exist_ok=True)

        for evaluator in eval_flows:
            logger.info("Processing evaluator: %s", evaluator.name)

            if eval_to_exec not in ["*", evaluator.name]:
                logger.info("Evaluator could not be processed: %s", evaluator.name)
                continue
            else:
                evaluator_path = os.path.join(
                    base_path, evaluator.flow
                )
                logger.debug("Evaluator path: %s", evaluator_path)
                evaluator.resolve_variables()

                set_environment_variables(evaluator.resolved_env_vars)
                logger.debug("Set evaluator-specific environment variables")

                try:
                    logger.debug(
                        "PROMPTY_FILE value: %s", os.environ.get(
                            'PROMPTY_FILE'
                            )
                    )
                except KeyError:
                    logger.warning("PROMPTY_FILE environment variable not set")
                    raise

                service_module = None
                eval_filename = evaluator.name + ".py"

                if os.path.isfile(os.path.join(evaluator_path, eval_filename)):
                    logger.info("Found evaluation file: %s", eval_filename)
                    module_name = evaluator.name.lstrip().rstrip()
                    flow_components = evaluator_path.split(os.sep)
                    flow_formatted = '.'.join(flow_components)
                    module_path = (
                        f'{flow_formatted}.'
                        f'{module_name}'
                    )

                    dependent_modules_dir = os.path.join(
                        base_path, experiment.flow
                        )
                    logger.debug("Adding to sys.path: %s", dependent_modules_dir)
                    sys.path.append(dependent_modules_dir)

                    # evaluations folder
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    parent_dir = os.path.dirname(current_dir)

                    logger.debug("Adding to sys.path: %s", parent_dir)
                    sys.path.insert(0, parent_dir)

                    logger.info("Importing module: %s", module_path)
                    service_module = importlib.import_module(
                        module_path
                        )

                    module_names = dir(service_module)

                    # Filter names to get functions defined in module
                    function_names = [
                        name for name in module_names
                        if inspect.isfunction
                        (
                            getattr(
                                service_module,
                                name
                                )
                            )
                        ]
                    logger.debug("Found %d functions in module", len(
                        function_names
                        )
                    )

                    for function_name in function_names:
                        if (
                            function_name.lower().startswith('eval_')
                        ):
                            logger.info(
                                "Executing evaluation function: %s", function_name
                            )
                            service_function = getattr(
                                service_module,
                                function_name
                                )
                            for ds in evaluator.datasets:
                                logger.info("Processing dataset: %s", ds.source)

                                timestamp = datetime.datetime.now().strftime(
                                    "%Y%m%d_%H%M%S"
                                    )
                                eval_id = f"{experiment_name}_eval_{timestamp}"

                                if inspect.iscoroutinefunction(service_function):
                                    logger.debug(
                                        "Executing async evaluation function"
                                    )
                                    result = asyncio.run(service_function(
                                        eval_id,
                                        os.path.join(base_path, ds.source),
                                        ds.mappings,
                                        report_dir
                                    ))
                                else:
                                    logger.debug(
                                        "Executing sync evaluation function"
                                    )
                                    result = service_function(
                                        eval_id,
                                        os.path.join(
                                            base_path,
                                            ds.source
                                        ),
                                        ds.mappings,
                                        report_dir
                                    )
                                logger.info(
                                    "Evaluation completed successfully: %s", result
                                )
                                results.append(result)
                else:
                    print(f"No evaluation flow found for {evaluator.name}")

        return results
    except Exception as e:
        print(f"Evaluation failed: {str(e)}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser("config_parameters")
    parser.add_argument(
        "--environment_name",
        type=str,
        required=True,
        help="env name (dev, test, prod) etc",
    )
    parser.add_argument(
        "--base_path",
        type=str,
        required=True,
        help="use case folder path",
    )
    parser.add_argument(
        "--report_dir",
        type=str,
        required=True,
        help="output folder path",
    )
    parser.add_argument(
        "--experiment_config_file",
        type=str,
        help="experiment config file name",
    )

    parser.add_argument(
        "--eval_to_exec",
        type=str,
        help="experiment config file name",
        default="*"
    )
    args = parser.parse_args()

    project = None
    if os.environ.get("AZURE_AI_PROJECT_CONNECTION_STRING"):
        project = AIProjectClient.from_connection_string(
            conn_str=os.environ["AZURE_AI_PROJECT_CONNECTION_STRING"],
            credential=DefaultAzureCredential()
        )

    results = prepare_and_execute(
        exp_filename=args.experiment_config_file,
        base_path=args.base_path,
        env_name=args.environment_name,
        report_dir=args.report_dir,
        eval_to_exec=args.eval_to_exec,
    )

    # Workaround: Apply tags to evaluation runs until SDK supports tagging natively
    if project and results:
        for res in results:
            try:
                if ("result" in res and "rows" in res["result"] and 
                    len(res["result"]["rows"]) > 0 and
                    "studio_url" in res["result"]):
                    
                    evaluation_tags = {}  # Add custom tags here as needed
                    
                    if "outputs" in res["result"]["rows"][0]:
                        outputs = res["result"]["rows"][0]["outputs"]
                        if isinstance(outputs, dict) and "model" in outputs:
                            evaluation_tags["model"] = outputs["model"]
                        elif hasattr(outputs, 'model'):
                            evaluation_tags["model"] = outputs.model

                    run_id = extract_run_id(res["result"]["studio_url"])
                    if run_id:
                        workspace_scope = project.scope
                        update_run_tags(
                            workspace_scope["subscription_id"],
                            workspace_scope["resource_group_name"],
                            workspace_scope["project_name"],
                            "eastus2",
                            run_id,
                            evaluation_tags
                        )
                    else:
                        logger.warning("Could not extract run ID from studio URL")
            except Exception as e:
                logger.error("Failed to apply tags to result: %s", str(e))
    else:
        if not project:
            logger.info("Azure AI Project Client not initialized - skipping tagging")
        if not results:
            logger.info("No results to tag")
