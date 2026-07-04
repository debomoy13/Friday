import json
from typing import Dict, Any, List, Type
from pydantic import BaseModel
from tools.base import BaseTool

# Import all tools
from tools.system import SystemStatsTool, ClipboardTool, VolumeTool
from tools.terminal import TerminalTool
from tools.file_manager import ListDirectoryTool, ReadFileTool, WriteFileTool, DeleteFileTool
from tools.web import WebSearchTool, FetchWebpageTool
from tools.desktop import ScreenshotTool, ClickPositionTool, TypeTextTool

class ToolRouter:
    """
    Registers and routes tool execution calls.
    Generates tool definitions in JSON schema format for the LLM Brain.
    """
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def register_tool(self, tool: BaseTool):
        """Registers a tool in the router."""
        self.tools[tool.name] = tool

    def _register_default_tools(self):
        # Register all the modules we built
        defaults = [
            SystemStatsTool(),
            ClipboardTool(),
            VolumeTool(),
            TerminalTool(),
            ListDirectoryTool(),
            ReadFileTool(),
            WriteFileTool(),
            DeleteFileTool(),
            WebSearchTool(),
            FetchWebpageTool(),
            ScreenshotTool(),
            ClickPositionTool(),
            TypeTextTool()
        ]
        for tool in defaults:
            self.register_tool(tool)

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Generates tool definitions in standard OpenAI/Gemini format.
        Converts Pydantic schemas into JSON function declarations.
        """
        definitions = []
        for name, tool in self.tools.items():
            parameters = {}
            if tool.args_schema:
                # Support both Pydantic v1 and v2 schema generation
                if hasattr(tool.args_schema, "model_json_schema"):
                    schema = tool.args_schema.model_json_schema()
                else:
                    schema = tool.args_schema.schema()
                
                # Clean up metadata schema keys not supported by LLM APIs
                parameters = {
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", [])
                }
            else:
                parameters = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }

            definitions.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": parameters
                }
            })
        return definitions

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Routes the tool execution request to the appropriate tool instance.
        """
        if name not in self.tools:
            return f"Error: Tool '{name}' is not registered."
        
        tool = self.tools[name]
        try:
            # Validate input arguments using the pydantic schema if provided
            if tool.args_schema:
                # Parse and validate dict into Pydantic model
                validated_args = tool.args_schema(**arguments)
                # Run the actual tool execution
                result = await tool.execute(**validated_args.model_dump() if hasattr(validated_args, "model_dump") else validated_args.dict())
            else:
                result = await tool.execute(**arguments)
                
            return result
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"
