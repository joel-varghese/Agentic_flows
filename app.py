import gradio as gr
from fastapi import FastAPI
from agent import graph
from oauth_callback import handle_oauth_callback

app = FastAPI()
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
@app.get("/oauth/callback")
async def oauth_callback(code: str = "", state: str = ""):
    """
    Gradio page that Google redirects to after the user grants consent.
    Mount at /oauth/callback in your Space.
    """
    result = handle_oauth_callback(code, state)
    if result["success"]:
        return {
            "status": "success",
            "message": result["message"],
            "instruction": "You can close this tab and return to the app."
        }
    return {
        "status": "error",
        "message": result["message"]
    }
 
 
# ── Gradio UI ─────────────────────────────────────────────────────────────────
 
with gr.Blocks(title="AI Agent") as demo:
    gr.Markdown("## 🤖 AI Agent  |  Email · Google Drive")
 
    with gr.Tab("Chat"):
        gr.ChatInterface(fn=chat)
 
 
 
# ── For local dev, run directly ───────────────────────────────────────────────
app = gr.mount_gradio_app(app, demo, path="/")