import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from agent import Runners  # your agent entrypoint
import httpx 
import gradio as gr 

app = FastAPI()

class Prompt(BaseModel):
    text: str

@app.post("/run")
async def run_agent_endpoint(prompt: Prompt):
    
    return  await Runners(prompt.text)
async def call_backend(prompt: str):
    """Send the user prompt to FastAPI /run."""
    async with httpx.AsyncClient() as client:
        resp = await client.post("http://localhost:9090/run", json={"text": prompt})
        return resp.json().get("answer", "No response")

def gradio_wrapper(prompt: str):
    
    return asyncio.run(call_backend(prompt))

iface = gr.Interface(
    fn=gradio_wrapper,
    inputs="text",
    outputs="text",
    title="Legal Reviewer"
)


if __name__ == "__main__":
    iface.launch(server_port=7860) 