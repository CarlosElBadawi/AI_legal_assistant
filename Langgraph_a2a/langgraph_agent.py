from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")



model =  ChatGoogleGenerativeAI(
    model="gemini-2.5-flash" 
)


client = MultiServerMCPClient(
    {
        "legal_tools_mcp": {
            "url": "http://localhost:8080/mcp/", 
            "transport": "streamable_http",
        }
    }
)

import asyncio

async def setup_tools_and_nodes():

    tools = await client.get_tools()

    model_with_tools = model.bind_tools(tools)


    tool_node = ToolNode(tools)
    return tools, model_with_tools, tool_node

tools, model_with_tools, tool_node = asyncio.run(setup_tools_and_nodes())


def should_continue(state: MessagesState):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END


async def call_model(state: MessagesState):
    messages = state["messages"]
    response = await model_with_tools.ainvoke(messages)
    return {"messages": [response]}

builder = StateGraph(MessagesState)
builder.add_node("call_model", call_model)
builder.add_node("tools", tool_node)

builder.add_edge(START, "call_model")
builder.add_conditional_edges("call_model", should_continue)
builder.add_edge("tools", "call_model")


graph = builder.compile()
# async def main():
#     response = await graph.ainvoke(
#         {"messages": [{"role": "user", "content": "Add 45 days to 2025-08-01."}]}
#     )
#     print(response)

# asyncio.run(main())
