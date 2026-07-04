import os
import shutil
import glob
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from tools.base import BaseTool

# Helper to resolve absolute paths and restrict if needed
def resolve_path(path: str) -> str:
    # Expand user directory (~/ -> C:\Users\...)
    expanded = os.path.expanduser(path)
    return os.path.abspath(expanded)

# --- List Directory ---
class ListDirectoryInput(BaseModel):
    path: str = Field(".", description="The directory path to list. Defaults to the current working directory.")

class ListDirectoryTool(BaseTool):
    name = "list_directory"
    description = "Lists files and folders in the specified directory."
    args_schema = ListDirectoryInput
    permission_level = "safe"

    async def execute(self, path: str = ".", **kwargs) -> Dict[str, Any]:
        target = resolve_path(path)
        if not os.path.exists(target):
            return {"error": f"Path '{path}' does not exist."}
        if not os.path.isdir(target):
            return {"error": f"Path '{path}' is a file, not a directory."}
        
        try:
            items = []
            for item in os.listdir(target):
                item_path = os.path.join(target, item)
                is_dir = os.path.isdir(item_path)
                items.append({
                    "name": item,
                    "type": "directory" if is_dir else "file",
                    "size_bytes": 0 if is_dir else os.path.getsize(item_path)
                })
            return {
                "directory": target,
                "items": items
            }
        except Exception as e:
            return {"error": str(e)}

# --- Read File ---
class ReadFileInput(BaseModel):
    path: str = Field(..., description="The path of the file to read.")
    max_lines: int = Field(200, description="Max number of lines to read. Default is 200.")

class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Reads and returns the contents of a text file."
    args_schema = ReadFileInput
    permission_level = "restricted"

    async def execute(self, path: str, max_lines: int = 200, **kwargs) -> str:
        target = resolve_path(path)
        if not os.path.exists(target):
            return f"Error: File '{path}' does not exist."
        if os.path.isdir(target):
            return f"Error: '{path}' is a directory, not a file. Use list_directory instead."
        
        try:
            lines = []
            # Try UTF-8 first, fallback to cp1252/latin-1 for Windows compatibility
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    with open(target, 'r', encoding=encoding) as f:
                        for i, line in enumerate(f):
                            if i >= max_lines:
                                lines.append(f"\n... [Truncated: File has more than {max_lines} lines] ...")
                                break
                            lines.append(line)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return f"Error: Could not decode file '{path}' (unsupported encoding)."
            
            return "".join(lines)
        except Exception as e:
            return f"Error reading file: {str(e)}"

# --- Write File ---
class WriteFileInput(BaseModel):
    path: str = Field(..., description="The path of the file to create or overwrite.")
    content: str = Field(..., description="The text content to write to the file.")

class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Writes text content to a file, creating it or overwriting it if it already exists."
    args_schema = WriteFileInput
    permission_level = "dangerous"  # Modifying files is dangerous

    async def execute(self, path: str, content: str, **kwargs) -> str:
        target = resolve_path(path)
        parent_dir = os.path.dirname(target)
        try:
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            with open(target, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"File successfully written to: {target}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

# --- Delete File ---
class DeleteFileInput(BaseModel):
    path: str = Field(..., description="The path of the file or folder to delete.")

class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = "Deletes a file or directory permanently."
    args_schema = DeleteFileInput
    permission_level = "dangerous"  # Destructive action!

    async def execute(self, path: str, **kwargs) -> str:
        target = resolve_path(path)
        if not os.path.exists(target):
            return f"Error: Path '{path}' does not exist."
        
        try:
            if os.path.isdir(target):
                shutil.rmtree(target)
                return f"Directory and all contents successfully deleted: {target}"
            else:
                os.remove(target)
                return f"File successfully deleted: {target}"
        except Exception as e:
            return f"Error deleting path: {str(e)}"
