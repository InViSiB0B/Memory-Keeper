from datetime import datetime
import json
import sqlite3
import uuid
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QTextEdit,
                             QListWidget, QCalendarWidget, QFileDialog,
                             QFormLayout, QGroupBox, QSplitter)
from PyQt5.QtCore import Qt, QDate, QDateTime
from PyQt5.QtGui import QIcon, QFont
from pathlib import Path

class MemoryKeeper:
    """
    Memory Keeper: A digital time capsule application that allows users
    to store memories to be unlocked at future dates.
    """
    def __init__(self, db_path="memorykeeper.db"):
        """
        Initialize the Memory Keeper application.
        Args:
                db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.app_dir = Path.home() / ".memory_keeper"
        self.media_dir = self.app_dir / "media"
        # Create application directories if they don't exist
        self.app_dir.mkdir(exist_ok=True)
        self.media_dir.mkdir(exist_ok=True)
        # Initialize database
        self.setup_database()
    
    def get_db_connection(self):
        """Establish and return a database connection."""
        return sqlite3.connect(self.db_path)
        
    def setup_database(self):
        """Create the database and tables if they don't exist."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        # Create memories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                media_path TEXT,
                created_date TEXT NOT NULL,
                unlock_date TEXT NOT NULL,
                unlock_type TEXT NOT NULL,
                unlock_conditions TEXT,
                is_unlocked INTEGER DEFAULT 0,
                category TEXT,
                mood TEXT,
                importance INTEGER DEFAULT 3
            )
        ''')
        # Create memory_tags table for tagging memories
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_tags (
                memory_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (memory_id, tag),
                FOREIGN KEY (memory_id) REFERENCES memories(id)
            )
        ''')
        # Create responses table for capturing reactions to unlocked memories
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS responses (
                id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL,
                response_content TEXT NOT NULL,
                response_date TEXT NOT NULL,
                response_mood TEXT,
                FOREIGN KEY (memory_id) REFERENCES memories (id)
            )
        ''')
        # Create categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                icon TEXT
            )
        ''')
        # Add default categories if non exist
        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            default_categories = [
                (str(uuid.uuid4()), "Milestone", "Important life events and achievements", "trophy"),
                (str(uuid.uuid4()), "Letter", "Messages to your future self", "envelope"),
                (str(uuid.uuid4()), "Question", "Questions for your future self to answer", "question-mark"),
                (str(uuid.uuid4()), "Prediction", "Guesses about your future", "crystal-ball"),
                (str(uuid.uuid4()), "Gratitude", "Things you're thankful for", "heart")
            ]
            cursor.executemany(
                "INSERT INTO categories (id, name, description, icon) VALUES (?, ?, ?, ?)",
                default_categories
            )
        conn.commit()
        conn.close()

## Database Test Function
# def test_database_setup():
#     """Test function to verify the database setup is working correctly."""
#     print("Testing database setup...")
    
#     # Create an instance of MemoryKeeper
#     memory_keeper = MemoryKeeper()
    
#     # Check if we can connect to the database
#     try:
#         conn = memory_keeper.get_db_connection()
#         print("Database connection successful")
#         cursor = conn.cursor()
        
#         # Test if tables were created by querying them
#         cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
#         tables = cursor.fetchall()
#         print(f"Found {len(tables)} tables in the database:")
#         for table in tables:
#             print(f"  - {table[0]}")
        
#         # Test if categories were added
#         cursor.execute("SELECT COUNT(*) FROM categories")
#         category_count = cursor.fetchone()[0]
#         print(f"Found {category_count} categories in the database")
        
#         # Show some category details
#         if category_count > 0:
#             cursor.execute("SELECT name, description FROM categories LIMIT 3")
#             categories = cursor.fetchall()
#             print("Sample categories:")
#             for name, description in categories:
#                 print(f"  - {name}: {description}")
        
#         conn.close()
#         print("Database test completed successfully!")
#         return True
    
#     except Exception as e:
#         print(f"Error during database test: {e}")
#         return False


# # Run the test function
# if __name__ == "__main__":
#     test_database_setup()

    def get_db_connection(self):
        """Establish and return a database connection"""
        return sqlite3.connect(self.db_path)

    def create_memory(self, title, content, unlock_date, category=None, tags=None,
                    media_path=None, mood=None, importance=3, unlock_type="date"):
        
        """
        Create a new memory in the database.

        Args:
            title: Title of the memory
            content: Text content of the memory
            unlock_date: When the memory should become available (datetime or str)
            category: Optional category ID
            tags: Optional list of tags
            media_path: Optional path to the associated media
            mood: Optional mood when creating the memory
            importance: Importance level (1-5)
            unlock_type: Type of unlock condition ('date', 'interval', 'random', etc.)

        Returns:
            The ID of the newly created memory
        """
        # Generate a unique ID for the memory
        memory_id = str(uuid.uuid4())

        # Ensure unlock_date is a string
        if isinstance(unlock_date, datetime):
            unlock_date = unlock_date.isoformat()

        # Get the current date and teme
        created_date = datetime.now().isoformat()

        # Store unlock conditions as JSON if they exist
        unlock_conditions = None
        if unlock_type != "date":
            unlock_conditions = json.dumps({
                "type": unlock_type,
            })
            
        # Insert the memory into the database
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO memories
        (id, title, content, media_path, created_date, unlock_date,
        unlock_type, unlock_conditions, category, mood, importance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (memory_id, title, content, media_path, created_date, unlock_date,
            unlock_type, unlock_conditions, category, mood, importance))
        
        # Add tags if provided
        if tags:
            for tag in tags:
                cursor.execute('''
                    INSERT INTO memory_tags (memory_id, tag) VALUES (?, ?)
                ''', (memory_id, tag))
        
        conn.commit()
        conn.close()
        return memory_id

