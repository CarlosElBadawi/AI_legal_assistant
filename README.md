# AI Legal Assistant

## 1. Project description
This project is an AI Legal Assistant. The tasks of this assistant are split into two models:  

### a. The ADK model
The ADK model can:  
- Summarize legal texts  
- Draft legal texts  
- Check compliance of clauses  
- Search the web for additional information  
- Format texts generated into a legal format  

To accurately choose between these tasks, an **analyzer agent** accepts a query and decides which of the first 3 agents to call and, based on if there is a need for more context, all three agents have access to the **web search tool**.  

After these agents are done, they must pass through the **Legal Formatter agent** so that the output of the model is up to standard.  

### b. The Langgraph model
The Langgraph model has a single agent that has access to multiple tools available through the **MCP server**, which contains the following tools:  
- **RAG tool**: reads a pdf and splits it into chunks (semantic chunking) and retrieves the most accurate chunks with relation to the question  
- **Policy comparator tool**: checks if a clause in a contract is compliant with the law  
- **Add days tool**: can add days to a specific date  
- **Jurisdiction checker tool**: checks if the specific city falls under its area of expertise  
- **Legal doc formatter tool**: formats and saves a text into a legal text in a `.docx` document  

To let these agents communicate, the **langgraph agent** was exposed using **a2a** and its agent card was called by the **adk agent**. Then an **orchestrator agent** was created to decide which model is more suited for the query at hand.  

---

## 2. Setup and Usage Instructions
To run and interact with the agents:  

1. Run the `server.py` file (**MCP**).  
2. Run the `__main__.py` file to expose the langgraph using **a2a**.  
   - Make sure to run each of these in a **dedicated terminal** since they both have to be running for the app to work.  

Then the next step depends on where you want to interact with the code.  
There are **3 ways of interacting with the agents**:  

### a. Command Prompt
Directly ask queries in the command prompt by running the `agent.py` on a dedicated terminal.  
- This method is primarily used if the user wants to create a docx file using the MCP tools.  

### b. ADK Web
Run the agents by running the command:  
```bash
adk web
```  
in the terminal of the `agent.py` and accessing it via the ADK UI.  
- This method is used to be able to pass pdf files (by the attach button) to be able to use RAG.  

### c. Gradio UI
Query the agent via the Gradio UI by running the `app.py` in a dedicated terminal.  

---

## 3. Issues and challenges faced

### RAG Models
- Started with **recursive chunking**, gave bad results → switched to **semantic chunking**  
- Embedding models:  
  - `all-MiniLM-L6-v2`: horrible accuracy  
  - `nlpaueb/legal-bert-base-uncased`: specialized in legal docs but had problems with downloading  
  - Final choice: `sentence-transformers/multi-qa-mpnet-base-dot-v1` → best avg similarity of **72%**  

- Retriever changes:  
  - From similarity score threshold = 0.5 → to **MMR with k=1**  
  - Limited results to 3 to avoid inaccuracies  

- Prompt changes:  
  - From:  
    > “Use the following context to answer the question”  
  - To:  
    > “Use the following context to answer the question, do not include any personal opinions or information, answer ONLY based on the context provided. If no context is available tell the user you don't know.  
    > If there are [] in the document especially if they are highlighted and in bold, consider them as filler for dates or numbers or names.”  

---

### MCP
- Tried the code from the session and added tools  
- Had issues connecting MCP server to Langgraph  
- Solved by switching to **Streamable-http transport**  

---

### A2A
- Huge difficulty finding working code, tested many repos  
- Repo structure was different → needed adjustments  
- Error encountered:  
  ```
  CompiledStateGraph is not callable
  ```  
  - Cause: In `main`, line `agent_executor=LegalAssistantExecutor()` was wrong  
  - Fix: Graph was already a compiledstategraph → should call as a **variable** (no parentheses)  

- Orchestrator issues:  
  - Tried binding agents as a tool → errors  
  - Passed them as **sub-agents** instead  
  - Prompt had to be changed multiple times until it worked (explicit mapping between tasks and agents was required)  

---

### API
- Faced problems connecting root agent to API  
- Needed terminal interaction (not only ADK web)  
- Fixed using a **Stack Overflow solution**  

---

### Gradio
- First attempt: built UI on top of API → bottleneck (10 min loading, no result)  
- Final fix: connected API to UI using **different ports**  

---

## References
- **RAG Outline**: session 10  
- **MCP Outline**: session 12  
- **Chunking**: [Mastering Document Chunking Strategies for RAG](https://medium.com/@sahin.samia/mastering-document-chunking-strategies-for-retrieval-augmented-generation-rag-c9c16785efc7)  
- **A2A**:  
  - [A2A Samples Repo](https://github.com/a2aproject/a2a-samples/tree/main/samples/python/agents/langgraph/app)  
  - [A2A Protocol Tutorial](https://a2a-protocol.org/latest/tutorials/python/7-streaming-and-multiturn/)  
- **FastAPI**:  
  - [AsyncIO AttributeError Fix](https://stackoverflow.com/questions/79715255/python-asyncio-attributeerror-coroutine-object-has-no-attribute-state-with)  
  - [FastAPI Path Params](https://fastapi.tiangolo.com/tutorial/path-params/)  
- **Gradio**:  
  - [Gradio API Page Guide](https://www.gradio.app/guides/view-api-page)  
  - [Gradio GitHub Issue #1608](https://github.com/gradio-app/gradio/issues/1608)  
