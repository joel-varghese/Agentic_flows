import gradio as gr
from fastapi import FastAPI, Request
from google_auth import get_auth_url, fetch_token
from agent import run_agent
import json

app = FastAPI()

@app.get("/login")
def login():
    auth_url, state = get_auth_url()
    return {"auth_url": auth_url}

@app.get("/auth/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    token_data = fetch_token(code)

    with open("user_token.json", "w") as f:
        json.dump(token_data, f)

    return {"status": "Login successful. You may close this tab."}

def chat_interface(message):
    return run_agent(message)

gradio_ui = gr.Interface(
    fn=chat_interface,
    inputs="text",
    outputs="text"
)

app = gr.mount_gradio_app(app, gradio_ui, path="/")
