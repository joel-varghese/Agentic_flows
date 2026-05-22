import discord
import requests
import os
from dotenv import load_dotenv

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

API_URL = "https://agentic-flows.onrender.com/chat"
# API_URL = "http://localhost:8000/chat"

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    res = requests.post(
        API_URL,
        json={
            "message": message.content,
            "user_id": str(message.author.id),
            "channel": "discord",
            "thread_id": str(message.channel.id)
        }
    ).json()

    if res["type"] in ("response", "auth_required"):
        await message.channel.send(res["response"])

client.run(os.environ["DISCORD_TOKEN"])