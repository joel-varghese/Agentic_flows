from json import load
import gradio as gr
from fastapi import FastAPI, Request
from pydantic import BaseModel
from slack_sdk import WebClient
from agent import graph
from oauth_callback import handle_oauth_callback
from fastapi.middleware.cors import CORSMiddleware
from chat_store import save_message, load_history
import os



slack_client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Reusable agent runner
def run_agent(message: str, user_id: str, channel: str, thread_id: str | None = None):
    thread_key = thread_id or f"{channel}:{user_id}"

    history = load_history(user_id)

    save_message(
        user_id=user_id,
        role="user",
        content=message
    )

    messages = history + [
        {
            "role": "user",
            "content": message
        }
    ]
    config = {
        "configurable": {
            "thread_id": thread_key
        }
    }

    events = graph.stream(
        {"messages": messages},
        config=config,
        stream_mode="values",
    )

    last_ai_text = ""

    for event in events:
        if "__interrupt__" in event:
            interrupt_val = event["__interrupt__"][0].value
            if interrupt_val.get("type") == "auth_required":
                text = interrupt_val["message"]
                return {
                    "type": "auth_required",
                    "response": text,
                    "auth_url": interrupt_val["auth_url"],
                }
        
        msgs = event.get("messages", [])
        for msg in reversed(msgs):
            if hasattr(msg, "content") and msg.type == "ai" and not msg.tool_calls:
                last_ai_text = msg.content
                break

    save_message(
        user_id=user_id,
        role="assistant",
        content=last_ai_text
    )
    return {"type": "response", "response": last_ai_text or "Done."}

class ChatRequest(BaseModel):
    message: str
    user_id: str = "anonymous"
    channel: str = "web"
    thread_id: str | None = None

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/chat")
def chat(req: ChatRequest):

    user_id = req.user_id or "anonymous"
    channel = req.channel or "web"

    result = run_agent(
        message=req.message,
        user_id=user_id,
        channel=channel,
        thread_id=req.thread_id
    )

    return result
 
@app.post("/slack/events")
async def slack_events(req: Request):
    data = await req.json()
    if "challenge" in data:
        return data["challenge"]

    event = data.get("event", {})

    if event.get("bot_id"):
        return {"ok": True}

    user_message = event.get("text", "")
    user_id = event.get("user", "unknown")
    channel_id = event.get("channel")
    result = run_agent(
        message=user_message,
        user_id=user_id,
        channel="slack",
        thread_id=channel_id
    )

    if result["type"] in ("response", "auth_required"):
        slack_client.chat_postMessage(
            channel=channel_id,
            text=result["response"]
        )

    return {"ok": True}

# ── OAuth callback endpoint ───────────────────────────────────────────────────
@app.get("/oauth/callback")
async def oauth_callback(code: str = "", state: str = ""):
    result = handle_oauth_callback(code, state)
    print(f">>> OAuth result: {result}")
    if result["success"]:
        return {
            "status": "success",
            "message": result["message"],
        }
    return {
        "status": "error",
        "message": result["message"]
    }
 
@app.get("/history/{user_id}")
def get_history(user_id: str):
    history = load_history(user_id)

    return history