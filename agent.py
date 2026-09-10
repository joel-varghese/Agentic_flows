from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph,START,END
from langgraph.prebuilt import tools_condition
from langgraph.graph.message import add_messages 
from langchain_core.tools import tool
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_tavily import TavilySearch
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from gmail_tools import send_email_tool
from drive_tools import search_and_download_doc_tool
from calendar_tools import create_calendar_event_tool
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


# ==================== LOAD ENV =======================
# memory = MemorySaver()

load_dotenv()
base_model = "openai/gpt-oss-120b"
api = os.getenv("GROQ_API_KEY")
tavily = os.getenv("TAVILY_API")

# ==================== LLM =======================
llm = ChatGroq(
    api_key = api,
    model = base_model,
    temperature=0.3
)

# ==================== TOOL =======================

    
tools = [search_and_download_doc_tool, send_email_tool, create_calendar_event_tool]
llm_with_tools = llm.bind_tools(tools)

# ==================== STATE =======================
class State(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str



# ==================== NODES =======================

def chatbot(state:State):
    response = llm_with_tools.invoke([
    SystemMessage(content="""
    You are an AI assistant with access to tools.

    Available tools:

    1. send_email_tool
    → Send an email using the user's connected Gmail account.

    2. search_and_download_doc_tool
    → Find or download documents from the user's Google Drive.

    3. create_calendar_event_tool
    → Create events using the user's Google Calendar.

    Rules:

    - Always call the appropriate tool when the request requires action.
    - Do NOT respond with plain text if an action is required.
    - Never ask the user for their Google OAuth token.
    - Never invent OAuth URLs.
    - Authentication is handled automatically by the tools.
    - The backend determines the authenticated user.
    - After tool execution, summarize the result.

    """),
        *state["messages"]
    ])
    return {"messages":[response]}

_AUTH_PRODUCT_LABELS = {
    "search_and_download_doc_tool": "Google Drive",
    "create_calendar_event_tool": "Google Calendar",
}


def handle_tools(state: State):

    last_message: AIMessage = state["messages"][-1]

    user_id = state["user_id"]

    results = []

    for tool_call in last_message.tool_calls:

        matched_tool = next(
            (
                t for t in tools
                if t.name == tool_call["name"]
            ),
            None,
        )

        if matched_tool is None:

            result_content = (
                f"Unknown tool: "
                f"{tool_call['name']}"
            )

        else:

            tool_args = dict(
                tool_call["args"]
            )

            # Never allow the LLM to choose
            # which user owns the credentials.
            tool_args["user_id"] = user_id

            result_content = matched_tool.invoke(
                tool_args
            )

        results.append(
            ToolMessage(
                content=result_content,
                tool_call_id=tool_call["id"],
            )
        )

    return {
        "messages": results
    }


# ==================== GRAPH =======================

# Adding Node
memory = MemorySaver()

graph_builder=StateGraph(State)

graph_builder.add_node("chatbot", chatbot)

graph_builder.add_node("tools", handle_tools)

graph_builder.add_edge(START, "chatbot")

graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
    {
        "tools": "tools",
        "__end__": END
    }
)


graph_builder.add_edge("tools","chatbot")

graph=graph_builder.compile(checkpointer=memory)

# ==================== ENTRY FUNCTION =======================

# def run_agent(user_input: str):
#     result = graph.invoke({
#         "messages": [HumanMessage(content=user_input)]
#     })
#     return result["messages"][-1].content