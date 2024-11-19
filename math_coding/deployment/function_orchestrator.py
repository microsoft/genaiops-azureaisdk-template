import logging
import os
import azure.functions as func
import json
from typing import Dict, Any
from azure.core.settings import settings
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.inference.tracing import AIInferenceInstrumentor

# Blueprint creation
bp = func.Blueprint()


# Enable instrumentation and logging of telemetry to the project
def enable_telemetry(log_to_project: bool = False):
    settings.tracing_implementation = "opentelemetry"
    AIInferenceInstrumentor().instrument()

    # enable logging message contents
    os.environ["AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = log_to_project

    if log_to_project:
        from azure.monitor.opentelemetry import configure_azure_monitor

        project = AIProjectClient.from_connection_string(
            conn_str=os.environ["CONNECTION_STRING"], credential=DefaultAzureCredential()
        )
        tracing_link = f"https://ai.azure.com/tracing?wsid=/subscriptions/{project.scope[os.environ['SUBSCRIPTION_ID']]}/resourceGroups/{project.scope[os.environ['RESOURCE_GROUP_NAME']]}/providers/Microsoft.MachineLearningServices/workspaces/{project.scope[os.environ['PROJECT_NAME']]}"
        application_insights_connection_string = project.telemetry.get_connection_string()
        if not application_insights_connection_string:
            logging.warning(
                "No application insights configured, telemetry will not be logged to project. Add application insights at:"
            )
            logging.warning(tracing_link)

            return

        configure_azure_monitor(connection_string=application_insights_connection_string)
        logging.info("Enabled telemetry logging to project, view traces at:")
        logging.info(tracing_link)    


if os.environ["ENABLE_TELEMETRY"]
  enable_telemetry(os.environ["ENABLE_TELEMETRY"])


@bp.route(route="process-math")
def process_math(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP Trigger handler that coordinates the request/response flow
    and delegates business logic to pure_python_flow.py
    """
    try:
        # 1. Request handling
        question = req.params.get('question')
        
        # 2. Input validation
        if not question:
            return func.HttpResponse(
                body=json.dumps({"error": "Request body is required"}),
                mimetype="application/json",
                status_code=400
            )

        # 3. Import and execute business logic
        try:
            from . import pure_python_flow
            result = pure_python_flow.get_math_response(question)
        except ImportError as ie:
            logging.error(f"Failed to import pure_python_flow: {str(ie)}")
            return func.HttpResponse(
                body=json.dumps({"error": "Business logic module not available"}),
                mimetype="application/json",
                status_code=500
            )

        # 4. Response handling
        return func.HttpResponse(
            body=json.dumps(result),
            mimetype="application/json",
            status_code=200
        )

    except ValueError as ve:
        return func.HttpResponse(
            body=json.dumps({"error": f"Invalid request format: {str(ve)}"}),
            mimetype="application/json",
            status_code=400
        )
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "Internal server error"}),
            mimetype="application/json",
            status_code=500
        )

