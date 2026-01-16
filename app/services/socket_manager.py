from typing import Dict, List, Optional
from fastapi import WebSocket


class ConnectionManager:
    """
    Manages WebSocket connections.
    Supports multiple connections per user (multiple tabs/devices).
    """

    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = []

        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a specific WebSocket connection."""
        if user_id not in self.active_connections:
            return

        if websocket in self.active_connections[user_id]:
            self.active_connections[user_id].remove(websocket)

        if not self.active_connections[user_id]:
            del self.active_connections[user_id]

    def is_user_online(
        self,
        user_id: int,
        exclude_websocket: Optional[WebSocket] = None,
    ) -> bool:
        """
        Check if user has at least one active connection.
        Optionally exclude a specific websocket.
        """
        if user_id not in self.active_connections:
            return False

        connections = self.active_connections[user_id]

        if exclude_websocket:
            return any(ws != exclude_websocket for ws in connections)

        return len(connections) > 0

    async def send_personal_message(self, msg_data: dict, receiver_id: int):
        """
        Send a message to all active connections of a user.
        Dead connections are cleaned up automatically.
        """
        if receiver_id not in self.active_connections:
            return

        connections = self.active_connections[receiver_id][:]
        dead_connections = []

        for ws in connections:
            try:
                await ws.send_json(msg_data)
            except Exception:
                dead_connections.append(ws)

        # Cleanup dead sockets
        for ws in dead_connections:
            if ws in self.active_connections.get(receiver_id, []):
                self.active_connections[receiver_id].remove(ws)

        if receiver_id in self.active_connections and not self.active_connections[receiver_id]:
            del self.active_connections[receiver_id]

    async def broadcast(self, msg_data: dict, exclude_user: int = None):
        """Broadcast message to all users (optionally exclude one)."""
        for user_id in list(self.active_connections.keys()):
            if exclude_user and user_id == exclude_user:
                continue
            await self.send_personal_message(msg_data, user_id)

    def get_online_users(self) -> List[int]:
        """Return list of online user IDs."""
        return list(self.active_connections.keys())

    def get_stats(self) -> dict:
        """Return connection statistics for debugging."""
        return {
            "total_online_users": len(self.active_connections),
            "total_connections": sum(len(v) for v in self.active_connections.values()),
            "users": {
                user_id: len(conns)
                for user_id, conns in self.active_connections.items()
            },
        }


manager = ConnectionManager()
