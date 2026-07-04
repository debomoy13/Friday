import os
import json
import base64
import httpx
import google.generativeai as genai
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple
from google.generativeai.types import GenerateContentResponse

def to_gemini_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively converts lowercase schema types (e.g. 'object') to uppercase ('OBJECT') for Gemini SDK compatibility."""
    if not isinstance(schema, dict):
        return schema
    new_schema = {}
    for k, v in schema.items():
        if k == "type" and isinstance(v, str):
            new_schema[k] = v.upper()
        elif isinstance(v, dict):
            new_schema[k] = to_gemini_schema(v)
        elif isinstance(v, list):
            new_schema[k] = [to_gemini_schema(item) if isinstance(item, dict) else item for item in v]
        else:
            new_schema[k] = v
    return new_schema

class LLMBrain:
    """
    Interfaces with Google Gemini API and local Ollama server to handle
    conversational reasoning, tool calling, and multimodal vision inputs.
    """
    def __init__(self, api_key: Optional[str] = None, user_name: str = "Sir", assistant_name: str = "Friday", provider: str = "gemini", ollama_url: str = "http://127.0.0.1:11434", ollama_model: str = "qwen3.6"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.user_name = user_name
        self.assistant_name = assistant_name
        self.model_name = "gemini-1.5-flash" # High speed, vision, and tool calling
        self.provider = provider
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
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

    def update_config(self, api_key: str, user_name: str, assistant_name: str, provider: str = "gemini", ollama_url: str = "http://127.0.0.1:11434", ollama_model: str = "qwen3.6"):
        """Updates configurations at runtime."""
        self.user_name = user_name
        self.assistant_name = assistant_name
        self.provider = provider
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
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
        Sends the dialogue, history, tools, and optional image to the configured provider (Gemini or Ollama).
        """
        if self.provider == "ollama":
            return await self._generate_ollama_response(prompt, history, tool_definitions, image_path)

        if not self.is_configured:
            return (
                f"Boss, I need a valid Gemini API Key to function. Please open the configuration panel in the top right and set your GEMINI_API_KEY, or add it to the .env file in the workspace.",
                []
            )

        try:
            # Map tool schemas to Gemini FunctionDeclarations (converting types to UPPERCASE)
            gemini_tools = []
            for tool_def in tool_definitions:
                func = tool_def["function"]
                gemini_tools.append({
                    "name": func["name"],
                    "description": func["description"],
                    "parameters": to_gemini_schema(func["parameters"])
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
            if image_path and os.getenv("WANT_VISION_GEMINI") != "false" and os.path.exists(image_path):
                try:
                    img = Image.open(image_path)
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

            # Call the Gemini API (run in executor to prevent blocking async loop)
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
                        args = {k: v for k, v in call.args.items()}
                        tool_calls.append({
                            "name": call.name,
                            "args": args
                        })

            return reply, tool_calls

        except Exception as e:
            return f"Error connecting to LLM Brain: {str(e)}", []

    async def _generate_ollama_response(
        self,
        prompt: str,
        history: List[Dict[str, str]],
        tool_definitions: List[Dict[str, Any]],
        image_path: Optional[str] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Runs the query against a local Ollama instance utilizing its native chat API."""
        try:
            # Format system prompt
            messages = [{"role": "system", "content": self.get_system_instruction()}]
            
            # Add dialogue history
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
                
            # Current prompt
            current_message = {"role": "user", "content": prompt}
            
            # If image is attached, encode it for local model
            if image_path and os.path.exists(image_path):
                try:
                    with open(image_path, "rb") as image_file:
                        encoded = base64.b64encode(image_file.read()).decode('utf-8')
                        current_message["images"] = [encoded]
                except Exception as img_err:
                    print(f"Error encoding local image for Ollama: {str(img_err)}")
                    
            messages.append(current_message)
            
            payload = {
                "model": self.ollama_model,
                "messages": messages,
                "stream": False
            }
            if tool_definitions:
                payload["tools"] = tool_definitions
                
            async with httpx.AsyncClient(trust_env=False, timeout=None) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
            if response.status_code != 200:
                return f"Error: Local Ollama service returned HTTP {response.status_code}. Make sure Ollama is running and model '{self.ollama_model}' is pulled.", []
                
            data = response.json()
            message_data = data.get("message", {})
            reply = message_data.get("content", "") or ""
            tool_calls = []
            
            # Parse Ollama's tool calls
            raw_calls = message_data.get("tool_calls", [])
            for call in raw_calls:
                func = call.get("function", {})
                args = func.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                tool_calls.append({
                    "name": func.get("name"),
                    "args": args
                })
                
            return reply, tool_calls
            
        except Exception as e:
            return f"Error connecting to local Ollama service: {repr(e)}. Please check if Ollama is running at {self.ollama_url}.", []
