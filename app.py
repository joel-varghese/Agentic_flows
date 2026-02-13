import gradio as gr
from indexer import run_email_agent

with gr.Blocks(css="""
    body {background-color: #fffaf0;}  /* Light creme background */
    .gr-textbox {min-height: 200px;}  /* Make textboxes taller */
""") as demo:
    gr.Markdown("## Tool-Based AI Email Agent")

    user_input = gr.Textbox(
        label="User Query",
        placeholder="Type your question here...",
        lines=4  # make input box slightly bigger
    )
    submit_btn = gr.Button("Run Agent")

    output = gr.Textbox(
        label="Agent Response",
        placeholder="The agent will respond here...",
        lines=10  # bigger response box
    )

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
