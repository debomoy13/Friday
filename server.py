import os
import json
import base64
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from core.orchestrator import FridayOrchestrator

app = FastAPI(title="Friday AI Assistant Server")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared orchestrator instance
orchestrator = FridayOrchestrator()

# Track active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Start background timers if this is the first connection
        if len(self.active_connections) == 1:
            orchestrator.start_background_services()

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        # Stop background services if no users are active
        if len(self.active_connections) == 0:
            orchestrator.stop_background_services()

    async def send_json(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast_json(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# Setup UI sender callback for orchestrator to broadcast background events
async def ui_event_broadcaster(event: dict):
    await manager.broadcast_json(event)

# Wrap sync/async callback compatibility
def set_orchestrator_callback():
    def callback_wrapper(event):
        asyncio.create_task(ui_event_broadcaster(event))
    orchestrator.set_ui_sender(callback_wrapper)

set_orchestrator_callback()

# Mount Static Files (Frontend UI files and local workspace file assets like screenshots)
# Create directories if they do not exist
os.makedirs("ui", exist_ok=True)

# Mount workspace directory as /static so the UI can retrieve screenshots
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
async def get_root():
    # Redirect base URL to the UI index page
    return RedirectResponse(url="/ui/index.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # 1. Send initial configuration, preferences, and recent chat history
    try:
        prefs = orchestrator.memory.get_all_preferences()
        history = orchestrator.memory.get_conversation_history(orchestrator.session_id, limit=20)
        
        # Load safety level from memory preference (default to env if missing)
        safety_level = orchestrator.memory.get_preference("safety_level", os.getenv("SAFETY_LEVEL", "medium"))
        orchestrator.safety.set_safety_level(safety_level)
        
        await manager.send_json({
            "type": "init",
            "preferences": prefs,
            "safety_level": safety_level,
            "has_api_key": bool(orchestrator.brain.api_key),
            "history": history
        }, websocket)
        
    except Exception as e:
        print(f"Error sending init package: {str(e)}")

    try:
        while True:
            # Wait for incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "user_message":
                content = message.get("content", "")
                base64_image = message.get("image", None)
                image_path = None
                
                # If image is sent, save it to disk
                if base64_image:
                    try:
                        # Extract base64 header if present
                        if "," in base64_image:
                            base64_image = base64_image.split(",")[1]
                        
                        img_data = base64.b64decode(base64_image)
                        image_path = "temp_webcam.png"
                        with open(image_path, "wb") as f:
                            f.write(img_data)
                    except Exception as img_err:
                        print(f"Failed to decode base64 webcam image: {str(img_err)}")

                # Process user request and stream back responses
                async for update in orchestrator.process_user_input(content, image_path):
                    await manager.send_json(update, websocket)

            elif msg_type == "approve_action":
                request_id = message.get("request_id")
                async for update in orchestrator.execute_approved_action(request_id):
                    await manager.send_json(update, websocket)

            elif msg_type == "deny_action":
                request_id = message.get("request_id")
                async for update in orchestrator.deny_approved_action(request_id):
                    await manager.send_json(update, websocket)

            elif msg_type == "update_settings":
                api_key = message.get("api_key", "")
                user_name = message.get("user_name", "Sir")
                assistant_name = message.get("assistant_name", "Friday")
                safety_level = message.get("safety_level", "medium")
                
                orchestrator.update_settings(api_key, user_name, assistant_name, safety_level)
                
                await manager.send_json({
                    "type": "settings_updated",
                    "preferences": {
                        "user_name": user_name,
                        "assistant_name": assistant_name,
                        "safety_level": safety_level
                    },
                    "has_api_key": bool(orchestrator.brain.api_key)
                }, websocket)

            elif msg_type == "add_reminder":
                title = message.get("title", "")
                delay = int(message.get("delay_seconds", 60))
                
                event_id = orchestrator.scheduler.add_reminder(title, delay)
                await manager.send_json({
                    "type": "reminder_added",
                    "event_id": event_id,
                    "title": title,
                    "delay_seconds": delay
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket)

# Mount the static files at the end to allow dynamic routes to take precedence
app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")
