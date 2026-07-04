import psutil
import subprocess
import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from tools.base import BaseTool

# --- System Stats Tool ---
class SystemStatsInput(BaseModel):
    pass

class SystemStatsTool(BaseTool):
    name = "get_system_stats"
    description = "Retrieves CPU usage, memory usage, battery level, disk space, and OS information."
    args_schema = SystemStatsInput
    permission_level = "safe"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        
        battery = psutil.sensors_battery()
        battery_pct = battery.percent if battery else None
        power_plugged = battery.power_plugged if battery else None
        
        return {
            "cpu_percent": cpu,
            "memory_total_gb": round(mem.total / (1024**3), 2),
            "memory_used_gb": round(mem.used / (1024**3), 2),
            "memory_percent": mem.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_percent": disk.percent,
            "battery_percent": battery_pct,
            "power_plugged": power_plugged,
            "os": "Windows"
        }

# --- Clipboard Tool ---
class ClipboardInput(BaseModel):
    action: str = Field(..., description="Action to perform: 'get' to read clipboard, 'set' to write text to clipboard.")
    text: Optional[str] = Field(None, description="Text to write to clipboard. Required if action is 'set'.")

class ClipboardTool(BaseTool):
    name = "manage_clipboard"
    description = "Reads from or writes to the Windows system clipboard."
    args_schema = ClipboardInput
    permission_level = "safe"

    async def execute(self, action: str, text: Optional[str] = None, **kwargs) -> str:
        if action == "get":
            # Using PowerShell to get clipboard safely
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                    capture_output=True, text=True, check=True
                )
                return result.stdout.strip()
            except Exception as e:
                return f"Error reading clipboard: {str(e)}"
        elif action == "set":
            if not text:
                return "Error: Action 'set' requires the 'text' parameter."
            try:
                # Send text to Set-Clipboard via powershell input stream
                p = subprocess.Popen(
                    ["powershell", "-NoProfile", "-Command", "Set-Clipboard"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                p.communicate(input=text)
                return "Text successfully copied to clipboard."
            except Exception as e:
                return f"Error writing clipboard: {str(e)}"
        else:
            return f"Error: Unknown action '{action}'."

# --- Volume Tool ---
class VolumeInput(BaseModel):
    action: str = Field(..., description="Action to perform: 'up' (increase volume), 'down' (decrease volume), 'mute' (toggle mute).")
    steps: int = Field(2, description="Number of times to press the volume key (each step is 2% volume difference). Default is 2.")

class VolumeTool(BaseTool):
    name = "control_volume"
    description = "Adjusts system volume (up, down, or toggle mute) using Windows native key events."
    args_schema = VolumeInput
    permission_level = "safe"

    async def execute(self, action: str, steps: int = 2, **kwargs) -> str:
        # 173: Mute, 174: Volume Down, 175: Volume Up
        key_map = {"mute": 173, "down": 174, "up": 175}
        if action not in key_map:
            return f"Error: Invalid action '{action}'. Choose from: up, down, mute."
        
        char_code = key_map[action]
        # Generate script to send keyboard triggers
        script = f"""
        $wsh = New-Object -ComObject WScript.Shell
        for ($i = 0; $i -lt {steps}; $i++) {{
            $wsh.SendKeys([char]{char_code})
        }}
        """
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True, check=True
            )
            return f"Volume '{action}' action executed successfully."
        except Exception as e:
            return f"Error controlling volume: {str(e)}"
