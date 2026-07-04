from abc import ABC, abstractmethod
from typing import Type, Any, Optional
from pydantic import BaseModel

class BaseTool(ABC):
    """
    Abstract base class for all Friday tools.
    Each tool exposes its name, description, schema, permission level, and implementation.
    """
    name: str
    description: str
    args_schema: Optional[Type[BaseModel]] = None
    permission_level: str = "safe"  # safe, restricted, dangerous

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Executes the tool asynchronously.
        Returns a string or JSON-serializable output.
        """
        pass
