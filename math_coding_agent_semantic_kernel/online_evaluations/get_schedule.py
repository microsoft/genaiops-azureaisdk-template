"""Online Evaluation script for math_coding."""
import os
import argparse
import yaml
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

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

    # Connect to your Azure AI Studio Project
    project_client = AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(),
        conn_str=f"{os.environ['CONNECTION_STRING']}"
    )

    schedule = project_client.evaluations.get_schedule(data["schedule_name"])
    print("Schedule: ", schedule)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("config_parameters")
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
