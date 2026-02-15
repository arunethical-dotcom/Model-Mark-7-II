"""
JARVIIS SQLite Storage Layer
Pure storage implementation - no business logic, no routing decisions.

Responsibilities:
- Initialize database schema
- Execute SQL operations safely
- Return structured data
- Handle SQLite errors gracefully

Does NOT:
- Compute importance scores (that's memory_router's job)
- Make storage decisions (that's memory_router's job)
- Contain FSM logic (that's orchestrator's job)
- Use async (synchronous only, matches core)

Philosophy: Boringly correct > Clever
"""

import sqlite3
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class SQLiteStore:
    """
    SQLite-backed memory storage.
    
    This class is intentionally boring:
    - No caching
    - No connection pooling
    - No ORM
    - No async
    - Just reliable SQL operations
    
    Design: Fail gracefully, never crash the system.
    """
    
    def __init__(self, db_path: str = "jarviis_memory.db"):
        """
        Initialize SQLite storage.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_schema()
    
    def _ensure_schema(self) -> None:
        """
        Initialize database schema if not exists.
        
        Idempotent - safe to call multiple times.
        """
        try:
            # Read schema file
            schema_path = Path(__file__).parent / "schema.sql"
            
            if not schema_path.exists():
                raise FileNotFoundError(f"Schema file not found: {schema_path}")
            
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            # Execute schema
            with self._get_connection() as conn:
                conn.executescript(schema_sql)
                conn.commit()
                
        except Exception as e:
            # Log but don't crash - memory failure shouldn't kill system
            print(f"[ERROR] Failed to initialize schema: {e}")
            raise
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get SQLite connection with sensible defaults.
        
        Returns:
            SQLite connection object
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def insert_memory(
        self,
        memory_type: str,
        summary: str,
        importance_score: int,
        user_input: Optional[str] = None,
        system_response: Optional[str] = None,
        metadata: Optional[str] = None,
        created_at: Optional[str] = None
    ) -> Optional[int]:
        """
        Insert a new memory record.
        
        Args:
            memory_type: Type of memory (interaction/fact/preference/error/system)
            summary: Short human-readable description
            importance_score: Numeric importance (computed by router)
            user_input: Original user input (optional)
            system_response: System response (optional)
            metadata: JSON string for extensibility (optional)
            created_at: ISO timestamp (defaults to now)
            
        Returns:
            Memory ID if successful, None on failure
        """
        if created_at is None:
            created_at = datetime.now().isoformat()
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO memories (
                        created_at,
                        memory_type,
                        summary,
                        user_input,
                        system_response,
                        metadata,
                        importance_score,
                        reinforcement_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    created_at,
                    memory_type,
                    summary,
                    user_input,
                    system_response,
                    metadata,
                    importance_score
                ))
                conn.commit()
                return cursor.lastrowid
                
        except sqlite3.IntegrityError as e:
            print(f"[ERROR] Integrity error inserting memory: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Failed to insert memory: {e}")
            return None
    
    def fetch_recent_memories(
        self,
        limit: int = 10,
        memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent memories by timestamp.
        
        Args:
            limit: Maximum number of memories to return
            memory_type: Filter by type (optional)
            
        Returns:
            List of memory dictionaries, newest first
        """
        try:
            with self._get_connection() as conn:
                if memory_type:
                    cursor = conn.execute("""
                        SELECT 
                            id,
                            created_at,
                            memory_type,
                            summary,
                            user_input,
                            system_response,
                            metadata,
                            importance_score,
                            reinforcement_count
                        FROM memories
                        WHERE is_deleted = 0 AND memory_type = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (memory_type, limit))
                else:
                    cursor = conn.execute("""
                        SELECT 
                            id,
                            created_at,
                            memory_type,
                            summary,
                            user_input,
                            system_response,
                            metadata,
                            importance_score,
                            reinforcement_count
                        FROM memories
                        WHERE is_deleted = 0
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            print(f"[ERROR] Failed to fetch recent memories: {e}")
            return []
    
    def fetch_important_memories(
        self,
        min_importance: int = 2,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch memories above importance threshold.
        
        Args:
            min_importance: Minimum importance score
            limit: Maximum number of memories
            
        Returns:
            List of important memories, sorted by importance then recency
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        id,
                        created_at,
                        memory_type,
                        summary,
                        user_input,
                        system_response,
                        metadata,
                        importance_score,
                        reinforcement_count
                    FROM memories
                    WHERE is_deleted = 0 AND importance_score >= ?
                    ORDER BY importance_score DESC, created_at DESC
                    LIMIT ?
                """, (min_importance, limit))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            print(f"[ERROR] Failed to fetch important memories: {e}")
            return []
    
    def fetch_by_type_and_importance(
        self,
        memory_type: str,
        min_importance: int = 1,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch memories filtered by type and importance.
        
        Args:
            memory_type: Type of memory to fetch
            min_importance: Minimum importance threshold
            limit: Maximum results
            
        Returns:
            Filtered memories
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        id,
                        created_at,
                        memory_type,
                        summary,
                        user_input,
                        system_response,
                        metadata,
                        importance_score,
                        reinforcement_count
                    FROM memories
                    WHERE is_deleted = 0 
                      AND memory_type = ?
                      AND importance_score >= ?
                    ORDER BY importance_score DESC, created_at DESC
                    LIMIT ?
                """, (memory_type, min_importance, limit))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            print(f"[ERROR] Failed to fetch memories by type: {e}")
            return []
    
    def reinforce_memory(self, memory_id: int) -> bool:
        """
        Increment reinforcement count for a memory.
        
        Used when a memory is recalled or proves useful.
        
        Args:
            memory_id: ID of memory to reinforce
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE memories
                    SET reinforcement_count = reinforcement_count + 1
                    WHERE id = ? AND is_deleted = 0
                """, (memory_id,))
                conn.commit()
                return True
                
        except Exception as e:
            print(f"[ERROR] Failed to reinforce memory {memory_id}: {e}")
            return False
    
    def soft_delete_memory(self, memory_id: int) -> bool:
        """
        Soft delete a memory (mark as deleted, don't remove).
        
        Args:
            memory_id: ID of memory to delete
            
        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE memories
                    SET is_deleted = 1
                    WHERE id = ?
                """, (memory_id,))
                conn.commit()
                return True
                
        except Exception as e:
            print(f"[ERROR] Failed to soft delete memory {memory_id}: {e}")
            return False
    
    def clear_all_memories(self) -> bool:
        """
        Clear all memories (soft delete).
        
        USE WITH CAUTION - This is for testing/reset only.
        
        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                conn.execute("UPDATE memories SET is_deleted = 1")
                conn.commit()
                return True
                
        except Exception as e:
            print(f"[ERROR] Failed to clear memories: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics for observability.
        
        Returns:
            Dictionary of statistics
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_memories,
                        COUNT(CASE WHEN is_deleted = 0 THEN 1 END) as active_memories,
                        AVG(CASE WHEN is_deleted = 0 THEN importance_score END) as avg_importance,
                        MAX(created_at) as last_memory_time
                    FROM memories
                """)
                
                row = cursor.fetchone()
                
                # Get memory type breakdown
                type_cursor = conn.execute("""
                    SELECT memory_type, COUNT(*) as count
                    FROM memories
                    WHERE is_deleted = 0
                    GROUP BY memory_type
                """)
                
                type_counts = {row['memory_type']: row['count'] 
                              for row in type_cursor.fetchall()}
                
                return {
                    'total_memories': row['total_memories'],
                    'active_memories': row['active_memories'],
                    'avg_importance': round(row['avg_importance'] or 0, 2),
                    'last_memory_time': row['last_memory_time'],
                    'type_breakdown': type_counts
                }
                
        except Exception as e:
            print(f"[ERROR] Failed to get stats: {e}")
            return {
                'total_memories': 0,
                'active_memories': 0,
                'avg_importance': 0,
                'last_memory_time': None,
                'type_breakdown': {}
            }
