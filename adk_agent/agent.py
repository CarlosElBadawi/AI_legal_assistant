from google.adk.agents import LlmAgent, Agent
from google.adk.tools import google_search
from google.adk.tools import agent_tool

import os
from langfuse import Langfuse

langfuse_client = Langfuse(
    public_key="pk-lf-2c86bd4d-6849-46a5-972f-31336b95e4a3",
    secret_key="sk-lf-f971db31-4f49-4954-bd34-e098a70cf94c",
    host="https://us.cloud.langfuse.com"
)

SearchAgent = LlmAgent(
    model="gemini-2.0-flash",
    name="SearchAgent",
    description="Searches the web when context is inadequate.",
    instruction="""
You are a focused web search specialist.
- Use the google_search tool to retrieve up-to-date, relevant legal information.
- Return a concise bundle of the most pertinent snippets with source titles and URLs.
- Prefer primary sources (statutes, regs, court opinions) and reputable secondary sources.
Output format:
- 'sources': bullet list with title and URL.
- 'snippets': short, high-signal quotes or paraphrases.
""",
    tools=[google_search],
    output_key="search_results",  # results placed into state["search_results"]
)


AnalyzerAgent = LlmAgent(
    model="gemini-2.0-flash",
    name="LegalAnalyzer",
    description="Classifies the user's request and proposes routing.",
    instruction="""
Classify the user request into EXACTLY ONE of:
- SUMMARIZE
- DRAFT_CLAUSE
- COMPLIANCE_CHECK

Also determine if existing context is adequate:
- If the conversation/state lacks domain grounding (e.g., no jurisdiction, no document excerpts),
  set needs_context=True, else False.

Write ONLY a concise JSON object to state["task_label_json"] with keys:
{
  "label": "<SUMMARIZE|DRAFT_CLAUSE|COMPLIANCE_CHECK>",
  "needs_context": <true|false>,
  "notes": "one brief sentence justifying the route"
}

YOU Always HAVE TO go to one of the three agents: ComplianceAgent, SummarizerAgent, or ClauseDrafterAgent.
NEVER let your response be the last, always call a sub-agent.

Guidance:
- If the user asks to "explain/summarize" a document → SUMMARIZE.
- If the user asks to "draft/propose clauses" → DRAFT_CLAUSE.
- If the user provides text to review/validate/cite → COMPLIANCE_CHECK.
""",
    output_key="task_label_json",
)


SummarizerAgent = LlmAgent(
    model="gemini-2.0-flash",
    name="LegalSummarizer",
    description="Summarizes legal documents in plain English.",
    instruction="""
You summarize legal text clearly and faithfully.
Inputs (if present):
- state["context"]: retrieved/RAG excerpts or user-provided text to summarize.
- state["user_query"]: the original user question.
- state["search_results"]: filled by SearchAgent if you request it.

Fallback behavior:
- If state["context"] is empty or < 50 chars, or Analyzer requested more context,
  CALL the SearchAgent using the embedded tool and place the result into the state,
  then incorporate it into your summary.

Output:
- Clear, structured summary with headings and bullet points.
- Neutral tone, accurate, non-speculative.
- Include a short "Citations & Sources" section using any available sources.

ALWAYS CALL the FormatterAgent sub agent after completing your summary.

Set the final summary text into state["summary"].
""",
    tools=[agent_tool.AgentTool(agent=SearchAgent)],
    output_key="summary",
)


ClauseDrafterAgent = LlmAgent(
    model="gemini-2.0-flash",
    name="ClauseDrafter",
    description="Drafts enforceable clauses tailored to the user's scenario.",
    instruction="""
You draft clear, enforceable legal clauses tailored to the user's scenario.

Inputs (if present):
- state["user_query"]: the drafting request (e.g., NDA clauses for a startup).
- state["context"]: any retrieved/RAG excerpts or constraints (jurisdiction, term, etc.).
- state["search_results"]: if SearchAgent was called.

Fallback behavior:
- If context is weak (missing governing law, jurisdiction, or relevant norms),
  CALL the SearchAgent. Use results to ground drafting choices (e.g., typical terms, statutory constraints).
- If jurisdiction is unspecified, propose a neutral baseline and mark jurisdiction placeholders.

Output requirements:
- Provide clauses with labels and short rationales.
- Parameterize where appropriate (e.g., [TERM_YEARS], [GOVERNING_LAW]).
- Add a brief "Assumptions & Variations" section.
- Include "Citations & Sources" when available.

ALWAYS CALL the FormatterAgent sub agent.

Write final drafted text into state["drafted_clauses"].

""",
    tools=[agent_tool.AgentTool(agent=SearchAgent)],
    output_key="drafted_clauses",
)

ComplianceAgent = LlmAgent(
    model="gemini-2.0-flash",
    name="ComplianceCiter",
    description="Validates drafts, flags issues, and attaches citations.",
    instruction="""
You validate legal drafts and attach citations.

Inputs:
- state["drafted_clauses"] if present; otherwise state["user_query"] may contain text to check.
- state["context"] for any provided legal materials.
- state["search_results"] for web-sourced context.

Fallback behavior:
- If citations are missing or weak, CALL the SearchAgent to obtain authoritative sources.
- Prefer primary sources (statutes, regulations, case law); fall back to reputable secondary sources.

Output:
- A "Compliance Report" with: Issues, Risk Level (Low/Med/High), and Fixes.
- A "Cited Authorities" section listing sources used.
- A "Revised Draft" reflecting fixes (if a draft was provided).

ALWAYS CALL the FormatterAgent sub agent.

Write your full compliance-checked output into state["compliance_checked"].
""",
    tools=[agent_tool.AgentTool(agent=SearchAgent)],
    output_key="compliance_checked",
)

FormatterAgent = LlmAgent(
    model="gemini-2.0-flash",
    name="LegalFormatter",
    description="Assembles the final response (summary or clauses + compliance) into polished output.",
    instruction="""
Assemble a polished final response.

Available state:
- state["task_label_json"]  (routing decision)
- state["summary"]          (if SUMMARIZE)
- state["drafted_clauses"]  (if DRAFT_CLAUSE)
- state["compliance_checked"] (if COMPLIANCE_CHECK or post-draft validation)

Rules:
- If label == SUMMARIZE → return state["summary"].
- If label == DRAFT_CLAUSE → include 'Drafted Clauses' and (if available) a short compliance note.
- If label == COMPLIANCE_CHECK → return the compliance report and revised draft.
- Always include a compact "Sources" section when present in state.

Format the output as a word document text.
Write the final text into state["final_answer"].
""",
    output_key="final_answer",
)


LegalSDK_Agent = LlmAgent(
    name="LegalSDK_Agent",
    model="gemini-2.0-flash",
    description="SDK-internal multi-agent legal assistant with web-search fallback.",
    instruction="""
You are the coordinator for the SDK-internal legal graph.

Flow:
1) Call LegalAnalyzer. Read state["task_label_json"].label and .needs_context.
2) Based on label:
   - SUMMARIZE → call LegalSummarizer.
   - DRAFT_CLAUSE → call ClauseDrafter, then optionally call ComplianceCiter to attach citations.
   - COMPLIANCE_CHECK → call ComplianceCiter.
3) Always finish by calling LegalFormatter to produce state["final_answer"].

Data passing:
- Keep the original user message in state["user_query"].
- If any helper reports weak/absent context, allow it to call SearchAgent.
- Never fabricate citations; prefer sources found by SearchAgent or provided context.

Output:
- Final user-facing answer should be in state["final_answer"].
""",
    sub_agents=[
        AnalyzerAgent,
    ],
)


AnalyzerAgent.sub_agents = [
    SummarizerAgent,
    ClauseDrafterAgent,
    ComplianceAgent,
]


for helper in [SummarizerAgent, ClauseDrafterAgent, ComplianceAgent]:
    helper.sub_agents = [FormatterAgent, SearchAgent]


from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.tools.agent_tool import AgentTool


lang_agent = RemoteA2aAgent(
    name="LegalAgent",
    description= "A multi-agent strategy pipeline that returns either context or a date or formats text into a docx document and checks jurisdiction."
                "Given a user goal or query, the graph (1) checks if the jurisdiction is valid,"
                "(2) uses RAG tools to get relevant context, (3) calculate dates"
                ", and (4) synthesizes a legal document and saves as a word document" 
                "Format the input as a dictionary. before feeding it to the tools",
                
    agent_card="http://localhost:10001/.well-known/agent.json"
)

orchestrator_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="adk_orchestrator_agent",
    instruction=("""""
        "ROLE: Orchestrator for a Legal Advisor workflow in ADK Web, You can never answer yourself to the question, always call one of your tools, but you have to choose which ones.\n"
        "YOU CAN CALL: root agent.\n"
        "END GOAL: By always relying on tools and tool agent.
    You are the Orchestrator Legal Agent. Your role is to coordinate tool and agent calls.

    PROCESS: You have access to 2 agents: lang_agent and LegalSDK_Agent. you can choose to call either or both agents
    1) Call lang_agent with the user's query.
    - The agent retrieves relevant legal documents or clauses via RAG.
    - The agent can calculate dates.
    - The agent can check jurisdiction.
    - The agent can format legal text into a word document.
      OR Call LegalSDK_Agent with the ORIGINAL_QUERY.
    - The agent can search the web.
    - The agent can draft clauses
    - The agent can summarize legal documents.
    - The agent can provide legal citations.

    2) Return a FINAL STRICT JSON with this schema:
    {
    "legal_issue": str,
    "original_query": str,
    "data_summary": {
        "highlights": list[str],
        "documents_used": list[str],
        "citations": list[str]
    },
    "adjusted_goals": list[str],
    "sources": [
        {"title": str, "url": str}
    ],
    "plan": str
    }

    RULES:
    - data_summary must only be filled using the output of legal_data_agent.
    - If no relevant documents are found, continue searching using web search
    and set data_summary.highlights = ["No internal legal documents available"].
    - plan must only be written by Yourself.
    - Always call on at least one of your tools (lang_agent or LegalSDK_Agent)"""),

)
orchestrator_agent.sub_agents = [LegalSDK_Agent, lang_agent]
root_agent = orchestrator_agent

from google.adk.a2a.utils.agent_to_a2a import to_a2a
a2a_app = to_a2a(root_agent, port=10001)


from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

from dotenv import load_dotenv
load_dotenv()
import asyncio
async def Runners(query : str):
    APP_NAME = "legal reviewer"
    root_agent = orchestrator_agent
    SESSION_CONFIG = {
        "user_id": "12345",
        "session_id": "123344"
    }
    USER_ID = "12345"
    SESSION_ID = "123344"

    # Session and Runner
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    runner = Runner(
        agent=orchestrator_agent, app_name=APP_NAME, session_service=session_service
    )



    new_message = types.Content(
        role="user", parts=[types.Part(text=query)]
    )

    session.state["user_query"] = query
    session.state["context"] = ""

    
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID, 
        new_message=new_message,
    ):
        final_response = ""
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response += event.content.parts[0].text
                session.state["final_answer"] = final_response



    print(final_response)
    return {"answer": final_response} 
if __name__ == "__main__":    
    while True:
        query = input("Enter query (or type 'exit' to quit): ")
        if query.lower() == "exit":
            break
        asyncio.run(Runners(query))

    