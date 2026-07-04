import os
import uuid
import datetime
from typing import Dict, Any, Tuple, Optional

class SafetyGuard:
    """
    Evaluates tool executions against safety policies.
    Maintains a registry of pending actions waiting for user confirmation.
    Logs all executions to 'friday_safety_log.txt' for audit trail.
    """
    def __init__(self, safety_level: str = "medium", log_file: str = "friday_safety_log.txt"):
        # safety_level: "low", "medium", "high"
        self.safety_level = safety_level.lower()
        self.log_file = log_file
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}

    def set_safety_level(self, level: str):
        self.safety_level = level.lower()

    def log_action(self, tool_name: str, arguments: Dict[str, Any], status: str, details: str = ""):
        """Appends action log to safety audit file."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] TOOL: {tool_name} | STATUS: {status} | ARGS: {arguments} | DETAILS: {details}\n"
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception:
            pass  # Do not block execution if logging fails

    def check_execution(self, tool_name: str, arguments: Dict[str, Any], tool_permission: str) -> Tuple[bool, Optional[str]]:
        """
        Determines if a tool execution is safe to proceed or requires manual user approval.
        Returns:
            (is_approved, request_id)
            If is_approved is True, execute immediately.
            If is_approved is False and request_id is present, wait for user confirmation.
            If is_approved is False and request_id is None, command is blocked.
        """
        # Low safety: everything runs immediately
        if self.safety_level == "low":
            self.log_action(tool_name, arguments, "EXECUTED_IMMEDIATELY", "Low safety level bypass")
            return True, None
            
        # Medium safety: dangerous tools require approval
        if self.safety_level == "medium":
            if tool_permission == "dangerous":
                request_id = str(uuid.uuid4())
                self.pending_approvals[request_id] = {
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "permission_level": tool_permission,
                    "timestamp": datetime.datetime.now()
                }
                self.log_action(tool_name, arguments, "PENDING_APPROVAL", "Medium safety check: dangerous tool")
                return False, request_id
            else:
                self.log_action(tool_name, arguments, "EXECUTED_IMMEDIATELY", "Medium safety check: safe/restricted tool")
                return True, None
                
        # High safety: restricted & dangerous tools require approval
        if self.safety_level == "high":
            if tool_permission in ["restricted", "dangerous"]:
                request_id = str(uuid.uuid4())
                self.pending_approvals[request_id] = {
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "permission_level": tool_permission,
                    "timestamp": datetime.datetime.now()
                }
                self.log_action(tool_name, arguments, "PENDING_APPROVAL", "High safety check: restricted/dangerous tool")
                return False, request_id
            else:
                self.log_action(tool_name, arguments, "EXECUTED_IMMEDIATELY", "High safety check: safe tool")
                return True, None

        # Fallback safety default
        request_id = str(uuid.uuid4())
        self.pending_approvals[request_id] = {
            "tool_name": tool_name,
            "arguments": arguments,
            "permission_level": tool_permission
        }
        return False, request_id

    def approve_action(self, request_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Approves a pending action and removes it from the queue."""
        action = self.pending_approvals.pop(request_id, None)
        if action:
            self.log_action(action["tool_name"], action["arguments"], "APPROVED", "Approved by user")
            return action["tool_name"], action["arguments"]
        return None

    def deny_action(self, request_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Denies a pending action and removes it from the queue."""
        action = self.pending_approvals.pop(request_id, None)
        if action:
            self.log_action(action["tool_name"], action["arguments"], "DENIED", "Denied by user")
            return action["tool_name"], action["arguments"]
        return None
