import os
import asyncio
from typing import Dict, Any, List, Optional, Callable, AsyncGenerator
from core.memory import MemoryManager
from core.brain import LLMBrain
from core.router import ToolRouter
from core.safety import SafetyGuard
from core.scheduler import Scheduler
from services.background_monitor import BackgroundMonitor

class FridayOrchestrator:
    """
    Central orchestration engine for Friday.
    Manages the agent execution cycle, handles multi-step tool calling,
    incorporates safety approvals, and manages background event callbacks.
    """
    def __init__(self, session_id: str = "default_session"):
        self.session_id = session_id
        
        # Core systems initialization
        self.memory = MemoryManager()
        
        # Load database preferences, fallback to env/defaults
        user_name = self.memory.get_preference("user_name", os.getenv("USER_NAME", "Sir"))
        assistant_name = self.memory.get_preference("assistant_name", os.getenv("ASSISTANT_NAME", "Friday"))
        safety_level = self.memory.get_preference("safety_level", os.getenv("SAFETY_LEVEL", "medium"))
        api_key = self.memory.get_preference("api_key", os.getenv("GEMINI_API_KEY", ""))
        provider = self.memory.get_preference("provider", "gemini")
        ollama_url = self.memory.get_preference("ollama_url", "http://127.0.0.1:11434")
        ollama_model = self.memory.get_preference("ollama_model", "qwen3.6")

        self.brain = LLMBrain(
            api_key=api_key, 
            user_name=user_name, 
            assistant_name=assistant_name,
            provider=provider,
            ollama_url=ollama_url,
            ollama_model=ollama_model
        )
        self.router = ToolRouter()
        self.safety = SafetyGuard(safety_level=safety_level)
        self.scheduler = Scheduler()
        self.monitor = BackgroundMonitor()
        
        # Connection callbacks (to send updates directly to WebSocket UI)
        self.ui_sender: Optional[Callable[[Dict[str, Any]], Any]] = None

    def set_ui_sender(self, sender: Callable[[Dict[str, Any]], Any]):
        """Sets the callback to push real-time events to the UI."""
        self.ui_sender = sender

    def start_background_services(self):
        """Starts the scheduler loop and background health monitors."""
        self.scheduler.start(self._on_scheduler_trigger)
        self.monitor.start(self._on_monitor_trigger)

    def stop_background_services(self):
        """Stops all running background services."""
        self.scheduler.stop()
        self.monitor.stop()

    async def _on_scheduler_trigger(self, reminder: Dict[str, Any]):
        """Fires when a scheduled reminder is due."""
        event = {
            "type": "reminder_trigger",
            "title": "Reminder Alert",
            "message": f"Excuse me, {self.brain.user_name}. You asked me to remind you: {reminder['title']}",
            "priority": "high"
        }
        if self.ui_sender:
            await self.ui_sender(event)

    async def _on_monitor_trigger(self, event_data: Dict[str, Any]):
        """Fires when background monitor senses low battery or high CPU load."""
        if self.ui_sender:
            await self.ui_sender(event_data)

    def update_settings(self, api_key: str, user_name: str, assistant_name: str, safety_level: str, provider: str = "gemini", ollama_url: str = "http://127.0.0.1:11434", ollama_model: str = "qwen3.6"):
        """Applies changes made in the dashboard settings panel."""
        self.brain.update_config(api_key, user_name, assistant_name, provider, ollama_url, ollama_model)
        self.safety.set_safety_level(safety_level)
        
        # Save to database preferences as well
        self.memory.set_preference("api_key", api_key)
        self.memory.set_preference("user_name", user_name)
        self.memory.set_preference("assistant_name", assistant_name)
        self.memory.set_preference("safety_level", safety_level)
        self.memory.set_preference("provider", provider)
        self.memory.set_preference("ollama_url", ollama_url)
        self.memory.set_preference("ollama_model", ollama_model)

    async def process_user_input(
        self, 
        user_message: str, 
        image_path: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes the agent thinking/acting loop.
        Yields status updates and tool execution reports back to the server in real-time.
        """
        # Reset break activity timer
        self.monitor.reset_activity_timer()
        
        # 1. Store user message
        self.memory.add_message(self.session_id, "user", user_message)
        
        # Keep track of temporary prompt history for LLM thinking loops
        history = self.memory.get_conversation_history(self.session_id, limit=15)
        
        # We start a multi-step reasoning loop (max 5 actions per prompt)
        max_steps = 5
        current_step = 0
        active_prompt = user_message
        active_image = image_path
        
        while current_step < max_steps:
            current_step += 1
            yield {"type": "status", "content": f"{self.brain.assistant_name} is reasoning..."}

            # Consult brain
            reply, tool_calls = await self.brain.generate_response(
                prompt=active_prompt,
                history=history[:-1] if current_step > 1 else history, # avoid repeating user prompt in loop
                tool_definitions=self.router.get_tool_definitions(),
                image_path=active_image
            )
            
            # Clear image path after first call so it's not repeatedly analyzed
            active_image = None

            if not tool_calls:
                # No tool calls; brain is done and returned final response
                self.memory.add_message(self.session_id, "assistant", reply)
                yield {"type": "final_response", "content": reply}
                break

            # Process the proposed tool calls
            for call in tool_calls:
                tool_name = call["name"]
                arguments = call["args"]
                
                yield {"type": "status", "content": f"Decided to call: {tool_name}"}
                
                # Check tool permission tier
                tool = self.router.tools.get(tool_name)
                if not tool:
                    yield {"type": "status", "content": f"Error: Tool '{tool_name}' not found."}
                    continue
                
                # Verify safety policy
                is_approved, request_id = self.safety.check_execution(
                    tool_name=tool_name, 
                    arguments=arguments, 
                    tool_permission=tool.permission_level
                )
                
                if not is_approved and request_id:
                    # Action is dangerous and requires approval. Stop execution loop and request via UI.
                    # Save the current state in conversation log as incomplete to resume later
                    yield {
                        "type": "requires_approval",
                        "request_id": request_id,
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "prompt": user_message # Store original query to resume
                    }
                    return # Exit loop until approved

                # Execute immediately
                yield {"type": "tool_executing", "name": tool_name, "args": arguments}
                result = await self.router.execute_tool(tool_name, arguments)
                yield {"type": "tool_result", "name": tool_name, "result": result}
                
                # Update temporary prompt history to feed back to LLM for next step
                result_str = str(result)
                history.append({"role": "model", "content": f"Executed tool {tool_name} with arguments {arguments}. Result: {result_str}"})
                active_prompt = f"Tool '{tool_name}' returned: {result_str}. Continue execution or summarize."

    async def execute_approved_action(self, request_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes a previously pending action that the user has authorized.
        Flashes execution updates, triggers tool, and feeds result back to LLM Brain.
        """
        action = self.safety.approve_action(request_id)
        if not action:
            yield {"type": "final_response", "content": "Authorization failed: Action request not found."}
            return

        tool_name, arguments = action
        yield {"type": "status", "content": f"Executing authorized action: {tool_name}"}
        yield {"type": "tool_executing", "name": tool_name, "args": arguments}
        
        # Execute tool
        result = await self.router.execute_tool(tool_name, arguments)
        yield {"type": "tool_result", "name": tool_name, "result": result}

        # Retrieve history and feed tool output back to the LLM to get a final response
        history = self.memory.get_conversation_history(self.session_id, limit=15)
        
        # Inject the tool execution context in conversation
        result_str = str(result)
        self.memory.add_message(self.session_id, "user", f"Tool '{tool_name}' output (User Approved): {result_str}")
        
        # Query brain for final response
        yield {"type": "status", "content": f"Summarizing action results..."}
        updated_history = self.memory.get_conversation_history(self.session_id, limit=15)
        
        reply, _ = await self.brain.generate_response(
            prompt=f"Review the results of the tool call '{tool_name}' and explain the outcome to me, Sir.",
            history=updated_history[:-1],
            tool_definitions=[] # No more tools allowed in final resolution to prevent loops
        )
        
        self.memory.add_message(self.session_id, "assistant", reply)
        yield {"type": "final_response", "content": reply}
        
    async def deny_approved_action(self, request_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Handles user rejection of a dangerous action."""
        action = self.safety.deny_action(request_id)
        if not action:
            yield {"type": "final_response", "content": "Action request not found."}
            return
            
        tool_name, _ = action
        reply = f"Understood. I canceled the execution of the '{tool_name}' command, Sir."
        self.memory.add_message(self.session_id, "assistant", reply)
        yield {"type": "final_response", "content": reply}
