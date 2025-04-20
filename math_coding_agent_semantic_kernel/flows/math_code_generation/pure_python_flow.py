"""Orchestation script for math_coding agent with semantic kernel and Azure AI Agents."""
import json
import os
import asyncio
from typing import Any, Dict, List
from dotenv import load_dotenv
from azure.ai.inference.prompts import PromptTemplate
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import CodeInterpreterTool
from azure.ai.projects import AIProjectClient
from semantic_kernel.agents.azure_ai import AzureAIAgent, AzureAIAgentSettings
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace

creds = DefaultAzureCredential()
project_client = AIProjectClient.from_connection_string(
    credential=creds, conn_str=os.environ["CONNECTION_STRING"]
)

# Enable Azure Monitor tracing
application_insights_connection_string = project_client.telemetry.get_connection_string()

if not application_insights_connection_string:
    print("Application Insights was not enabled for this project.")
    print("Enable it via the 'Tracing' tab in your AI Foundry project page.")
    exit()

configure_azure_monitor(connection_string=application_insights_connection_string)

scenario = os.path.basename(__file__)
tracer = trace.get_tracer(__name__)


def simplify_message(msg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplify a message dictionary by flattening nested structures and removing empty fields.

    Args:
        msg: Dictionary containing message data with potentially nested structures

    Returns:
        Dictionary with flattened structure suitable for JSON serialization
    """
    # Create a new dict with basic fields
    simplified = {
        'id': msg.get('id'),
        'object': msg.get('object'),
        'created_at': str(msg.get('created_at')),
        'assistant_id': msg.get('assistant_id', ""),
        'thread_id': msg.get('thread_id'),
        'run_id': msg.get('run_id'),
        'role': msg.get('role'),
    }

    # Extract content text from nested structure
    content = msg.get('content', [])
    if content and isinstance(content, list) and len(content) > 0:
        text_content = content[0].get('text', {})
        simplified['content_text'] = text_content.get('value', '')
    else:
        simplified['content_text'] = ''

    # Remove None values
    simplified = {k: v for k, v in simplified.items() if v is not None}

    return simplified


def convert_and_serialize(data: List[Dict[str, Any]]) -> str:
    """
    Convert a list of message dictionaries to a simplified format and serialize to JSON.

    Args:
        data: List of message dictionaries

    Returns:
        JSON string of simplified data
    """
    simplified_data = [simplify_message(msg) for msg in data.data]
    return json.dumps(simplified_data)


async def get_math_response(question):
    """Get the response for the math question"""
    prompty_file = os.environ["PROMPTY_FILE"]
    path = f"./{prompty_file}"
    prompt_template = PromptTemplate.from_prompty(file_path=path)

    messages = prompt_template.create_messages(question=question)

    message_input = " ".join([json.dumps(entry) for entry in messages])
    ai_agent_settings = AzureAIAgentSettings.create()

    client = AzureAIAgent.create_client(
        credential=creds,
        conn_str=ai_agent_settings.project_connection_string.get_secret_value(),
    )

    code_interpreter = CodeInterpreterTool()

    agent_definition = await client.agents.create_agent(
        model=ai_agent_settings.model_deployment_name,
        tools=code_interpreter.definitions,
        tool_resources=code_interpreter.resources,
        instructions=message_input,
        name="math-agent",
    )

    # Create the AzureAI Agent
    agent = AzureAIAgent(
        client=client,
        definition=agent_definition,
    )

    # Create a new thread
    thread = await client.agents.create_thread()

    message = await agent.add_chat_message(
        thread_id=thread.id, message=ChatMessageContent(role=AuthorRole.USER, content=question)
    )

    last_message = None
    messages = agent.invoke(thread_id=thread.id)
    async for content in messages:
        print(f"## Agent: {content}")
        if content.role == AuthorRole.ASSISTANT:
            last_message = content.content
     
    if last_message is not None:
        print(f"# last_message: {last_message}")
    else:
        print("No assistant messages found.")

    messages = await client.agents.list_messages(thread_id=thread.id)

    await client.agents.delete_thread(thread.id)
    await client.agents.delete_agent(agent.id)
    return {
        "response": last_message,
        "full_output": convert_and_serialize(messages)
    }


if __name__ == "__main__":
    # Test the math response
    load_dotenv()
    QUESTION = "Find (24^{-1} pmod{11^2})?"
    result = asyncio.run(get_math_response(QUESTION))
    print(result)
