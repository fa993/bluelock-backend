import google.generativeai as genai
from google.generativeai import ChatSession
from dotenv import load_dotenv
import os
import models
import repositories
from websocket_pool import ConnectionManager
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
import json

load_dotenv()

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

PROMPT = """You will be given a transcript of a conversation, You must detect and categorise the transcripts as one of certain flags, which will be given in a format that is specified further down. You must also give your answer as a json array with the following key: [{ "<flagname>": "<reason why it was flagged>" }]. You will be given snippets of the conversation at a time, please be aware that they belong to the same conversation. Do not add in additional comments, just stick to the json. Add the reason why that particular line was flagged in the value of the json field. Keep the property names and value in double quotes. The transcript will be in the form of: Name(Comma separated Flags to detect): Dialog. If there are no flags, return an empty array, Please stick to the flags in the prompts. Also only categorise a particular dialog as a single flag. Do not use markdown, just use plaintext regular json when you format the output. Do not use any other keys in the json other than the ones in the prompt"""

# Set up the model
generation_config = {
    "temperature": 0.5,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}

safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE"
    },
]

model = genai.GenerativeModel(model_name="gemini-1.0-pro",
                              generation_config=generation_config,
                              safety_settings=safety_settings)


class SessionManager:

    def __init__(self):
        self.cons = {}
        self.sessions: dict[str, ChatSession] = {}

    async def create_session(self, channel_id: str, user_id: int):
        if channel_id not in self.sessions:
            # Add starting prompt
            convo = model.start_chat(history=[])
            self.sessions[channel_id] = convo
            response = await convo.send_message_async(PROMPT)
            response.text
        self.cons.setdefault(channel_id, []).append(user_id)
        return convo

    def destroy_connection(self, channel_id: str, user_id: int):
        for se in self.cons.values():
            se.remove(user_id)
            if not se:
                del self.sessions[channel_id]


async def send_to_gemini(msg: models.Message, flags, session_manager: SessionManager, ws_manager: ConnectionManager, db: Session):
    convo = session_manager.sessions.get(msg.channel_id, None)
    if not convo:
        convo = await session_manager.create_session(msg.channel_id, msg.sender_id)
    response = await convo.send_message_async(f"{msg.username}({flags}): {msg.body}")
    res = response.text
    res = res.strip('```')
    res = res.strip()
    res = res.strip("json")
    res = res.strip()
    repositories.MessageRepo.update_ai(db, msg.id, res)
    msg.AIComments = res
    await ws_manager.broadcast(json.dumps(jsonable_encoder(msg)), msg.channel_id)


async def analyse_from_gemini(channel_id, session_manager: SessionManager, ws_manager: ConnectionManager, db: Session):
    convo = session_manager.sessions.get(channel_id, None)
    if not convo:
        return
    response = await convo.send_message_async(f"Summarize the entire conversation so far in 200 words plaintext no json (just for this promp)")
    res = response.text
    res = res.strip('```')
    res = res.strip()
    res = res.strip("json")
    res = res.strip()
    repositories.AnalysisRepo.update_summary(db, channel_id, res)
    msg = repositories.AnalysisRepo.fetch_latest(db, channel_id)
    await ws_manager.broadcast(json.dumps(jsonable_encoder(msg)), channel_id)
