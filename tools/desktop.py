import os
import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from tools.base import BaseTool

# We import pyautogui inside execute or check import, because pyautogui requires GUI context
# and we want the imports to be safe if run in environments without display server.

class ScreenshotInput(BaseModel):
    filename: str = Field("screenshot.png", description="Name of the screenshot file to save. Default is screenshot.png.")

class ScreenshotTool(BaseTool):
    name = "take_screenshot"
    description = "Captures the entire desktop screen and saves it as an image."
    args_schema = ScreenshotInput
    permission_level = "safe" # Reading screen is usually safe but lets verify

    async def execute(self, filename: str = "screenshot.png", **kwargs) -> Dict[str, Any]:
        import pyautogui
        # Make sure the screenshot is saved inside a public/temp directory or workspace
        # We'll save it to the current working directory, which the server can serve static
        out_dir = os.path.abspath(os.getcwd())
        target_path = os.path.join(out_dir, filename)
        
        try:
            # PyAutoGUI screenshot
            screenshot = pyautogui.screenshot()
            screenshot.save(target_path)
            
            # Get screen sizes
            width, height = pyautogui.size()
            
            return {
                "success": True,
                "saved_path": target_path,
                "filename": filename,
                "resolution": f"{width}x{height}",
                "message": f"Screenshot successfully saved to {target_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to capture screenshot: {str(e)}"
            }

class ClickInput(BaseModel):
    x: int = Field(..., description="The X coordinate to click.")
    y: int = Field(..., description="The Y coordinate to click.")
    clicks: int = Field(1, description="Number of clicks. Default is 1.")
    button: str = Field("left", description="Mouse button: 'left', 'right', or 'middle'. Default is 'left'.")

class ClickPositionTool(BaseTool):
    name = "click_position"
    description = "Clicks the mouse at specified screen coordinates."
    args_schema = ClickInput
    permission_level = "dangerous"  # Controls mouse

    async def execute(self, x: int, y: int, clicks: int = 1, button: str = "left", **kwargs) -> str:
        import pyautogui
        try:
            width, height = pyautogui.size()
            if x < 0 or x > width or y < 0 or y > height:
                return f"Error: Click coordinates ({x}, {y}) are outside the screen resolution ({width}x{height})."
            
            pyautogui.click(x=x, y=y, clicks=clicks, button=button)
            return f"Successfully clicked {button} button {clicks} time(s) at ({x}, {y})."
        except Exception as e:
            return f"Error clicking screen: {str(e)}"

class TypeTextInput(BaseModel):
    text: str = Field(..., description="The text string to type.")
    press_enter: bool = Field(True, description="Whether to press Enter after typing. Default is True.")

class TypeTextTool(BaseTool):
    name = "type_text"
    description = "Simulates keyboard typing of the specified text."
    args_schema = TypeTextInput
    permission_level = "dangerous"  # Controls keyboard

    async def execute(self, text: str, press_enter: bool = True, **kwargs) -> str:
        import pyautogui
        try:
            # Small delay before typing to ensure window focus
            time.sleep(0.5)
            pyautogui.write(text, interval=0.01)
            if press_enter:
                pyautogui.press("enter")
            return f"Successfully typed text (length: {len(text)}) and pressed enter: {press_enter}."
        except Exception as e:
            return f"Error typing text: {str(e)}"
