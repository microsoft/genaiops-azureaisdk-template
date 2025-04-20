"""Online Evaluation script for math_coding."""
import os
import argparse
import yaml

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import (
    ApplicationInsightsConfiguration,
    EvaluatorConfiguration,
    EvaluationSchedule,
    RecurrenceTrigger,
    ConnectionType
)

from dotenv import load_dotenv


def prepare_and_execute(
    base_path
):
    """
    Prepare and execute the online evaluation schedule.
    """
    load_dotenv()

    with open(
        f'{base_path}/online_evaluation_config.yaml', 'r', encoding='utf-8'
    ) as file:
        data = yaml.safe_load(file)

    # Name of your online evaluation schedule
    SCHEDULE_NAME = data["schedule_name"]

    # Name of your gen AI app (will be available in trace data in app insights)
    SERVICE_NAME = data["service_name"]

    # Your Application Insights resource ID
    APPLICATION_INSIGHTS_RESOURCE_ID = (
        f"/subscriptions/{os.environ['SUBSCRIPTION_ID']}/resourceGroups/"
        f"{os.environ['RESOURCE_GROUP_NAME']}/providers/microsoft.insights/components/"
        f"{data['app_insights_name']}"
    )

    # Kusto Query Language (KQL) query to query data
    # from Application Insights resource
    # This query is compatible with data logged by the Azure AI Inferencing
    # Tracing SDK (linked in documentation)
    # You can modify it depending on your data schema
    # The KQL query must output these required columns:
    # operation_ID, operation_ParentID, and gen_ai_response_id
    # You can choose which other columns to output
    # as required by the evaluators you are using
    KUSTO_QUERY = (
        "let gen_ai_spans=(dependencies | where isnotnull(customDimensions[\"gen_ai.system\"]) "
        "| extend response_id = tostring(customDimensions[\"gen_ai.response.id\"]) "
        "| project id, operation_Id, operation_ParentId, timestamp, response_id); "
        "let gen_ai_events=(traces | where message in (\"gen_ai.choice\", \"gen_ai.user.message\", "
        "\"gen_ai.system.message\") or tostring(customDimensions[\"event.name\"]) in (\"gen_ai.choice\", "
        "\"gen_ai.user.message\", \"gen_ai.system.message\") | project id= operation_ParentId, operation_Id, "
        "operation_ParentId, user_input = iff(message == \"gen_ai.user.message\" or "
        "tostring(customDimensions[\"event.name\"]) == \"gen_ai.user.message\", parse_json(iff(message == "
        "\"gen_ai.user.message\", tostring(customDimensions[\"gen_ai.event.content\"]), message)).content, \"\"), "
        "system = iff(message == \"gen_ai.system.message\" or tostring(customDimensions[\"event.name\"]) == "
        "\"gen_ai.system.message\", parse_json(iff(message == \"gen_ai.system.message\", "
        "tostring(customDimensions[\"gen_ai.event.content\"]), message)).content, \"\"), llm_response = iff(message == "
        "\"gen_ai.choice\", parse_json(tostring(parse_json(tostring(customDimensions[\"gen_ai.event.content\"]))"
        ".message)).content, iff(tostring(customDimensions[\"event.name\"]) == \"gen_ai.choice\", "
        "parse_json(parse_json(message).message).content, \"\")) | summarize operation_ParentId = any(operation_ParentId), "
        "Input = maxif(user_input, user_input != \"\"), System = maxif(system, system != \"\"), Output = maxif(llm_response, "
        "llm_response != \"\") by operation_Id, id); gen_ai_spans | join kind=inner (gen_ai_events) on id, operation_Id | "
        "project Input, System, Output, operation_Id, operation_ParentId, gen_ai_response_id = response_id"
    )

    # Connect to your Azure AI Studio Project
    project_client = AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(),
        conn_str=f"{os.environ['CONNECTION_STRING']}"
    )
    application_insights_connection_string = project_client.telemetry.get_connection_string()

    if not application_insights_connection_string:
        print("no application insight configured")

    # Connect to your Application Insights resource
    app_insights_config = ApplicationInsightsConfiguration(
        resource_id=APPLICATION_INSIGHTS_RESOURCE_ID,
        query=KUSTO_QUERY,
        service_name=SERVICE_NAME
    )

    # Connect to your AOAI resource, you must use an AOAI GPT model
    deployment_name = data["deployment_name"]
    api_version = data["deployment_api_version"]

    # This is your llm connection name from AI Studio project
    default_connection = project_client.connections.get_default(
        connection_type=ConnectionType.AZURE_OPEN_AI
    )

    model_config = {
        "azure_deployment": deployment_name,
        "api_version": api_version,
        "type": "azure_openai",
        "azure_endpoint": default_connection.endpoint_url
    }

    # Configure your evaluators
    # RelevanceEvaluator
    # id for each evaluator can be found in your AI Studio registry
    # init_params is the configuration for the model
    # to use to perform the evaluation
    # data_mapping is used to map the output columns of your query
    # to the names required by the evaluator
    relevance_evaluator_config = EvaluatorConfiguration(
        id=(
            "azureml://registries/azureml-staging/models/"
            "Relevance-Evaluator/versions/4"
        ),
        init_params={"model_config": model_config},
        data_mapping={"query": "${data.Input}", "response": "${data.Output}"}
    )

    # Frequency to run the schedule
    recurrence_trigger = RecurrenceTrigger(frequency="day", interval=1)

    # Dictionary of evaluators
    evaluators = {
        "relevance": relevance_evaluator_config
    }

    name = SCHEDULE_NAME
    description = f"{SCHEDULE_NAME} description"
    # AzureMSIClientId is the clientID of the User-assigned managed identity
    properties = {"AzureMSIClientId": os.environ["USER_CLIENT_ID"]}

    # Configure the online evaluation schedule
    evaluation_schedule = EvaluationSchedule(
        data=app_insights_config,
        evaluators=evaluators,
        trigger=recurrence_trigger,
        description=description,
        properties=properties)

    # Create the online evaluation schedule
    evaluation_schedule = project_client.evaluations.create_or_replace_schedule(
        name,
        evaluation_schedule,
    )
    print(evaluation_schedule)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("config_parameters")
    parser.add_argument(
        "--environment_name",
        type=str,
        required=True,
        help="env_name from config.yaml",
    )
    parser.add_argument(
        "--base_path",
        type=str,
        required=True,
        help="use case folder path",
    )
    args = parser.parse_args()

    prepare_and_execute(
        base_path=args.base_path
    )
