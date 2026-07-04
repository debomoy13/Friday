import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional

class MemoryManager:
    """
    Manages long-term, short-term, and semantic memory using SQLite.
    Provides key-value user preferences, conversation history, and tag-based semantic search.
    Closes database handles explicitly after each transaction to prevent file-locking errors.
    """
    def __init__(self, db_path: str = "friday_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _execute(
        self, 
        query: str, 
        params: tuple = (), 
        commit: bool = False, 
        fetch_all: bool = False, 
        fetch_one: bool = False
    ) -> Any:
        """Helper to run a query safely, ensuring the connection is always closed."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
            if fetch_all:
                return cursor.fetchall()
            if fetch_one:
                return cursor.fetchone()
            return cursor.lastrowid
        finally:
            conn.close()

    def _init_db(self):
        # Conversation history table
        self._execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """, commit=True)
        
        # User preferences and profile details (key-value storage)
        self._execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """, commit=True)
        
        # Semantic memories / long-term facts
        self._execute("""
            CREATE TABLE IF NOT EXISTS semantic_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT NOT NULL,
                tags TEXT NOT NULL, -- comma separated tags
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """, commit=True)
        
        # Insert default preferences if they don't exist
        default_prefs = {
            "preferred_editor": "VS Code",
            "preferred_browser": "Chrome",
            "user_name": "Sir",
            "assistant_name": "Friday",
            "voice_speed": "1.0",
            "safety_level": "medium"
        }
        for k, v in default_prefs.items():
            self._execute("""
                INSERT OR IGNORE INTO preferences (key, value)
                VALUES (?, ?)
            """, (k, v), commit=True)

    # --- Short-term / Conversation History ---
    def add_message(self, session_id: str, role: str, content: str):
        """Adds a message to the conversation log."""
        self._execute("""
            INSERT INTO conversations (session_id, role, content)
            VALUES (?, ?, ?)
        """, (session_id, role, content), commit=True)

    def get_conversation_history(self, session_id: str, limit: int = 20) -> List[Dict[str, str]]:
        """Retrieves the last N messages for a session."""
        rows = self._execute("""
            SELECT role, content, timestamp FROM conversations
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (session_id, limit), fetch_all=True)
        return [{"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]} for r in reversed(rows)]

    def clear_conversation(self, session_id: str):
        """Clears conversation history for a session."""
        self._execute("DELETE FROM conversations WHERE session_id = ?", (session_id,), commit=True)

    # --- Key-Value User Preferences ---
    def set_preference(self, key: str, value: str):
        """Sets a user preference."""
        self._execute("""
            INSERT INTO preferences (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
        """, (key, value), commit=True)

    def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Gets a user preference."""
        row = self._execute("SELECT value FROM preferences WHERE key = ?", (key,), fetch_one=True)
        return row["value"] if row else default

    def get_all_preferences(self) -> Dict[str, str]:
        """Gets all preferences as a dict."""
        rows = self._execute("SELECT key, value FROM preferences", fetch_all=True)
        return {row["key"]: row["value"] for row in rows}

    # --- Semantic Memories / Long-term facts ---
    def add_semantic_memory(self, fact: str, tags: List[str]):
        """Saves a long-term fact with tags."""
        tags_str = ",".join([t.strip().lower() for t in tags])
        self._execute("""
            INSERT INTO semantic_memories (fact, tags)
            VALUES (?, ?)
        """, (fact, tags_str), commit=True)

    def search_semantic_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Searches facts based on keyword overlap inside the fact and tag fields.
        Returns matching memories sorted by matching score (token intersection).
        """
        query_tokens = set(query.lower().split())
        if not query_tokens:
            return []

        rows = self._execute("SELECT id, fact, tags, created_at FROM semantic_memories", fetch_all=True)
            
        results = []
        for r in rows:
            fact = r["fact"]
            tags = r["tags"].split(",")
            
            # Combine fact text and tags for matching
            search_space = set(fact.lower().split() + tags)
            overlap = query_tokens.intersection(search_space)
            
            if overlap:
                # Rank score based on overlap size
                score = len(overlap) / len(query_tokens)
                results.append({
                    "id": r["id"],
                    "fact": fact,
                    "tags": tags,
                    "created_at": r["created_at"],
                    "score": score
                })
                
        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def delete_semantic_memory(self, memory_id: int):
        """Deletes a semantic memory by ID."""
        self._execute("DELETE FROM semantic_memories WHERE id = ?", (memory_id,), commit=True)
