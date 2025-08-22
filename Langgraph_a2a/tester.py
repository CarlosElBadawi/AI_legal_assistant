import logging
from typing import Any
from uuid import uuid4
import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    EXTENDED_AGENT_CARD_PATH,
)


async def main() -> None:
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    base_url = 'http://localhost:10001'

    async with httpx.AsyncClient() as httpx_client:
        # Initialize resolver
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)

        # Fetch agent card
        final_agent_card_to_use: AgentCard | None = None
        try:
            _public_card = await resolver.get_agent_card()
            logger.info("Fetched public agent card")
            final_agent_card_to_use = _public_card
        except Exception as e:
            logger.error(f"Failed to fetch public agent card: {e}")
            raise

        # Initialize client
        client = A2AClient(httpx_client=httpx_client, agent_card=final_agent_card_to_use)
        logger.info("A2AClient initialized.")

        
        send_message_payload: dict[str, Any] = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": "how much is 10 USD in INR?"}],
                "message_id": uuid4().hex,
            }
        }

        request = SendMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**send_message_payload)
        )

       
        response = await client.send_message(request)

        
        normalized = {
            "role": "assistant",
            "parts": [{"kind": "text", "text": str(response)}],
            "message_id": uuid4().hex,
        }
        print("Standard Response:", normalized)

       
        streaming_request = SendStreamingMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**send_message_payload)
        )

        stream_response = client.send_message_streaming(streaming_request)

        async for chunk in stream_response:
            normalized_chunk = {
                "role": "assistant",
                "parts": [{"kind": "text", "text": str(chunk)}],
                "message_id": uuid4().hex,
            }
            print("Stream Chunk:", normalized_chunk)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
