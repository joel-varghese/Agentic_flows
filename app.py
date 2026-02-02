import gradio as gr
from indexer import answer_query

with gr.Blocks() as demo:
    gr.Markdown("## Agentic RAG System")

    user_input = gr.Textbox(label="User Query")
    submit_btn = gr.Button("Submit")

    output = gr.Textbox(label="LLM Response")

    human_box = gr.Textbox(
        label="Human Assistance Required",
        visible=False
    )
    human_submit = gr.Button("Send Human Input", visible=False)

    state = gr.State()

    def handle_user_query(query):
        result = answer_query(query)
        if result["status"] == "HUMAN_NEEDED":
            return (
                gr.update(value="Waiting for human assistance..."),
                gr.update(visible=True),
                gr.update(visible=True),
                result["query"]
            )
        return (
            result["response"],
            gr.update(visible=False),
            gr.update(visible=False),
            None
        )
    
    def handle_human_input(human_text):
        result = answer_query(None, resume_data=human_text)
        return (
            result["response"],
            gr.update(visible=False),
            gr.update(visible=False)
        )
    
    submit_btn.click(
        handle_user_query,
        inputs=user_input,
        outputs=[output, human_box, human_submit, state]
    )

    human_submit.click(
        handle_human_input,
        inputs=human_box,
        outputs=[output, human_box, human_submit]
    )

demo.launch()