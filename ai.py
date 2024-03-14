import google.generativeai as genai
from google.generativeai import ChatSession
from dotenv import load_dotenv
import os

load_dotenv()

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

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
        self.sessions: dict[str, list[ChatSession]] = {}

    def accept_connection(self, channel_id: str, user_id: int, username: str):
        if not self.sessions[channel_id]:
            # Add starting prompt
            self.sessions[channel_id] = model.start_chat(history=[])
        self.cons.setdefault(channel_id, []).append(user_id)

    def destroy_connection(self, channel_id: str, user_id: int):
        for se in self.cons.values():
            se.remove(user_id)
            if not se:
                del self.sessions[channel_id]


convo = model.start_chat(history=[
])

convo.send_message("YOUR_USER_INPUT")
print(convo.last.text)
