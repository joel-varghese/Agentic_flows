import gradio as gr
from indexer import answer_query

def rag_system(input_text):
    answer = answer_query(input_text)

    return answer

iface = gr.Interface(
    fn=rag_system,
    inputs="text",
    outputs="text",
    title="RAG QA System",
    description="Enter a text and ask questions based on the input text."
)

iface.launch()