import gradio as gr
from agent import graph

THREAD_CONFIG = {"configurable": {"thread_id": "default-thread"}}


def chat(user_message: str, history: list):
    events = graph.stream(
        {"messages": [{"role": "user", "content": user_message}]},
        config=THREAD_CONFIG,
        stream_mode="values",
    )

    last_ai_text = ""

    for event in events:
        if "__interrupt__" in event:
            interrupt_val = event["__interrupt__"][0].value
            if interrupt_val.get("type") == "auth_required":
                return f"{interrupt_val['message']}\n\n{interrupt_val['auth_url']}"

        msgs = event.get("messages", [])
        for msg in reversed(msgs):
            if hasattr(msg, "content") and msg.type == "ai":
                last_ai_text = msg.content
                break

    return last_ai_text


with gr.Blocks() as demo:
    gr.Markdown("## 🤖 AI Agent")
    gr.ChatInterface(fn=chat)


if __name__ == "__main__":
    demo.launch()