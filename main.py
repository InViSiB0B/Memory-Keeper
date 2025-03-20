from datetime import datetime
import json
import sqlite3
import sys
import uuid
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QTextEdit,
                             QListWidget, QCalendarWidget, QFileDialog,
                             QFormLayout, QGroupBox, QSplitter, QTabWidget,
                             QMessageBox, QComboBox,QScrollArea, QFrame, QLineEdit, 
                             QDateEdit, QDateTimeEdit, QSpinBox)
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
    
    def get_upcoming_memories(self, limit = 10):
        """
        Get memories that will unlock soon but haven't yet.

        Args:
            limit: Maximum number of memories to return

        Returns:
            List of memory dictionaries
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, title, created_date, unlock_date, category, importance
            FROM memories
            WHERE is_unlocked = 0 AND unlock_date > ?
            ORDER BY unlock_date ASC
            LIMIT ?
        ''', (datetime.now().isoformat(), limit))

        columns = ["id", "title", "created_date", "unlock_date", "category", "importance"]
        memories = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return memories
    
    def unlock_memory(self, memory_id):
        """
        Mark a memory as unlocked.

        Args:
            memory_id: ID of the memory to unlock

        Returns:
            Boolean indicating success
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE memories
            SET is_unlocked = 1
            WHERE id = ?
        ''', (memory_id,))

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success
    
    def add_response (self, memory_id, response_content, mood = None):
        """
        Add a response to an unlocked memory.

        Args:
            memory_id: ID of the memory being responded to
            response_content: Text content of the response
            mood: Optional mood when creating the response

        Returns:
            The ID of the newly created response
        """
        response_id = str(uuid.uuid4())
        response_date = datetime.now().isoformat()

        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO responses
            (id, memory_id, response_content, response_date, response_mood)
            VALUES (?, ?, ?, ?, ?)
        ''', (response_id, memory_id, response_content, response_date, mood))

        conn.commit()
        conn.close()

        return response_id
    
    def get_memory_count(self):
        """Get counts of total, locked, and unlocked memories."""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM memories")
        total_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM memories WHERE is_unlocked = 0")
        locked_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM memories WHERE is_unlocked = 1")
        unlocked_count = cursor.fetchone()[0]

        conn.close()

        return {
            "total": total_count,
            "locked": locked_count,
            "unlocked": unlocked_count
        }

    def get_categories(self):
        """Get all available categories."""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, name, description, icon FROM categories")

        columns = ["id", "name", "description", "icon"]
        categories = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return categories
    
    def get_unlockable_memories(self):
        """
        Get memories that are ready to be unlocked based on their unlock date.
        
        Returns:
            List of memory dictionaries
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute('''
            SELECT id, title, content, media_path, created_date, unlock_date, 
                category, mood, importance
            FROM memories
            WHERE is_unlocked = 0 AND unlock_date <= ?
        ''', (now,))
        
        columns = ["id", "title", "content", "media_path", "created_date", 
                "unlock_date", "category", "mood", "importance"]
        memories = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return memories
    
class MemoryKeeperApp(QMainWindow):
    """Main application window for MemoryKeeper."""

    def __init__(self, memory_keeper):
        super().__init__()

        self.memory_keeper = memory_keeper
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("MemoryKeeper - Your Digital Time Capsule")
        self.setGeometry(100, 100, 1000, 800)

        # Create the central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header with application title
        header_label = QLabel("MemoryKeeper")
        header_label.setFont(QFont("Arial", 18, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)

        # Create tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Create individual tabs
        self.dashboard_tab = self.create_dashboard_tab()
        self.create_memory_tab = self.create_memory_form_tab()
        self.vault_tab = self.create_vault_tab()
        self.unlocked_tab = self.create_unlocked_tab()

        # Add tabs to the tab widget
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.create_memory_tab, "Create Memory")
        self.tabs.addTab(self.vault_tab, "Memory Vault")
        self.tabs.addTab(self.unlocked_tab, "Unlocked Memories")

        # Check for unlockable memories
        self.check_unlockable_memories()

        # Footer with status information
        status_bar = self.statusBar()
        status_bar.showMessage("Ready")

    def create_dashboard_tab(self):
        """Create the dashboard tab with summary information."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Welcome section
        welcome_group = QGroupBox("Welcome to MemoryKeeper")
        welcome_layout = QVBoxLayout(welcome_group)

        welcome_text = QLabel(
            "MemoryKeeper is your personal digital time capsule, allowing you to send "
            "messages and memories to your future self. Create memories today that will "
            "surprise and delight you months or years from now!"
        )
        welcome_text.setWordWrap(True)
        welcome_layout.addWidget(welcome_text)

        layout.addWidget(welcome_group)

        # Statistics section
        stats_group = QGroupBox("Your Memory Stats")
        stats_layout = QHBoxLayout(stats_group)

        # Get memory counts
        counts = self.memory_keeper.get_memory_count()

        total_label = QLabel(f"Total Memories: {counts['total']}")
        total_label.setFont(QFont("Arial", 12))

        locked_label = QLabel(f"Locked:  {counts['locked']}")
        locked_label.setFont(QFont("Arial", 12))

        unlocked_label = QLabel(f"Unlocked: {counts['unlocked']}")
        unlocked_label.setFont(QFont("Arial", 12))

        stats_layout.addWidget(total_label)
        stats_layout.addWidget(locked_label)
        stats_layout.addWidget(unlocked_label)

        layout.addWidget(stats_group)

        # Upcoming memories section
        upcoming_group = QGroupBox("Upcoming Memories")
        upcoming_layout = QVBoxLayout(upcoming_group)

        # Get upcoming memories
        upcoming_memories = self.memory_keeper.get_upcoming_memories(limit = 5)

        if upcoming_memories:
            for memory in upcoming_memories:
                # Convert ISO dates to a readable format
                created = datetime.fromisoformat(memory["created_date"]).strftime("%m/%d/%Y")
                unlock = datetime.fromisoformat(memory["unlock_date"]).strftime("%m/%d/%Y")

                memory_frame = QFrame()
                memory_frame.setFrameShape(QFrame.StyledPanel)
                memory_frame.setFrameShadow(QFrame.Raised)
                memory_layout = QVBoxLayout(memory_frame)

                title_label = QLabel(memory["title"])
                title_label.setFont(QFont("Arial", 11, QFont.Bold))

                dates_label = QLabel(f"Created: {created} | Unlocks: {unlock}")

                memory_layout.addWidget(title_label)
                memory_layout.addWidget(dates_label)

                upcoming_layout.addWidget(memory_frame)
        else:
            no_memories_label = QLabel("You don't have any upcoming memories. Create one now!")
            upcoming_layout.addWidget(no_memories_label)

        layout.addWidget(upcoming_group)

        # Quick actions section
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout(actions_group)

        create_button = QPushButton("Create New Memory")
        create_button.clicked.connect(lambda: self.tabs.setCurrentIndex(1))

        browse_button = QPushButton("Browse Memory Vault")
        browse_button.clicked.connect(lambda: self.tabs.setCurrentIndex(2))

        actions_layout.addWidget(create_button)
        actions_layout.addWidget(browse_button)

        layout.addWidget(actions_group)

        # Add stretching space at the bottom
        layout.addStretch()

        return tab
    
    def create_memory_form_tab(self):
        """Create the tab for creating new memories."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Title section
        title_layout = QFormLayout()

        self.memory_title_input = QLineEdit()
        self.memory_title_input.setPlaceholderText("Enter a title for your memory")

        title_layout.addRow("Memory Title:", self.memory_title_input)
        layout.addLayout(title_layout)

        # Content section
        content_group = QGroupBox("Memory Content")
        content_layout = QVBoxLayout(content_group)

        content_label = QLabel("What would you like to say to your future self?")
        self.memory_content_input = QTextEdit()

        content_layout.addWidget(content_label)
        content_layout.addWidget(self.memory_content_input)

        layout.addWidget(content_group)

        # Unlock settings
        unlock_group = QGroupBox("Unlock Settings")
        unlock_layout = QFormLayout(unlock_group)

        self.unlock_type_combo = QComboBox()
        self.unlock_type_combo.addItems(["Specific Date", "Time Interval", "Random Date"])

        self.unlock_date_edit = QDateEdit()
        self.unlock_date_edit.setDate(QDate.currentDate().addMonths(1)) # Defaulting to one month from now
        self.unlock_date_edit.setCalendarPopup(True)

        unlock_layout.addRow("Unlock Type:", self.unlock_type_combo)
        unlock_layout.addRow("Unlock Date:", self.unlock_date_edit)

        layout.addWidget(unlock_group)

        # Category and tags
        metadata_group = QGroupBox("Categorization")
        metadata_layout = QFormLayout(metadata_group)

        self.category_combo = QComboBox()
        # Populate with categories from database
        categories = self.memory_keeper.get_categories()
        for category in categories:
            self.category_combo.addItem(category["name"], category["id"])

        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Enter tags separated by commas")

        metadata_layout.addRow("Category:", self.category_combo)
        metadata_layout.addRow("Tags:", self.tags_input)

        layout.addWidget(metadata_group)

        # Additional settings
        additional_group = QGroupBox("Additional Information")
        additional_layout = QFormLayout(additional_group)

        self.mood_combo = QComboBox()
        self.mood_combo.addItems(["Happy", "Reflective", "Excited", "Curious", "Hopeful", "Anxious", "Proud"])

        self.importance_spin = QSpinBox()
        self.importance_spin.setRange(1, 5)
        self.importance_spin.setValue(3)
        self.importance_spin.setPrefix("★ ")

        additional_layout.addRow("Current Mood:", self.mood_combo)
        additional_layout.addRow("Importance:", self.importance_spin)

        layout.addWidget(additional_group)

        # Submit button
        submit_button = QPushButton("Create Memory")
        submit_button.clicked.connect(self.save_memory)
        layout.addWidget(submit_button)

        return tab
    
    def create_vault_tab(self):
        """Create the tab for browsing locked memories."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Placeholder - This will eventually show all locked memories
        info_label = QLabel("Your Memory Vault - Where your memories are securely stored until unlock time")
        info_label.setWordWrap(True)

        # This tab will be implemented with a scrollable list of memory cards
        under_construction = QLabel("This tab is under construction")

        layout.addWidget(info_label)
        layout.addWidget(under_construction)

        return tab
    
    def create_unlocked_tab(self):
        """Create the tab for viewing unlocked memories."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Placeholder - This will eventually show all unlocked memories
        info_label = QLabel("Your Unlocked Memories - Revisit memories from your past self")
        info_label.setWordWrap(True)

        # This tab will be implemented with a scrollable list of unlocked memory cards
        under_construction = QLabel("This tab is under construction")

        layout.addWidget(info_label)
        layout.addWidget(under_construction)

        return tab
    
    def save_memory(self):
        """Save a new memory from the form data."""
        # Get form data
        title = self.memory_title_input.text().strip()
        content = self.memory_content_input.toPlainText().strip()

        # Validate required fields
        if not title or not content:
            QMessageBox.warning(self, "Missing Information",
                                "Please provide both a title and content for your memory.")
            return
        
        # Get unlock date
        qdate = self.unlock_date_edit.date()
        unlock_date = datetime(qdate.year(), qdate.month(), qdate.day())

        # Get category
        category_id = self.category_combo.currentData()

        # Get tags (split by comma and strip whitespace)
        tags_text = self.tags_input.text().strip()
        tags = [tag.strip() for tag in tags_text.split(",")] if tags_text else None

        # Get mood and importance 
        mood = self.mood_combo.currentText()
        importance = self.importance_spin.value()

        # Save the memory
        try:
            self.memory_keeper.create_memory(
                title = title,
                content = content,
                unlock_date = unlock_date,
                category = category_id,
                tags = tags,
                mood = mood,
                importance = importance
            )

            # Show success message
            QMessageBox.information(self, "Memory Created",
                                    "Your memory has been successfully saved and will unlock on the specified date.")
            
            # Clear the form
            self.memory_title_input.clear()
            self.memory_content_input.clear()
            self.tags_input.clear()

            # Refresh the dashboard
            self.refresh_dashboard()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save memory: {str(e)}")

    def check_unlockable_memories(self):
        """Check if there are any memories ready to be unlocked."""
        unlockable_memories = self.memory_keeper.get_unlockable_memories()

        if unlockable_memories:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Memories Ready to Unlock")
            msg.setText(f"You have {len(unlockable_memories)} memories ready to unlock!")
            msg.setInformativeText("Would you like to view them now?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            if msg.exec_() == QMessageBox.Yes:
                # Switch to the unlocked memories tab
                self.tabs.setCurrentIndex(3)

    def refresh_dashboard(self):
        """Refresh the dashboard with updated data."""
        # This is a placeholder - in the real implementation, this will update the dashboard
        # For now, we'll just recreate the dashboard tab
        new_dashboard = self.create_dashboard_tab()
        self.tabs.removeTab(0)
        self.tabs.insertTab(0, new_dashboard, "Dashboard")
        self.tabs.setCurrentIndex(0)

def main():
    """Main entry point for MemoryKeeper"""
    print("Welcome to MemoryKeeper - Your Digital Time Capsule!")

    # Initialize the memory keeper backend
    memory_keeper = MemoryKeeper()

    try:
        # Create and run
        app = QApplication(sys.argv)
        app.setStyle('Fusion')

        main_window = MemoryKeeperApp(memory_keeper)
        main_window.show()

        sys.exit(app.exec_())

    except Exception as e:
        print(f"An error occurred: {e}")
        return 1
        
    return 0
    
if __name__ == "__main__":
    main()