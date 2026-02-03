from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph,START,END
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from langgraph.graph.message import add_messages 
from langchain_core.tools import tool
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_community.llms import HuggingFacePipeline
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from langchain_huggingface import ChatHuggingFace,HuggingFacePipeline
from langchain_tavily import TavilySearch
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt

import torch
import os



memory = MemorySaver()

load_dotenv()
base_model = "llama-3.3-70b-versatile"
api = os.getenv("GROQ_API_KEY")
tavily = os.getenv("TAVILY_API")

llm = ChatGroq(
    api_key = api,
    model = base_model,
    temperature=0
)

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



class State(TypedDict):

    messages: Annotated[list,add_messages]

graph_builder=StateGraph(State)


# Node Functionality
def chatbot(state:State):
    messages = state["messages"]
    if isinstance(messages[-1], HumanMessage):
        prompt = messages[-1].content
    elif isinstance(messages, str):
        prompt = messages
    else:
        raise ValueError(f"Unsupported message format: {type(messages)}")
    response = llm.invoke(prompt)
    return {"messages":[response]}


def multiply(a:int,b:int)->int:
    """
        Multiple a and b

        Args:
            a (int): first int
            b (int): secong int

        Returns:
            int: output int
    """
    return a*b


def tool_calling_llm(state:State):
    messages = state["messages"]
    response = llm_with_tool.invoke(messages)

    return {"messages":[response]}


@tool
def human_assistance(query: str) -> str:
    """Request permission from a human to proceed with action"""
    human_response = interrupt({"query": query})
    return human_response["data"]



tool = TavilySearch(max_results=2, tavily_api_key=tavily)
tools=[tool,multiply, human_assistance]
llm_with_tool = llm.bind_tools(tools)


# Adding Node
graph_builder.add_node("chatbot", chatbot)

tool_node = ToolNode(tools=tools)

graph_builder.add_node("tools", tool_node)
# Adding Edges

graph_builder.add_conditional_edges(
    "chatbot", tools_condition
)

graph_builder.add_edge("tools","chatbot")
graph_builder.add_edge(START, "chatbot")


graph=graph_builder.compile(checkpointer=memory)

config = {"configurable":{"thread_id":"1"}}


def answer_query(query, resume_data=None):

    if resume_data: 
        events = graph.stream(
            Command(resume=resume_data), config=config, stream_mode="values"
        )
    else:
        events = graph.stream(
            {"messages":[HumanMessage(content=query)]}, config=config, stream_mode="values"
        )

    final_msg = None

    for event in events:
        msg = event["messages"][-1].content
        if isinstance(msg, dict) and "query" in msg:
            return {
                "status": "HUMAN_NEEDED",
                "query": msg["query"]
            }
        final_msg = msg

    return {
        "status": "DONE",
        "response": final_msg
    }

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
