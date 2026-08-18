from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph,START,END
from langgraph.prebuilt import tools_condition
from langgraph.graph.message import add_messages 
from langchain_core.tools import tool
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_tavily import TavilySearch
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
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
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

# ==================== LLM =======================
llm = ChatGroq(
    api_key = api,
    model = base_model,
    temperature=0.3
)

# ==================== TOOL =======================

@tool
def send_email_tool(to_email: str, subject: str, body: str) -> str:
    """
    Sends an email to a recipient.

    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body content
    """
    try:
        message = Mail(
            from_email=SENDER_EMAIL,
            to_emails=to_email,
            subject=subject,
            plain_text_content=body
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        return f"Email sent. Status code: {response.status_code}"

    except Exception as e:
        print("EMAIL ERROR:", repr(e))
        return f"Failed to send email: {repr(e)}"
    
tools = [search_and_download_doc_tool, send_email_tool, create_calendar_event_tool]
llm_with_tools = llm.bind_tools(tools)

# ==================== STATE =======================
class State(TypedDict):
    messages: Annotated[list,add_messages]


# ==================== NODES =======================

def chatbot(state:State):
    response = llm_with_tools.invoke([
    SystemMessage(content="""
    You are an AI assistant with access to tools.

    Available tools:
    1. send_email_tool → Use when the user wants to send an email.
    2. search_and_download_doc_tool → Use when the user wants to find or download a document from Google Drive.
    3. create_calendar_event_tool → Use when the user wants to schedule a meeting, send a calendar invite, or create a Google Meet.

    Rules:
    - Always call the appropriate tool when the request requires action.
    - Do NOT respond with plain text if an action is required.
    - After tool execution, summarize the result for the user.
    - Never invent or fabricate Google OAuth URLs. If authentication is required, the tool
      result or system interrupt will provide the real sign-in link.
    """),
        *state["messages"]
    ])
    return {"messages":[response]}

_AUTH_PRODUCT_LABELS = {
    "search_and_download_doc_tool": "Google Drive",
    "create_calendar_event_tool": "Google Calendar",
}


def handle_tools(state: State):
    """
    Execute tool calls.

    Google authentication is handled inside the individual Google tools
    using LangGraph interrupt().
    """

    last_message: AIMessage = state["messages"][-1]

    results = []
    for tool_call in last_message.tool_calls:
        matched_tool = next(
            (t for t in tools if t.name == tool_call["name"]), None
        )
        if matched_tool is None:
            result_content = f"Unknown tool: {tool_call['name']}"
        else:
            result_content = matched_tool.invoke(tool_call["args"])

        results.append(
            ToolMessage(
                content=result_content,
                tool_call_id=tool_call["id"],
            )
        )

    return {"messages": results}
 

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