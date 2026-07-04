import os
import asyncio
import unittest
import shutil
import sqlite3
from core.memory import MemoryManager
from core.safety import SafetyGuard
from core.router import ToolRouter
from tools.system import SystemStatsTool

class TestFridaySystem(unittest.TestCase):
    """
    Test suite to verify database memory tables, safety guard evaluations,
    and system stats tool execution.
    """
    
    def setUp(self):
        # Setup clean temporary DB for tests
        self.db_path = "test_friday_memory.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.memory = MemoryManager(db_path=self.db_path)
        self.safety = SafetyGuard(safety_level="medium", log_file="test_safety_log.txt")
        self.router = ToolRouter()

    def tearDown(self):
        # Cleanup temporary files
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists("test_safety_log.txt"):
            os.remove("test_safety_log.txt")

    def test_database_crud(self):
        """Verifies short term messages and long term preferences write/read cleanly."""
        # Test conversation history
        self.memory.add_message("session_123", "user", "Hello Friday")
        self.memory.add_message("session_123", "assistant", "Yes, Sir?")
        
        history = self.memory.get_conversation_history("session_123")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Hello Friday")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[1]["content"], "Yes, Sir?")
        
        # Test preferences
        self.memory.set_preference("test_key", "test_val")
        self.assertEqual(self.memory.get_preference("test_key"), "test_val")
        
        # Test semantic memory keywords
        self.memory.add_semantic_memory("User likes VS Code for editing", ["editor", "coding", "editor-pref"])
        results = self.memory.search_semantic_memories("what is the editor preference?")
        self.assertEqual(len(results), 1)
        self.assertTrue("VS Code" in results[0]["fact"])

    def test_safety_router_permissions(self):
        """Verifies safe tools execute immediately while dangerous tools require permission checks."""
        # 1. Safe tool (volume control / stats)
        is_approved, req_id = self.safety.check_execution(
            tool_name="control_volume",
            arguments={"action": "up"},
            tool_permission="safe"
        )
        self.assertTrue(is_approved)
        self.assertIsNone(req_id)
        
        # 2. Dangerous tool (terminal command) under medium safety
        is_approved, req_id = self.safety.check_execution(
            tool_name="execute_terminal_command",
            arguments={"command": "ping 127.0.0.1"},
            tool_permission="dangerous"
        )
        self.assertFalse(is_approved)
        self.assertIsNotNone(req_id)
        
        # Approve and check
        action = self.safety.approve_action(req_id)
        self.assertEqual(action[0], "execute_terminal_command")
        
        # 3. Restricted tool under high safety
        self.safety.set_safety_level("high")
        is_approved, req_id = self.safety.check_execution(
            tool_name="read_file",
            arguments={"path": "notes.txt"},
            tool_permission="restricted"
        )
        self.assertFalse(is_approved)
        self.assertIsNotNone(req_id)

    def test_system_stats_execution(self):
        """Verifies system stats tool runs and returns system utilization profiles."""
        tool = SystemStatsTool()
        
        # Create an event loop to run async execute
        stats = asyncio.run(tool.execute())
        
        self.assertIn("cpu_percent", stats)
        self.assertIn("memory_percent", stats)
        self.assertIn("disk_percent", stats)
        self.assertTrue(stats["cpu_percent"] >= 0)
        self.assertTrue(stats["memory_total_gb"] > 0)

if __name__ == "__main__":
    unittest.main()
