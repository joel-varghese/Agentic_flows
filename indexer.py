from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph,START,END
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from langgraph.graph.message import add_messages 
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_community.llms import HuggingFacePipeline
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from langchain_huggingface import ChatHuggingFace
from langchain_tavily import TavilySearch
import torch
import os



load_dotenv()
base_model = "meta-llama/Llama-3.2-1B-Instruct"
local_dir = "../llama3_local"
api = os.getenv("HF_TOKEN")
tavily = os.getenv("TAVILY_API")

tokenizer = AutoTokenizer.from_pretrained(
    base_model,
    use_auth_token=api,
    cache_dir=local_dir,
)

model = AutoModelForCausalLM.from_pretrained(
    base_model,
    use_auth_token=api,
    torch_dtype=torch.float16,
    cache_dir=local_dir,
    device_map="auto",
)

hf_pipeline = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=512,
    do_sample=True,
    temperature=0.7
)

# llm = ChatHuggingFace.from_model_id(
#     model_id="meta-llama/Llama-3.2-1B-Instruct",
#     task="text-generation",
#     max_new_tokens=512,
#     temperature=0.7,
#     device_map="auto",
# )

llm = ChatHuggingFace(pipeline=hf_pipeline)

# add_messages is a reducer it appends messages into the list
# #


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
    return {"messages":[AIMessage(content=response)]}


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


tool = TavilySearch(max_results=2, tavily_api_key=tavily)
# tool.invoke("What is langgraph ?")



tools=[tool,multiply]
llm_with_tool = llm.bind_tools(tools)


def tool_calling_llm(state:State):
    messages = state["messages"]
    if isinstance(messages[-1], HumanMessage):
        prompt = messages[-1].content
    elif isinstance(messages, str):
        prompt = messages
    else:
        raise ValueError(f"Unsupported message format: {type(messages)}")
    response = llm_with_tool.invoke(prompt)

    return {"messages":[AIMessage(content=response)]}

# Adding Node
graph_builder.add_node("tool_calling_llm", tool_calling_llm)
graph_builder.add_node("tools",ToolNode(tools))
# Adding Edges
graph_builder.add_edge(START,"tool_calling_llm")
graph_builder.add_conditional_edges(
    "tool_calling_llm", tools_condition
)
graph_builder.add_edge("tools",END)


graph=graph_builder.compile()

def answer_query(query):
    response = graph.invoke({"messages": [HumanMessage(content=query)]})
    print(response)
    print("_-----")
    print(response["messages"][-1])
    # for event in graph.stream({"messages":[HumanMessage(content=query)]}):
    #     print(event)

    return response["messages"][-1].content



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
# Binding tools with LLMs #




# Stategraph
