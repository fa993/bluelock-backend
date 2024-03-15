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

PROMPT = "You will be given a transcript of a conversation, your job is to detect whether any of the callers are potential scammers and/or speaking with malicious intent. You must also format your responses as json with the following key: { 'suspicious': true/false}. You will be given snippets of the conversation at a time, please be aware that they belong to the same conversation. Do not add in additional comments, just stick to the json. If you would like to add further reasoning, please keep it to within 3 lines and add it in the key 'comments'. Keep the property names in double quotes"

# Set up the model
generation_config = {
    "temperature": 0.9,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}

safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
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


async def send_to_gemini(msg: models.Message, session_manager: SessionManager, ws_manager: ConnectionManager, db: Session):
    convo = session_manager.sessions.get(msg.channel_id, None)
    if not convo:
        convo = await session_manager.create_session(msg.channel_id, msg.sender_id)
    response = await convo.send_message_async(f"{msg.sender_id}: {msg.body}")
    repositories.MessageRepo.update_ai(db, msg.id, json.loads(response.text))
    await ws_manager.broadcast(json.dumps(jsonable_encoder(msg)), msg.channel_id)
