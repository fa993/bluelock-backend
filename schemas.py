from typing import List, Optional

from pydantic import BaseModel


class Message:
    body: str
    sender_id: str
    channel_id: str

    def __init__(self, body, sender_id, channel_id):
        self.body = body
        self.sender_id = sender_id
        self.channel_id = channel_id
