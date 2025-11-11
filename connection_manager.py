from fastapi import WebSocket
from typing import Dict

class ConnectionManager:
    def __init__(self):
        # Store active connections as {mobile_number: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except Exception:
                # Handle case where connection might be closed
                pass

    # --- YEH NAYA FUNCTION HAI ---
    # Sabko message bhejo, siwaye sender ke
    async def broadcast_to_others(self, message: str, sender_id: str):
        for client_id, connection in self.active_connections.items():
            if client_id != sender_id:
                try:
                    await connection.send_text(message)
                except Exception:
                    pass
    # --- YAHAA TAK ---

manager = ConnectionManager()