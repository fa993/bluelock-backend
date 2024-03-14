from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, channel_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(channel_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket):
        for cons in self.active_connections.values():
            cons.remove(websocket)

    async def broadcast(self, message: str, channel_id: str):
        for connection in self.active_connections.get(channel_id, []):
            await connection.send_text(message)
