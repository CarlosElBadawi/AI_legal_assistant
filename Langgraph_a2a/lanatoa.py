
import logging
from uuid import uuid4

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_task, new_agent_text_message
from a2a.utils.errors import ServerError
from langgraph_agent import graph as LegalAssistantAgent  

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LegalAssistantExecutor(AgentExecutor):
    """A2A Executor wrapper for your LangGraph Legal Assistant."""

    def __init__(self):
        agent_instance = LegalAssistantAgent  
        self.agent = agent_instance  

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Validate the request
        if self._validate_request(context):
            raise ServerError(error=InvalidParamsError())

        user_input_text = context.get_user_input()
        query_dict = {
            "messages": [
                {
                    "role": "user",
                    "content": user_input_text, 
                }
            ]
        }
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)
        def extract_text(content):
            if isinstance(content, str):
                return content
            elif isinstance(content, dict):
               
                for key in ["text", "content", "message"]:
                    if key in content and isinstance(content[key], str):
                        return content[key]
                
                return str(content)
            else:
                return str(content)

        try:

            
            result = await self.agent.ainvoke(query_dict)
            
            item = {
                "content": result,
                "is_task_complete": True,
                "require_user_input": False,
            }
            await updater.add_artifact(
                [Part(root=TextPart(text=extract_text(item["content"])))],
                name="legal_response",
            )
            await updater.complete()

        except Exception as e:
            logger.error(f"Error while streaming response: {e}", exc_info=True)
            raise ServerError(error=InternalError()) from e

    def _validate_request(self, context: RequestContext) -> bool:
      
        return False

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise ServerError(error=UnsupportedOperationError())
