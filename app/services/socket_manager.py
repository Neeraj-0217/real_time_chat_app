from typing import Dict, List, Optional
from fastapi import WebSocket
import asyncio


class ConnectionManager:
    def __init__(self):
        # Store multiple websocket connections per user (for multiple tabs)
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accepts a new user websocket connection and stores it mapped to the user_id."""
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = []

        self.active_connections[user_id].append(websocket)
        connection_count = len(self.active_connections[user_id])
        print(f"✓ User {user_id} connected (connections: {connection_count}). Active users: {list(self.active_connections.keys())}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Removes a specific WebSocket connection when it disconnects."""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            
            connection_count = len(self.active_connections[user_id])
            
            # Remove user from dict if no more connections
            if connection_count == 0:
                del self.active_connections[user_id]
                print(f"✗ User {user_id} fully disconnected. Active users: {list(self.active_connections.keys())}")
            else:
                print(f"⚠ User {user_id} tab closed (remaining connections: {connection_count})")

    def is_user_online(self, user_id: int, exclude_websocket: Optional[WebSocket] = None) -> bool:
        """
        Check if a user has any active connections.
        
        Args:
            user_id: The user to check
            exclude_websocket: Optional websocket to exclude from the count
                             (useful when checking before adding a new connection)
        """
        if user_id not in self.active_connections:
            return False
        
        connections = self.active_connections[user_id]
        
        if exclude_websocket:
            # Count connections excluding the specified one
            return len([ws for ws in connections if ws != exclude_websocket]) > 0
        
        return len(connections) > 0

    def get_connection_count(self, user_id: int) -> int:
        """Get the number of active connections for a user."""
        if user_id not in self.active_connections:
            return 0
        return len(self.active_connections[user_id])

    async def send_personal_message(self, msg_data: dict, receiver_id: int):
        """
        Sends a JSON message to ALL active connections of a specific user.
        This ensures the message appears in all tabs the user has open.
        Handles dead connections gracefully.
        """
        if receiver_id not in self.active_connections:
            return
        
        # Create a copy of the list to iterate over
        connections = self.active_connections[receiver_id][:]
        dead_connections = []
        
        for connection in connections:
            try:
                await connection.send_json(msg_data)
            except Exception as e:
                print(f"⚠ Dead connection detected for user {receiver_id}: {e}")
                dead_connections.append(connection)
        
        # Clean up dead connections
        if dead_connections:
            for dead_conn in dead_connections:
                try:
                    if dead_conn in self.active_connections.get(receiver_id, []):
                        self.active_connections[receiver_id].remove(dead_conn)
                except Exception as cleanup_error:
                    print(f"⚠ Error during cleanup: {cleanup_error}")
            
            # Remove user entry if no connections remain
            if receiver_id in self.active_connections and not self.active_connections[receiver_id]:
                del self.active_connections[receiver_id]
                print(f"✗ User {receiver_id} removed due to all dead connections")

    async def broadcast(self, msg_data: dict, exclude_user: int = None):
        """
        Broadcast a message to all connected users.
        Optionally exclude a specific user.
        """
        for user_id in list(self.active_connections.keys()):
            if exclude_user and user_id == exclude_user:
                continue
            await self.send_personal_message(msg_data, user_id)

    def get_online_users(self) -> List[int]:
        """Get list of all currently online user IDs."""
        return list(self.active_connections.keys())

    def get_stats(self) -> dict:
        """Get connection statistics for debugging."""
        return {
            "total_online_users": len(self.active_connections),
            "total_connections": sum(len(conns) for conns in self.active_connections.values()),
            "users": {
                user_id: len(conns) 
                for user_id, conns in self.active_connections.items()
            }
        }


manager = ConnectionManager()