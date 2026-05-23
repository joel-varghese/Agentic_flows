import smtplib
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
from langgraph.types import Command, interrupt
from google_auth_helpers import AUTH_REQUIRED_PREFIX
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
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)

        server.starttls()

        server.login(
            SENDER_EMAIL,
            SENDER_PASSWORD
        )

        server.sendmail(
            SENDER_EMAIL,
            to_email,
            msg.as_string()
        )

        server.quit()

        return f"Email successfully sent to {to_email}"

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
    Custom tool-execution node that intercepts AUTH_REQUIRED:: sentinels
    from Google tools and surfaces them via LangGraph interrupt.
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

        if isinstance(result_content, str) and result_content.startswith(AUTH_REQUIRED_PREFIX):
            first_line = result_content.split("\n")[0]
            auth_url = first_line.removeprefix(AUTH_REQUIRED_PREFIX).strip()
            product = _AUTH_PRODUCT_LABELS.get(
                tool_call["name"], "Google (Drive & Calendar)"
            )

            interrupt({
                "type": "auth_required",
                "auth_url": auth_url,
                "message": (
                    f"🔐 {product} access is required. "
                    "Please authenticate by visiting the link below, then retry your request.\n\n"
                    f"👉 {auth_url}"
                ),
            })
            result_content = (
                "Authentication flow initiated. Once you have completed Google sign-in, "
                "please repeat your request."
            )

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

def run_agent(user_input: str):
    result = graph.invoke({
        "messages": [HumanMessage(content=user_input)]
    })
    return result["messages"][-1].content

# Start
# LLM + promt -> Chatbot 
# 
# 
# 
# External Yools  Tool Node
# Make a tool Call || Tavily || -><- 
# 
# 
# End 
# How does chatbot know the when to use tools ?
# LLM binds with the tools : 
# Addition function added as tool to the LLM 
# Doc String is used to know what are thre inputs and arguments : If they match LLM make a call to Tool
# Instead of relying on its own response.
# 
# ReACT agent aplits the query into multiple statements and repeatedly solves query part by part
# 1. Act
# 2. Observe
# 3. Reason
# #
# Binding tools with LLMs #




# Stategraph



# tokenizer = AutoTokenizer.from_pretrained(
#     base_model,
#     use_auth_token=api,
#     cache_dir=local_dir,
# )

# model = AutoModelForCausalLM.from_pretrained(
#     base_model,
#     use_auth_token=api,
#     torch_dtype=torch.float16,
#     cache_dir=local_dir,
#     device_map="auto",
# )

# hf_pipeline = pipeline(
#     "text-generation",
#     model=model,
#     tokenizer=tokenizer,
#     max_new_tokens=512,
#     do_sample=True,
#     temperature=0.7
# )

# hf_llm = HuggingFacePipeline(pipeline=hf_pipeline)