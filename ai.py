import google.generativeai as genai
from google.generativeai import ChatSession
from dotenv import load_dotenv
import os
import models

load_dotenv()

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

PROMPT = "You will be given a transcript of a conversation, your job is to detect whether any of the callers are potential scammers and/or speaking with malicious intent. You must also format your responses as json with the following key: { 'suspicious': true/false}. You will be given snippets of the conversation at a time, please be aware that they belong to the same conversation. Do not add in additional comments, just stick to the json. If you would like to add further reasoning, please keep it to within 3 lines and add it in the key 'comments'"

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

    def create_session(self, channel_id: str, user_id: int):
        if channel_id not in self.sessions:
            # Add starting prompt
            self.sessions[channel_id] = model.start_chat(history=[PROMPT])
        self.cons.setdefault(channel_id, []).append(user_id)
        return self.sessions[channel_id]

    def destroy_connection(self, channel_id: str, user_id: int):
        for se in self.cons.values():
            se.remove(user_id)
            if not se:
                del self.sessions[channel_id]


def send_to_gemini(msg: models.Message, session_manager: SessionManager):
    convo = session_manager.sessions.get(msg.channel_id, None)
    if not convo:
        convo = session_manager.create_session(msg.channel_id, msg.sender_id)
    response = convo.send_message(f"{msg.sender_id}: {msg.body}")
    print(response.text)


# convo = model.start_chat(history=[])

# convo.send_message(PROMPT)
# print(convo.last.text)
