import os
import google.generativeai as genai
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple
from google.generativeai.types import GenerateContentResponse

class LLMBrain:
    """
    Interfaces with Google Gemini API to handle conversational intelligence,
    multimodal understanding (screenshots/webcam), and structured tool calling.
    """
    def __init__(self, api_key: Optional[str] = None, user_name: str = "Sir", assistant_name: str = "Friday"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.user_name = user_name
        self.assistant_name = assistant_name
        self.model_name = "gemini-1.5-flash" # High speed, vision, and tool calling
        self.is_configured = False
        self._configure_sdk()

    def _configure_sdk(self):
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.is_configured = True
            except Exception as e:
                print(f"Error configuring Gemini SDK: {str(e)}")
                self.is_configured = False
        else:
            self.is_configured = False

    def update_config(self, api_key: str, user_name: str, assistant_name: str):
        """Updates configurations at runtime."""
        self.user_name = user_name
        self.assistant_name = assistant_name
        if api_key != self.api_key:
            self.api_key = api_key
            self._configure_sdk()

    def get_system_instruction(self) -> str:
        """Returns Friday's core personality prompt."""
        return f"""You are {self.assistant_name}, a highly sophisticated, production-quality AI desktop assistant inspired by the Marvel universe (JARVIS / FRIDAY).
You act as a personal operating system companion.

Your Personality:
- Professional, highly intelligent, calm, concise, confident, and proactive.
- Never overly verbose, repetitive, or conversational. Keep spoken answers short and punchy.
- Address the user as {self.user_name}.
- If you cannot perform a task, explain why concisely.

Tool Execution Rules:
- You have access to local computer tools. Use them to execute desktop actions, file modifications, terminal execution, and web queries.
- Do not explain that you are calling a tool unless helpful. Just call the tool.
- Break complex requests into subtasks. Call one tool at a time and inspect its results before planning the next step.
- If a tool reports an error, attempt to troubleshoot it (e.g., if a file does not exist, check the directory contents).
- Always output clean, user-friendly summaries of tool execution results.
"""

    async def generate_response(
        self, 
        prompt: str, 
        history: List[Dict[str, str]], 
        tool_definitions: List[Dict[str, Any]], 
        image_path: Optional[str] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Sends the dialogue, history, tools, and optional image to Gemini.
        Returns:
            (reply_text, list_of_tool_calls)
            list_of_tool_calls: list of dicts like {"name": "tool_name", "args": {...}}
        """
        if not self.is_configured:
            return (
                f"Boss, I need a valid Gemini API Key to function. Please open the configuration panel in the top right and set your GEMINI_API_KEY, or add it to the .env file in the workspace.",
                []
            )

        try:
            # Map tool schemas to Gemini FunctionDeclarations
            gemini_tools = []
            for tool_def in tool_definitions:
                func = tool_def["function"]
                # Convert parameter format if required
                gemini_tools.append({
                    "name": func["name"],
                    "description": func["description"],
                    "parameters": func["parameters"]
                })

            # Create model instance with system prompt and tools
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=self.get_system_instruction(),
                tools=gemini_tools if gemini_tools else None
            )

            # Build content parts (incorporating history & current message)
            contents = []
            
            # Map SQLite history
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [msg["content"]]
                })

            # Add current user prompt (and optional visual input)
            current_parts = []
            if image_path and os.path.exists(image_path):
                try:
                    img = Image.open(image_path)
                    # Convert to RGB if needed to avoid format issues
                    if img.mode not in ("RGB", "L"):
                        img = img.convert("RGB")
                    current_parts.append(img)
                except Exception as img_err:
                    print(f"Error opening image for multimodal input: {str(img_err)}")
                    
            current_parts.append(prompt)
            contents.append({
                "role": "user",
                "parts": current_parts
            })

            # Call the Gemini API (run in execution executor to prevent blocking async loop)
            import asyncio
            loop = asyncio.get_event_loop()
            
            response: GenerateContentResponse = await loop.run_in_executor(
                None,
                lambda: model.generate_content(contents)
            )

            # Parse results
            reply = response.text if response.text else ""
            tool_calls = []

            # Check if model wanted to call functions
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        call = part.function_call
                        # Convert Map/Struct arguments to standard dict
                        args = {}
                        for k, v in call.args.items():
                            args[k] = v
                        tool_calls.append({
                            "name": call.name,
                            "args": args
                        })

            return reply, tool_calls

        except Exception as e:
            return f"Error connecting to LLM Brain: {str(e)}", []
