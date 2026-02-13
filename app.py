import gradio as gr
from indexer import run_email_agent

with gr.Blocks() as demo:
    gr.Markdown("## Tool-Based AI Email Agent")

    user_input = gr.Textbox(label="User Query")
    submit_btn = gr.Button("Run Agent")

    output = gr.Textbox(label="Agent Response")

    human_box = gr.Textbox(
        label="Human Assistance Required",
        visible=False
    )
    def handle_query(text):
        response = run_email_agent(text)
        return response

    submit_btn.click(
        handle_query,
        inputs=user_input,
        outputs=output
    )

demo.launch()