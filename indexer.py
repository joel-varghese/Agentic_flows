import smtplib
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph,START,END
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from langgraph.graph.message import add_messages 
from langchain_core.tools import tool
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_tavily import TavilySearch
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt
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
            plain_text_content=body,
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)

        return f"Email successfully sent to {to_email}"

    except Exception as e:
        return f"Failed to send email: {str(e)}"
    
tools = [send_email_tool]
llm_with_tools = llm.bind_tools(tools)

# ==================== STATE =======================
class State(TypedDict):
    messages: Annotated[list,add_messages]

graph_builder=StateGraph(State)

# ==================== NODES =======================

def chatbot(state:State):
    response = llm_with_tools.invoke([
    SystemMessage(content="""
    You are an email assistant.
    When the user wants to send an email:
    - Extract recipient email
    - Generate subject
    - Generate professional body
    - ALWAYS call send_email_tool
    """),
        *state["messages"]
    ])
    return {"messages":[response]}

# ==================== GRAPH =======================

# Adding Node
graph_builder.add_node("chatbot", chatbot)

tool_node = ToolNode(tools=tools)

graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "chatbot")

graph_builder.add_conditional_edges(
    "chatbot", tools_condition
)

graph_builder.add_edge("tools","chatbot")

graph_builder.add_edge("chatbot",END)

graph=graph_builder.compile()

# ==================== ENTRY FUNCTION =======================

def run_email_agent(user_input: str):
    result = graph.invoke({
        "messages": [HumanMessage(content=user_input)]
    })

    final_message = result["messages"][-1].content
    return final_message



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