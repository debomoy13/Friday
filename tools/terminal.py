import subprocess
import os
from typing import Dict, Any
from pydantic import BaseModel, Field
from tools.base import BaseTool

class TerminalInput(BaseModel):
    command: str = Field(..., description="The shell command to execute in PowerShell.")
    timeout: int = Field(30, description="Execution timeout in seconds. Default is 30.")

class TerminalTool(BaseTool):
    name = "execute_terminal_command"
    description = "Executes an approved terminal command in PowerShell and returns stdout and stderr."
    args_schema = TerminalInput
    permission_level = "dangerous"  # Always requires approval!

    async def execute(self, command: str, timeout: int = 30, **kwargs) -> Dict[str, Any]:
        # Enforce current working directory within user workspace or subfolders
        cwd = os.getcwd()
        try:
            # Run command in PowerShell
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Error: Command timed out after {timeout} seconds.",
                "exit_code": -1,
                "success": False
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Error: {str(e)}",
                "exit_code": -1,
                "success": False
            }
        
