from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph,START,END
from langgraph.graph.message import add_messages 
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_community.llms import HuggingFacePipeline
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import torch
import os



load_dotenv()
base_model = "meta-llama/Llama-3.2-1B-Instruct"
local_dir = "../llama3_local"
api = os.getenv("HF_TOKEN")

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

llm = HuggingFacePipeline(pipeline=hf_pipeline)

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
    response = llm(prompt)
    return {"messages":[AIMessage(content=response)]}



# Adding Node
graph_builder.add_node("my_chat",chatbot)
# Adding Edges
graph_builder.add_edge(START,"my_chat")
graph_builder.add_edge("my_chat",END)

graph=graph_builder.compile()


def answer_query(query):
    response = graph.invoke({"messages": [HumanMessage(content=query)]})

    return response["messages"][-1].content

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