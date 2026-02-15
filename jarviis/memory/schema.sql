-- JARVIIS Memory Schema
-- Version: 1.0
-- Database: SQLite
-- Design: Structured episodic memory with importance scoring
--
-- Philosophy:
-- - Human-readable and debuggable
-- - Importance-aware retrieval
-- - Extensible without migration pain
-- - No premature optimization

-- ============================================================================
-- Core Memory Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS memories (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Temporal tracking
    created_at TEXT NOT NULL,  -- ISO 8601 timestamp
    
    -- Memory classification
    memory_type TEXT NOT NULL CHECK(memory_type IN (
        'interaction',  -- User-system dialogue
        'fact',         -- Learned information
        'preference',   -- User preferences
        'error',        -- Errors or corrections
        'system'        -- System events
    )),
    
    -- Content (human-readable)
    summary TEXT NOT NULL,              -- Short description (for display)
    user_input TEXT,                    -- Original user input (if applicable)
    system_response TEXT,               -- System response (if applicable)
    metadata TEXT,                      -- JSON blob for extensibility
    
    -- Importance tracking
    importance_score INTEGER NOT NULL DEFAULT 1 CHECK(importance_score >= 0),
    reinforcement_count INTEGER NOT NULL DEFAULT 0,
    
    -- Future extensibility (reserved columns)
    embedding_id INTEGER,               -- Future: link to vector embeddings
    graph_node_id TEXT,                 -- Future: link to knowledge graph
    parent_memory_id INTEGER,           -- Future: memory chains/threads
    
    -- Soft delete support
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK(is_deleted IN (0, 1))
);

-- ============================================================================
-- Indexes (minimal, targeted)
-- ============================================================================

-- Index for temporal queries (recent memories)
CREATE INDEX IF NOT EXISTS idx_memories_created_at 
    ON memories(created_at DESC) 
    WHERE is_deleted = 0;

-- Index for importance-based retrieval
CREATE INDEX IF NOT EXISTS idx_memories_importance 
    ON memories(importance_score DESC, created_at DESC) 
    WHERE is_deleted = 0;

-- Index for type-based filtering
CREATE INDEX IF NOT EXISTS idx_memories_type 
    ON memories(memory_type, created_at DESC) 
    WHERE is_deleted = 0;

-- ============================================================================
-- Metadata Table (Future: For Complex Queries)
-- ============================================================================

-- Reserved for Phase 3+: Tags, entities, relationships
-- Keeping schema simple for now, but structure allows evolution

CREATE TABLE IF NOT EXISTS memory_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_memory_tags_memory_id 
    ON memory_tags(memory_id);

-- ============================================================================
-- Schema Version Tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT
);

INSERT OR IGNORE INTO schema_version (version, applied_at, description) 
VALUES (1, datetime('now'), 'Initial structured episodic memory schema');

-- ============================================================================
-- Design Notes
-- ============================================================================

-- 1. No embeddings yet - but embedding_id reserved for future FAISS/ChromaDB linking
-- 2. No complex joins - optimized for simple queries
-- 3. Metadata as TEXT (JSON) - flexible evolution without schema changes
-- 4. Soft delete (is_deleted) - preserves data integrity, allows undelete
-- 5. Reinforcement count - tracks memory strengthening over time
-- 6. Parent memory - enables conversation threading in future
-- 7. All timestamps as TEXT ISO 8601 - SQLite-friendly, human-readable

-- ============================================================================
-- Migration Strategy (Future)
-- ============================================================================

-- To add new columns: ALTER TABLE memories ADD COLUMN new_field TYPE;
-- To add indexes: CREATE INDEX IF NOT EXISTS idx_name ON table(col);
-- Reserved columns prevent breaking changes for 6+ months
