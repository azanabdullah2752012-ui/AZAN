import asyncio
import logging
import json
import uuid
from typing import Dict, Any, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Maps device_token -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # Simple security: list of generated valid device tokens
        self.registered_tokens: List[str] = [
            "JARVIS-MOBILE-001",
            "JARVIS-WATCH-001"
        ]

    async def connect(self, websocket: WebSocket, token: str):
        if token not in self.registered_tokens:
            await websocket.close(code=1008, reason="Unauthorized Device")
            return False
            
        await websocket.accept()
        self.active_connections[token] = websocket
        logger.info(f"[Sync] Device connected: {token}")
        
        # Send initial confirmation
        await websocket.send_json({
            "type": "system",
            "status": "connected",
            "message": f"Device {token} authenticated to J.A.R.V.I.S. Core"
        })
        return True

    def disconnect(self, token: str):
        if token in self.active_connections:
            del self.active_connections[token]
            logger.info(f"[Sync] Device disconnected: {token}")

    async def broadcast_state(self, state_update: dict):
        """Streams ReAct loop states and system telemetry to all connected devices."""
        disconnected = []
        for token, connection in self.active_connections.items():
            try:
                await connection.send_json({
                    "type": "state_stream",
                    "data": state_update
                })
            except Exception as e:
                logger.error(f"[Sync] Broadcast error to {token}: {e}")
                disconnected.append(token)
                
        for token in disconnected:
            self.disconnect(token)

manager = ConnectionManager()

@router.get("/mobile/token")
async def generate_token():
    """Generates a new pairing token for a mobile/watch client."""
    new_token = f"JARVIS-DEVICE-{str(uuid.uuid4())[:8].upper()}"
    manager.registered_tokens.append(new_token)
    return {"device_token": new_token}

@router.websocket("/mobile/ws/{device_token}")
async def mobile_websocket_endpoint(websocket: WebSocket, device_token: str):
    """
    Bidirectional WebSocket stream.
    Mobile sends: Voice audio blobs, manual command texts.
    Backend sends: Live ReAct streaming cards, final TTS audio blobs, Telemetry.
    """
    is_connected = await manager.connect(websocket, device_token)
    if not is_connected:
        return

    try:
        while True:
            # Client can send text commands or JSON wrapped binary metadata
            data = await websocket.receive_text()
            
            try:
                payload = json.loads(data)
                
                if payload.get("type") == "command":
                    # Instruct orchestrator to run command and stream back to *this* socket
                    cmd = payload.get("text", "")
                    logger.info(f"[Sync] Command from {device_token}: {cmd}")
                    
                    # We would hook into `JarvisOrchestrator.process()` here natively.
                    # As a proxy for the existing HTTP streaming, we acknowledge receipt.
                    await websocket.send_json({
                        "type": "ack",
                        "message": "Orchestrator received command."
                    })
                    
            except json.JSONDecodeError:
                logger.warning("[Sync] Received non-JSON from client.")

    except WebSocketDisconnect:
        manager.disconnect(device_token)
    except Exception as e:
        logger.error(f"[Sync] Socket exception: {e}")
        manager.disconnect(device_token)
