
import logging
import os
import sys

import click
import httpx
import uvicorn
from dotenv import load_dotenv

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from langgraph_agent import  graph as LegalAssistantAgent
from lanatoa import LegalAssistantExecutor

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10001)
def main(host, port):
    """Starts the Legal Assistant Agent server."""
    try:
        if not os.getenv('GOOGLE_API_KEY'):
            raise MissingAPIKeyError(
                'GOOGLE_API_KEY environment variable not set.'
            )

        # Define capabilities and skills
        capabilities = AgentCapabilities(streaming=True, push_notifications=True)
        skill = AgentSkill(
            id='legal_advice',
            name='Legal Assistant Tool',
            description='Provides legal guidance by using a pdf document as a reference, or by comparing legal texts, or by checking jurisdiction, or by formatting a text into a legal word document.',
            tags=['legal', 'compliance', 'guidance'],
            examples=['What are the sick days policies in this contract?'],
        )
        agent_card = AgentCard(
            name='Legal Assistant Agent',
            description='Helps users with legal queries and advice',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            default_input_modes=["text"],
            default_output_modes=["text"],
            capabilities=capabilities,
            skills=[skill],
        )

        # --8<-- [start:DefaultRequestHandler]
        httpx_client = httpx.AsyncClient()
        push_config_store = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(
            httpx_client=httpx_client,
            config_store=push_config_store
        )
        try:
            request_handler = DefaultRequestHandler(
                agent_executor=LegalAssistantExecutor(),
                task_store=InMemoryTaskStore(),
                push_config_store=push_config_store,
                push_sender=push_sender
            )
        except Exception as e:
            logger.error(f'Error initializing request handler: {e}')
            sys.exit(1)

        server = A2AStarletteApplication(
            agent_card=agent_card,
            http_handler=request_handler
        )

        uvicorn.run(server.build(), host=host, port=port)
        # --8<-- [end:DefaultRequestHandler]

    except MissingAPIKeyError as e:
         logger.error(f'Error: {e}')
         sys.exit(1)
    except Exception as e:
         logger.error(f'An error occurred during server startup: {e}')
         sys.exit(1)


if __name__ == '__main__':
    main()
