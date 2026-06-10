import os
import aiosqlite
import json
import logging

logger = logging.getLogger("AssetSync.DB")

# Resolve DB path to the project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "assetsync.db")

async def get_db():
    """
    FastAPI dependency yielding an active database connection.
    Cleans up the connection after the request finishes.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        yield db

async def init_db():
    """
    Initializes database tables on application startup.
    Creates tables if they do not exist.
    """
    # Ensure parent directories exist
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        
        # Table for analyses runs
        await db.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                cmdb_file TEXT NOT NULL,
                actual_file TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                summary_stats TEXT
            );
        """)
        
        # Table for storing raw assets linked to an analysis
        await db.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id TEXT NOT NULL,
                source TEXT NOT NULL, -- 'cmdb' or 'actual'
                external_id TEXT,
                hostname TEXT,
                ip_address TEXT,
                cpu INTEGER,
                ram_gb INTEGER,
                os TEXT,
                status TEXT,
                FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
            );
        """)
        
        # Table for tracking identified discrepancies
        await db.execute("""
            CREATE TABLE IF NOT EXISTS discrepancies (
                id TEXT PRIMARY KEY,
                analysis_id TEXT NOT NULL,
                type TEXT NOT NULL, -- 'missing', 'untracked', 'naming_mismatch', 'attribute_mismatch', 'duplicate'
                severity TEXT NOT NULL, -- 'High', 'Medium', 'Low'
                description TEXT NOT NULL,
                external_id TEXT,
                hostname_cmdb TEXT,
                hostname_actual TEXT,
                ip_cmdb TEXT,
                ip_actual TEXT,
                details TEXT, -- JSON string storing custom mismatch details
                remediation TEXT NOT NULL,
                FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
            );
        """)
        
        await db.commit()
    logger.info("Database initialized successfully.")
