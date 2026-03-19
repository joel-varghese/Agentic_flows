import gradio as gr
from agent import graph
from oauth_callback import handle_oauth_callback

# ── Persistent thread so MemorySaver keeps conversation context ───────────────
THREAD_CONFIG = {"configurable": {"thread_id": "default-thread"}}


def chat(user_message: str, history: list) -> str:
    """Called by the Gradio ChatInterface on each user message."""
    events = graph.stream(
        {"messages": [{"role": "user", "content": user_message}]},
        config=THREAD_CONFIG,
        stream_mode="values",
    )
 
    last_ai_text = ""
    for event in events:
        # Check for an interrupt (auth required)
        if "__interrupt__" in event:
            interrupt_val = event["__interrupt__"][0].value
            if interrupt_val.get("type") == "auth_required":
                return interrupt_val["message"]
 
        msgs = event.get("messages", [])
        for msg in reversed(msgs):
            if hasattr(msg, "content") and msg.type == "ai" and not msg.tool_calls:
                last_ai_text = msg.content
                break
 
    return last_ai_text or "Done."
 
 
# ── OAuth callback endpoint ───────────────────────────────────────────────────
 
def oauth_callback_page(request: gr.Request) -> str:
    """
    Gradio page that Google redirects to after the user grants consent.
    Mount at /oauth/callback in your Space.
    """
    params = dict(request.query_params)
    code  = params.get("code", "")
    state = params.get("state", "")
    result = handle_oauth_callback(code, state)
    if result["success"]:
        return f"<h2>{result['message']}</h2><p>You can close this tab and return to the chat.</p>"
    return f"<h2>❌ Authentication failed</h2><p>{result['message']}</p>"
 
 
# ── Gradio UI ─────────────────────────────────────────────────────────────────
 
with gr.Blocks(title="AI Agent") as demo:
    gr.Markdown("## 🤖 AI Agent  |  Email · Google Drive")
 
    with gr.Tab("Chat"):
        gr.ChatInterface(fn=chat)
 
    # Hidden page — Google redirects here after OAuth
    with gr.Tab("OAuth Callback", visible=False) as callback_tab:
        callback_output = gr.HTML()
 
    # Route /oauth/callback → the handler above
    demo.load(fn=None)   # placeholder; real routing done via gr.mount_gradio_app or FastAPI
 
 
# ── For local dev, run directly ───────────────────────────────────────────────
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)