import gradio as gr
from fastapi import FastAPI
from pydantic import BaseModel
from agent import graph
from oauth_callback import handle_oauth_callback
from fastapi.middleware.cors import CORSMiddleware
import uvicorn



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ── Persistent thread so MemorySaver keeps conversation context ───────────────
THREAD_CONFIG = {"configurable": {"thread_id": "default-thread"}}

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/chat")
def chat(req: ChatRequest):
    events = graph.stream(
        {"messages": [{"role": "user", "content": req.message}]},
        config=THREAD_CONFIG,
        stream_mode="values",
    )
 
    last_ai_text = ""
    for event in events:
        # Check for an interrupt (auth required)
        if "__interrupt__" in event:
            interrupt_val = event["__interrupt__"][0].value
            if interrupt_val.get("type") == "auth_required":
                return {
                    "type": "auth_required",
                    "auth_url": interrupt_val["auth_url"],
                    "message": interrupt_val["message"]
                }
            
        msgs = event.get("messages", [])
        for msg in reversed(msgs):
            if hasattr(msg, "content") and msg.type == "ai" and not msg.tool_calls:
                last_ai_text = msg.content
                break
 
    return {"type": "response", "response": last_ai_text or "Done."}
 
 
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
 