"""Main function orchestrator for the math_coding Azure Function app"""
import logging
import os
import json
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.monitor.opentelemetry import configure_azure_monitor


# Blueprint creation
bp = func.Blueprint()

_IS_INITIALIZED = False


def initialize_once():
    """Run startup code only once"""
    global _IS_INITIALIZED
    if not _IS_INITIALIZED:
        logging.info("Running startup initialization...")

        _IS_INITIALIZED = True


# Run initialization when module loads
initialize_once()


def enable_telemetry():
    """Enable telemetry logging"""
    # enable logging message contents
    os.environ["AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = "True"

    project = AIProjectClient.from_connection_string(
        conn_str=os.environ["CONNECTION_STRING"],
        credential=DefaultAzureCredential(),
    )

    application_insights_connection_string = project.telemetry.get_connection_string()

    if not application_insights_connection_string:
        logging.warning(
            "No app insights configured, telemetry will not be logged."
        )
    project.telemetry.enable()
    configure_azure_monitor(
        connection_string=application_insights_connection_string
        )
    logging.info("Enabled telemetry logging to project, view traces at:")


@bp.route(route="process-math-agent-semantic-kernel")
def process_math_agent_semantic_kernel(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP Trigger handler that coordinates the request/response flow
    and delegates business logic to pure_python_flow.py
    """
    try:
        # 1. Request handling
        enable_telemetry()
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
            logging.error("Failed to import pure_python_flow: %s", str(ie))
            return func.HttpResponse(
                body=json.dumps(
                    {"error": "Business logic module not available"}
                ),
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
    except ImportError as ie:
        logging.error("Import error: %s", str(ie))
        return func.HttpResponse(
            body=json.dumps({"error": "Internal server error"}),
            mimetype="application/json",
            status_code=500
        )
    except KeyError as ke:
        logging.error("Key error: %s", str(ke))
        return func.HttpResponse(
            body=json.dumps({"error": "Internal server error"}),
            mimetype="application/json",
            status_code=500
        )
