import unittest
import os
import sqlite3
import datetime
from pathlib import Path
from main import MemoryKeeper

class TestMemoryKeeper(unittest.TestCase):
    """Test cases for MemoryKeeper"""

    def setUp(self):
        """Set up a test environment before each test."""
        # Use a test database file
        self.test_db_path = "test_memory_keeper.db"
        
        # Remove the test database if it exists
        try:
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)
        except PermissionError:
            print(f"Warning: Could not remove existing test database. It may be in use.")
            # Generate a unique filename instead
            self.test_db_path = f"test_memory_keeper_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        # Create a fresh instance of MemoryKeeper for testing
        self.memory_keeper = MemoryKeeper(db_path=self.test_db_path)

    def tearDown(self):
        """Clean up after each test."""
        try:
            # Force close any open connections
            self.memory_keeper = None  # Remove reference to memory keeper
            
            # Force the garbage collector to run
            import gc
            gc.collect()
            
            # Wait a brief moment to allow OS to release file locks
            import time
            time.sleep(0.1)
            
            # Try to remove the test database
            if os.path.exists(self.test_db_path):
                try:
                    os.remove(self.test_db_path)
                    print(f"Successfully removed {self.test_db_path}")
                except PermissionError:
                    print(f"Warning: Could not remove test database {self.test_db_path}. It may still be in use.")
        except Exception as e:
            print(f"Error during tearDown: {e}")

    def test_database_setup(self):
        """Test that the database is correctly set up with all the required tables."""
        conn = self.memory_keeper.get_db_connection()
        cursor = conn.cursor()

        # Check that all expected tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]

        self.assertIn("memories", tables, "The 'memories' table was not created")
        self.assertIn("memory_tags", tables, "The 'memory_tags' table was not created")
        self.assertIn("responses", tables, "The 'responses' table was not created")
        self.assertIn("categories", tables, "The 'categories' table was not created")

        # Check that default categories were added
        cursor.execute("SELECT COUNT(*) FROM categories")
        category_count = cursor.fetchone()[0]
        self.assertGreater(category_count, 0, "No default categories were created")

        conn.close()

    def test_create_memory(self):
        """Test that memories can be created and retrieved correctly."""
        # Create a test memory
        title = "Test Memory"
        content = "This is a test memory created for unit testing."
        unlock_date = datetime.datetime.now() + datetime.timedelta(days=7)
        tags = ["test", "unit testing"]
        mood = "curious"
        importance = 4

        memory_id = self.memory_keeper.create_memory(
            title = title,
            content = content,
            unlock_date = unlock_date,
            tags = tags,
            mood = mood,
            importance = importance
        )

        # Verify the memory was created
        self.assertIsNotNone(memory_id, "Memory creation failed")

        # Retrieve the memory from the database and verify its data
        conn = self.memory_keeper.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT title, content, mood, importance FROM memories WHERE id = ?", (memory_id,))
        memory_data = cursor.fetchone()

        self.assertIsNotNone(memory_data, "Failed to retrieve the created memory")
        self.assertEqual(memory_data[0], title, "Memory title doesn't match")
        self.assertEqual(memory_data[1], content, "Memory content doesn't match")
        self.assertEqual(memory_data[2], mood, "Memory mood doesn't match")
        self.assertEqual(memory_data[3], importance, "Memory importance doesn't match")

        # Check that tags were properly saved
        cursor.execute("SELECT tag FROM memory_tags WHERE memory_id = ?", (memory_id,))
        saved_tags = [row[0] for row in cursor.fetchall()]

        self.assertEqual(len(saved_tags), len(tags), "Not all tags were saved")
        for tag in tags:
            self.assertIn(tag, saved_tags, f"Tag '{tag}' was not saved")
        
        conn.close()

    def test_unlock_conditions(self):
        """Test that unlock conditions are properly stored."""
        # Create memory with an interval unlock type
        unlock_type = "interval"
        memory_id = self.memory_keeper.create_memory(
            title = "Interval Test",
            content = "Testing interval unlock type",
            unlock_date = datetime.datetime.now() + datetime.timedelta(days = 30),
            unlock_type = unlock_type
        )

        # Verify unlock conditions were set correctly
        conn = self.memory_keeper.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT unlock_type, unlock_conditions FROM memories WHERE id = ?", (memory_id,))
        unlock_data = cursor.fetchone()

        self.assertEqual(unlock_data[0], unlock_type, "Unlock type wasn't saved correctly")
        self.assertIsNotNone(unlock_data[1], "Unlock conditions should be set for non-date unlock types")

        conn.close()

    def test_multiple_memories(self):
        """Test creating and retrieving multiple memories."""
        # Create several memories
        memory_ids = []
        for i in range(5):
            memory_id = self.memory_keeper.create_memory(
                title = f"Memory {i + 1}",
                content = f"Content for memory {i + 1}",
                unlock_date = datetime.datetime.now() + datetime.timedelta(days = i + 1)
            )
            memory_ids.append(memory_id)

        # Verify all memories were created
        conn = self.memory_keeper.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM memories")
        memory_count = cursor.fetchone()[0]

        self.assertEqual(memory_count, len(memory_ids),
                         f"Expected {len(memory_ids)} memories, but found {memory_count}")
        
        conn.close()

if __name__=="__main__":
    unittest.main()