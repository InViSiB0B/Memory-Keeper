from datetime import datetime, timedelta
import json
import shutil
import sqlite3
import sys
import tempfile
import uuid
import zipfile
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QTextEdit,
                             QListWidget, QCalendarWidget, QFileDialog,
                             QFormLayout, QGroupBox, QSplitter, QTabWidget,
                             QMessageBox, QComboBox,QScrollArea, QFrame, QLineEdit, 
                             QDateEdit, QDateTimeEdit, QSpinBox, QListWidgetItem)
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
    
    def get_locked_memories(self, category_id = None, sort_field = "unlock_date", 
                            sort_order = "ASC", search_text = "", limit = 50):
        """
        Get locked memories with filtering and sorting options.

        Args:
            category_id: Filter by category ID (None for all categories)
            sort_field: Field to sort by (unlock_date, created_date, importance)
            sort_order: Sort direction (ASC or DESC)
            search_text: Filter by title or tags containing this text
            limit: Maximum number of memories to return

        Returns:
            List of memory dictionaries
        """
        conn = self.get_db_connection()
        conn.row_factory = sqlite3.Row # This makes the rows accessible by column name
        cursor = conn.cursor()

        # Start building the query
        query = """
            SELECT m.id, m.title, m.created_date, m.unlock_date,
                    m.category, m.importance, m.mood, GROUP_CONCAT(mt.tag) as tags
            FROM memories m
            LEFT JOIN memory_tags mt ON m.id = mt.memory_id
            WHERE m.is_unlocked = 0
        """

        # Parameters for the query
        params = []

        # Add category filter if specified
        if category_id:
            query += " AND m.category = ?"
            params.append(category_id)
        
        # Add searc filter if specified
        if search_text:
            query += """ AND (
                LOWER(m.title) LIKE ?
                OR EXISTS (
                    SELECT 1 FROM memory_tags
                    WHERE memory_id = m.id AND LOWER(tag) LIKE?
                )
            )"""
            search_param = f"%{search_text}%"
            params.extend([search_param, search_param])

        # Group by memory ID to combine tags
        query += " GROUP by m.id"

        # Add sorting
        query += f" ORDER by m.{sort_field} {sort_order}"

        #Add limit
        query += " LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        #Convert to list of dictionaries
        memories = []
        for row in cursor.fetchall():
            memory = dict(row)
            # Convert tags from comma-separated string to list if not None
            if memory.get("tags"):
                memory["tags"] = memory["tags"].split(",")
            memories.append(memory)
        
        conn.close()
        return memories
    
    def get_memories_with_filters(self, filters):
        """
        Get memories with complex filtering options.

        Args:
            filters: Dictionary of filter parameters
            - is_unlocked: 1 for unlocked, 0 for locked
            - unlock_after date: Only memories unlocked after this date
            - category_id: Filter by category
            - has_responses: True/False for memories with/without responses

        Returns:
            List of memory dictionaries
        """
        conn = self.get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Start building the query
        query = """
            SELECT m.id, m.title, m.content, m.media_path, m.created_date,
                   m.unlock_date, m.category, m.mood, m.importance
            FROM memories m
        """

        # Join with responses table if needed
        if filters.get("has_responses") is not None:
            query += " LEFT JOIN responses r ON m.id = r.memory_id"

        # Where clause
        query += " WHERE 1 = 1" # Start with a true condition

        # Parameters for the query
        params = []

        # Apply filters
        if "is_unlocked" in filters:
            query += " AND m.is_unlocked = ?"
            params.append(filters["is_unlocked"])

        if "unlocked_after_date" in filters:
            query += " AND m.unlock_date >= ?"
            params.append(filters["unlock_after_date"])

        if "category_id" in filters:
            query += " AND m.category = ?"
            params.append(filters["category_id"])

        if "has_responses" in filters:
            if filters["has_responses"]:
                query += " AND r.id IS NOT NULL"
            else:
                query += " AND r.id IS NULL"

        # Group by memory id to avoid duplicates from the join
        query += " GROUP BY m.id"

        # Order by unlock date (most recent first)
        query += " ORDER BY m.unlock_date DESC"

        cursor.execute(query, params)

        # Convert to list of dictionaries
        memories = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return memories
    
    def get_memory_by_id(self, memory_id):
        """
        Get a single memory by its ID.

        Args:
            memory_id: The unique ID of the memory

        Returns:
            Memory dictionary or None if not found
        """
        conn = self.get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get the memory
        cursor.execute("""
            SELECT m.id, m.title, m.content, m.media_path, m.created_date,
                m.unlock_date, m.category, m.mood, m.importance
            FROM memories m
            WHERE m.id = ? 
        """, (memory_id,))

        row = cursor.fetchone()

        if not row:
            conn.close()
            return None
        
        memory = dict(row)

        # Get tags for this memory
        cursor.execute("""
            SELECT tag FROM memory_tags
            WHERE memory_id = ?
        """, (memory_id,))

        tags = [row[0] for row in cursor.fetchall()]
        if tags:
            memory["tags"] = tags

        conn.close()
        return memory
    
    def get_responses_for_memory(self, memory_id):
        """
        Get all responses for a specific memory.

        Args:
            memory_id: The unique ID of the memory

        Returns:
            List of response dictionaries
        """
        conn = self.get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, response_content, response_date, response_mood
            FROM responses
            WHERE memory_id = ?
            ORDER BY response_date DESC
        """, (memory_id,))

        responses = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return responses
    
    def delete_memory(self, memory_id):
        """
        Delete a memory and all its associated data (tags and responses).

        Args:
            memory_id: ID of the memory to delete

        Returns:
            Boolean indicating success
        """

        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            # Start a transaction
            conn.execute("BEGIN TRANSACTION")

            # Delete associated responses
            cursor.execute("DELETE FROM responses WHERE memory_id = ?", (memory_id,))

            # Delete associated tags
            cursor.execute("DELETE FROM memory_tags WHERE memory_id = ?", (memory_id,))

            # Delete the memory itself
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))

            # Check if any rows were affected
            success = cursor.rowcount > 0

            # Commit the transaction
            conn.commit()

            return success
        
        except Exception as e:
            # If anything goes wrong, roll back the transaction
            conn.rollback()
            print(f"Error deleting memory: {e}")
            return False
        
        finally:
            conn.close()

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
                created = datetime.fromisoformat(memory["created_date"]).strftime("%B %d, %Y")
                unlock = datetime.fromisoformat(memory["unlock_date"]).strftime("%B %d, %Y")

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
        actions_layout = QVBoxLayout(actions_group)

        # Main actions row (first row)
        main_actions = QHBoxLayout()

        create_button = QPushButton("Create New Memory")
        create_button.clicked.connect(lambda: self.tabs.setCurrentIndex(1))

        browse_button = QPushButton("Browse Memory Vault")
        browse_button.clicked.connect(lambda: self.tabs.setCurrentIndex(2))

        main_actions.addWidget(create_button)
        main_actions.addWidget(browse_button)

        # Add the first row to the actions layout
        actions_layout.addLayout(main_actions)

        # Import/Export row (second row)
        import_export_actions = QHBoxLayout()

        export_button = QPushButton("Export Memories")
        export_button.setToolTip("Create a backup of all your memories")
        export_button.clicked.connect(self.export_memories)

        import_button = QPushButton("Import Memories")
        import_button.setToolTip("Create a backup of all your memories")
        import_button.clicked.connect(self.import_memories)

        import_export_actions.addWidget(export_button)
        import_export_actions.addWidget(import_button)

        # Add the second row to the actions layout
        actions_layout.addLayout(import_export_actions)

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

        # Header section
        header_label = QLabel("Your Memory Vault")
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)

        description_label = QLabel(
            "This is where your memories are securely stored until their unlock time. "
            "Browse through your future surprises, but remember - you can't peek "
            "inside until the time is right!"
        )
        description_label.setWordWrap(True)

        layout.addWidget(header_label)
        layout.addWidget(description_label)

        # Filter and search section
        filter_group = QGroupBox("Filter Memories")
        filter_layout = QHBoxLayout(filter_group)

        # Category filter
        category_label = QLabel("Category:")
        self.vault_category_filter = QComboBox()
        self.vault_category_filter.addItem("All Categories", None)

        # Populate with categories from database
        categories = self.memory_keeper.get_categories()
        for category in categories:
            self.vault_category_filter.addItem(category["name"], category["id"])

        # Sort options
        sort_label = QLabel("Sort by:")
        self.vault_sort_combo = QComboBox()
        self.vault_sort_combo.addItems(["Unlock Date (Soonest)", "Unlock Date (Latest)", 
                                        "Creation Date (Newest)", "Creation Date (Oldest)",
                                         "Importance (Highest)", "Importance (Lowest)"])
        
        # Connect filters to update function
        self.vault_category_filter.currentIndexChanged.connect(self.refresh_vault_memories)
        self.vault_sort_combo.currentIndexChanged.connect(self.refresh_vault_memories)

        # Search box
        self.vault_search_box = QLineEdit()
        self.vault_search_box.setPlaceholderText("Search memories by title or tags...")
        self.vault_search_box.textChanged.connect(self.refresh_vault_memories)

        # Arrange filter widgets
        filter_layout.addWidget(category_label)
        filter_layout.addWidget(self.vault_category_filter)
        filter_layout.addWidget(sort_label)
        filter_layout.addWidget(self.vault_sort_combo)

        layout.addWidget(filter_group)
        layout.addWidget(self.vault_search_box)

        # Scrollable area for memory cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()

        self.vault_memories_layout = QVBoxLayout(scroll_content)
        self.vault_memories_layout.setAlignment(Qt.AlignTop)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)

        # Initial load of memories
        self.refresh_vault_memories()
    
        return tab
    
    def refresh_vault_memories(self):
        """Refresh the list of memories in the vault tab based on the current filters."""
        # Clear existing memory cards
        for i in reversed(range(self.vault_memories_layout.count())):
            widget = self.vault_memories_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Get filter values
        category_id = self.vault_category_filter.currentData()
        sort_option = self.vault_sort_combo.currentText()
        search_text = self.vault_search_box.text().lower()

        # Get locked memories with appropriate filters
        memories = self.get_filtered_locked_memories(category_id, sort_option, search_text)

        if memories:
            # Create a memory card for each memory
            for memory in memories:
                memory_card = self.create_memory_card(memory)
                self.vault_memories_layout.addWidget(memory_card)
        else:
            # Show a message if no memories are found
            no_memories_label = QLabel("No locked memories found with the current filters.")
            no_memories_label.setAlignment(Qt.AlignCenter)
            self.vault_memories_layout.addWidget(no_memories_label)

    def get_filtered_locked_memories(self, category_id = None, sort_option = "Unlock Date (Soonest)", search_text = ""):
        """
        Get locked memories from the database with filtering and sorting.

        Args:
            category_id: Filter by category ID (None for all categories)
            sort_option: How to sort the results
            search_text: Filter by title or tags containing this text

        Returns:
            List of the memory dictionaries
        """
        
        # Convert sort option to parameters for the query
        sort_field = "unlock_date"
        sort_order = "ASC"

        if "Creation Date" in sort_option:
            sort_field = "created_date"
        elif "Importance" in sort_option:
            sort_field = "importance"
            sort_order = "DESC"

        if "Latest" in sort_option or "Oldest" in sort_option or "Newest" in sort_option:
            sort_order = "DESC"

        return self.memory_keeper.get_locked_memories(
            category_id = category_id,
            sort_field = sort_field,
            sort_order = sort_order,
            search_text = search_text
        )

    def create_memory_card(self, memory):
        """
        Create a card widget for a locked memory.

        Args:
            memory: Dictionary containing memory information

        Returns:
            QFrame widget representing the memory
        """
        # Create card frame
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setFrameShadow(QFrame.Raised)
        card.setStyleSheet("QFrame { border: 1px solid #CCCCCC; border-radius: 8px; background-color: #F8F8F8; margin: 5px; }")

        # Create layout for the new card
        card_layout = QVBoxLayout(card)

        # Format dates
        created_date = datetime.fromisoformat(memory["created_date"]).strftime("%B %d, %Y")
        unlock_date = datetime.fromisoformat(memory["unlock_date"]).strftime("%B %d, %Y")

        # Days until unlock
        days_until = (datetime.fromisoformat(memory["unlock_date"]) - datetime.now()).days
        days_text = f"{days_until} days remaining" if days_until > 0 else "Unlocks today!"

        # Create header with title and actions
        header_layout = QHBoxLayout()

        title_label = QLabel(memory["title"])
        title_label.setFont(QFont("Arial", 12, QFont.Bold))

        # Container for action buttons
        buttons_layout = QHBoxLayout()

        # Add unlock button if the memory is ready to be unlocked
        if days_until <= 0:
            unlock_button = QPushButton("Unlock Now")
            unlock_button.setStyleSheet("background-color: #E0FFE0;")
            unlock_button.clicked.connect(lambda: self.unlock_and_view_memory(memory["id"]))
            buttons_layout.addWidget(unlock_button)

            # Change the days text
            days_text = "Ready to unlock now!"
        else:
            days_text = f"{days_until} days remaining"

        # Add delete button
        delete_button = QPushButton("Delete")
        delete_button.setStyleSheet("background-color: #FFE0E0;")
        delete_button.clicked.connect(lambda: self.confirm_delete_memory(memory["id"], is_locked = True))
        buttons_layout.addWidget(delete_button)

        header_layout.addWidget(title_label, 1)
        header_layout.addLayout(buttons_layout)

        # Info section
        info_layout = QHBoxLayout()
        
        # Left side info
        left_info = QVBoxLayout()
        created_label = QLabel(f"Created: {created_date}")
        unlock_label = QLabel(f"Unlocks: {unlock_date}")
        left_info.addWidget(created_label)
        left_info.addWidget(unlock_label)

        # Right side info
        right_info = QVBoxLayout()
        countdown_label = QLabel(days_text)
        countdown_label.setStyleSheet("font-weight: bold; color: #2C6694;")

        # Get category name if available
        category_name = "Uncategorized"
        if memory.get("category"):
            categories = self.memory_keeper.get_categories()
            for category in categories:
                if category["id"] == memory["category"]:
                    category_name = category["name"]
                    break

        category_label = QLabel(f"Category: {category_name}")
        right_info.addWidget(countdown_label)
        right_info.addWidget(category_label)

        # Add left and right info to the info layout
        info_layout.addLayout(left_info)
        info_layout.addStretch()
        info_layout.addLayout(right_info)

        # Add components to card layout
        card_layout.addWidget(title_label)
        card_layout.addLayout(info_layout)

        # If the memory has importance, show stars
        if "importance" in memory and memory ["importance"]:
            importance = int(memory["importance"])
            stars = "★" * importance + "☆" * (5 - importance)
            importance_label = QLabel(stars)
            importance_label.setStyleSheet("color:gold;")
            card_layout.addWidget(importance_label)

        # Add Tags if available
        if memory.get("tags"):
            tags_text = ", ".join(memory["tags"])
            tags_label = QLabel(f"Tags: {tags_text}")
            tags_label.setStyleSheet("font-style: italic; color: #666666;")
            card_layout.addWidget(tags_label)

        return card

    
    def create_unlocked_tab(self):
        """Create the tab for viewing unlocked memories."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Header section
        header_label = QLabel("Your Unlocked Memories")
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)

        description_label = QLabel(
            "These are messages from your past self that have reached their unlock date. "
            "Take a moment to reflect on how you've changed and grown since you wrote them."
        )
        description_label.setWordWrap(True)

        layout.addWidget(header_label)
        layout.addWidget(description_label)

        # Create a splitter for the main content
        splitter = QSplitter(Qt.Horizontal)
        self.unlocked_splitter = splitter  # Store reference

        # Left side - List of unlocked memories
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)  # Reduce margins
        
        # Filter options
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter by:")
        self.unlocked_filter_combo = QComboBox()
        self.unlocked_filter_combo.addItems([
            "All Unlocked", 
            "Recent (Last 30 Days)",
            "By Category", 
            "With Responses", 
            "Without Responses"
        ])
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.unlocked_filter_combo, 1)  # Give it more space
        left_layout.addLayout(filter_layout)

        # Category sub-filter (initially hidden)
        self.unlocked_category_filter = QComboBox()
        self.unlocked_category_filter.setVisible(False)
        left_layout.addWidget(self.unlocked_category_filter)

        # Memory list
        self.unlocked_memory_list = QListWidget()
        self.unlocked_memory_list.setSelectionMode(QListWidget.SingleSelection)
        left_layout.addWidget(self.unlocked_memory_list, 1)  # Give it stretch

        # Connect signals AFTER creating widgets
        self.unlocked_filter_combo.currentIndexChanged.connect(self.filter_unlocked_memories)
        self.unlocked_category_filter.currentIndexChanged.connect(self.filter_unlocked_memories)
        self.unlocked_filter_combo.currentIndexChanged.connect(self.toggle_category_filter)
        self.unlocked_memory_list.currentItemChanged.connect(self.display_unlocked_memory)

        # Right side - Memory details and response area
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)  # Reduce margins

        # Create a scroll area for memory content
        content_scroll = QScrollArea()
        content_scroll.setWidgetResizable(True)
        self.unlocked_content_scroll = content_scroll  # Store reference

        # Create content widget and layout
        content_widget = QWidget()
        self.unlocked_content_widget = content_widget  # Store reference
        self.memory_content_layout = QVBoxLayout(content_widget)  # Store reference
        self.memory_content_layout.setAlignment(Qt.AlignTop)  # Align to top
        content_scroll.setWidget(content_widget)

        # Default content - shown when no memory is selected
        default_label = QLabel("Select a memory from the list to view its contents.")
        default_label.setAlignment(Qt.AlignCenter)
        self.memory_content_layout.addWidget(default_label)

        # Add the content scroll area to the right layout
        right_layout.addWidget(content_scroll, 3)  # Give content more space

        # Response section
        response_group = QGroupBox("Your Response")
        response_layout = QVBoxLayout(response_group)

        response_label = QLabel(
            "Reflect on this memory from your past self. How do you feel about it now?"
        )
        response_label.setWordWrap(True)

        self.response_text_edit = QTextEdit()
        self.response_text_edit.setPlaceholderText("Type your response here...")
        self.response_text_edit.setEnabled(False)  # Disabled until a memory is selected

        mood_layout = QHBoxLayout()
        mood_label = QLabel("Your current mood:")
        self.response_mood_combo = QComboBox()
        self.response_mood_combo.addItems([
            "Happy", "Reflective", "Surprised", "Nostalgic",
            "Amused", "Grateful", "Inspired", "Other"
        ])
        self.response_mood_combo.setEnabled(False)  # Disabled until a memory is selected
        mood_layout.addWidget(mood_label)
        mood_layout.addWidget(self.response_mood_combo, 1)

        self.save_response_button = QPushButton("Save Response")
        self.save_response_button.setEnabled(False)  # Disabled until a memory is selected

        # Connect signals AFTER creating widgets
        self.save_response_button.clicked.connect(self.save_memory_response)

        # Add widgets to response layout
        response_layout.addWidget(response_label)
        response_layout.addWidget(self.response_text_edit)
        response_layout.addLayout(mood_layout)
        response_layout.addWidget(self.save_response_button)

        # Add the response section to the right layout
        right_layout.addWidget(response_group, 1)

        # Add the left and right widgets to the splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        # Set the initial sizes of the splitter
        total_width = 1000
        splitter.setSizes([int(total_width * 0.4), int(total_width * 0.6)])

        # Add the splitter to the main layout
        layout.addWidget(splitter, 1)  # Give it stretch

        # Store reference to the currently displayed memory
        self.current_memory_id = None

        # Populate unlocked memories list
        self.populate_categories_filter()
        self.load_unlocked_memories()

        # Store a reference to this tab
        self.unlocked_tab_widget = tab
        
        return tab
    
    def toggle_category_filter(self):
        """Show of hide the category filter based on the main filter selection."""
        show_category = self.unlocked_filter_combo.currentText() == "By Category"
        self.unlocked_category_filter.setVisible(show_category)

        if show_category:
            # Make sure categories are loaded
            self.populate_categories_filter()

    def populate_categories_filter(self):
        """Populate the category filter dropdown."""
        self.unlocked_category_filter.clear()
        self.unlocked_category_filter.addItem("All Categories", None)

        categories = self.memory_keeper.get_categories()
        for category in categories:
            self.unlocked_category_filter.addItem(category["name"], category["id"])
    
    def load_unlocked_memories(self):
        """Load unlocked memories into the list widget."""
        self.unlocked_memory_list.clear()

        # Get Unlocked memories
        memories = self.get_filtered_unlocked_memories()

        if memories:
            for memory in memories:
                # Create a list item for each memory
                created_date = datetime.fromisoformat(memory["created_date"]).strftime("%B %d, %Y")
                unlock_date = datetime.fromisoformat(memory["unlock_date"]).strftime("%B %d, %Y")

                # Format the item text
                item_text = f"{memory['title']}\nCreated: {created_date} | Unlocked: {unlock_date}"

                # Create item and store the memory id as item date
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, memory["id"])

                self.unlocked_memory_list.addItem(item)
        else:
            # Add a placeholder item if no memories are found
            placeholder = QListWidgetItem("No unlocked memories found")
            placeholder.setFlags(placeholder.flags() & ~Qt.ItemIsSelectable)
            self.unlocked_memory_list.addItem(placeholder)
    
    def filter_unlocked_memories(self):
        """Apply filters to the unlocked memories list."""
        self.load_unlocked_memories()

    def get_filtered_unlocked_memories(self):
        """
        Get unlocked memories from the database with filtering.

        Returns:
            List of memory dictionaries
        """
        filter_option = self.unlocked_filter_combo.currentText()

        # Determine filter parameters
        filter_params = {
            "is_unlocked": 1
        }

        if filter_option == "Recent (Last 30 Days)":
            # Calculate date 30 days ago
            thirty_days_ago = (datetime.now() - timedelta(days = 30)).isoformat()
            filter_params["unlock_after_date"] = thirty_days_ago

        elif filter_option == "By Category":
            category_id = self.unlocked_category_filter.currentData()
            if category_id:
                filter_params["category_id"] = category_id

        elif filter_option == "With Responses":
            filter_params["has_responses"] = True

        elif filter_option == "Without Responses":
            filter_params["has_responses"] = False

        return self.memory_keeper.get_memories_with_filters(filter_params)
    
    def display_unlocked_memory(self, current, previous):
        """
        Display the selected unlocked memory's content.

        Args:
            current: The currently selected item
            previous: The previously selected item
        """

        # Clear the current memory ID
        self.current_memory_id = None
        
        # Clear the response inputs regardless of selection
        if hasattr(self, 'response_text_edit'):
            self.response_text_edit.clear()
            self.response_text_edit.setEnabled(False)
        
        if hasattr(self, 'response_mood_combo'):
            self.response_mood_combo.setEnabled(False)
        
        if hasattr(self, 'save_response_button'):
            self.save_response_button.setEnabled(False)
        
        # Make sure we have a content layout to work with
        if not hasattr(self, 'memory_content_layout') or not self.memory_content_layout:
            # Create a new widget and layout
            self.unlocked_content_widget = QWidget()
            self.memory_content_layout = QVBoxLayout(self.unlocked_content_widget)
            if hasattr(self, 'unlocked_content_scroll'):
                self.unlocked_content_scroll.setWidget(self.unlocked_content_widget)
        
        # Clear current content safely
        while self.memory_content_layout.count():
            item = self.memory_content_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        
        # Check if we have a valid selection
        if not current or not (current.flags() & Qt.ItemIsSelectable):
            # Show default message
            default_label = QLabel("Select a memory from the list to view its contents.")
            default_label.setAlignment(Qt.AlignCenter)
            self.memory_content_layout.addWidget(default_label)
            return
        
        # Get memory ID from the selected item
        try:
            memory_id = current.data(Qt.UserRole)
            self.current_memory_id = memory_id
            
            # Get the full memory details
            memory = self.memory_keeper.get_memory_by_id(memory_id)
            if not memory:
                error_label = QLabel("Error: Could not load memory details.")
                self.memory_content_layout.addWidget(error_label)
                return
            
            # Set up response inputs now that we have a valid memory
            if hasattr(self, 'response_text_edit'):
                self.response_text_edit.setEnabled(True)
            
            if hasattr(self, 'response_mood_combo'):
                self.response_mood_combo.setEnabled(True)
            
            if hasattr(self, 'save_response_button'):
                self.save_response_button.setEnabled(True)
            
            # Display the memory content
            self.display_memory_content(memory)
        
        except Exception as e:
            print(f"Error displaying memory: {e}")
            error_label = QLabel(f"An error occurred: {str(e)}")
            error_label.setWordWrap(True)
            error_label.setStyleSheet("color: red;")
            self.memory_content_layout.addWidget(error_label)

    def display_memory_content(self, memory):
        """
        Create and display the widgets for memory content.

        Args:
            memory: Dictionary with memory details
        """
        try:
            # Memory Title
            title_label = QLabel(memory["title"])
            title_label.setFont(QFont("Arial", 16, QFont.Bold))
            self.memory_content_layout.addWidget(title_label)
            
            # Delete button
            delete_button = QPushButton("Delete Memory")
            delete_button.setStyleSheet("background-color: #FFCCCC;")
            delete_button.clicked.connect(lambda: self.confirm_delete_memory(memory["id"], is_locked=False))
            self.memory_content_layout.addWidget(delete_button)
            
            # Memory metadata
            created_date = datetime.fromisoformat(memory["created_date"]).strftime("%B %d, %Y")
            unlock_date = datetime.fromisoformat(memory["unlock_date"]).strftime("%B %d, %Y")
            
            metadata_label = QLabel(f"Created: {created_date} | Unlocked: {unlock_date}")
            self.memory_content_layout.addWidget(metadata_label)
            
            # Get category name
            category_name = "Uncategorized"
            if memory.get("category"):
                categories = self.memory_keeper.get_categories()
                for category in categories:
                    if category["id"] == memory["category"]:
                        category_name = category["name"]
                        break
            
            category_label = QLabel(f"Category: {category_name}")
            self.memory_content_layout.addWidget(category_label)
            
            # Show original mood if available
            if memory.get("mood"):
                mood_label = QLabel(f"Your mood when writing: {memory['mood']}")
                self.memory_content_layout.addWidget(mood_label)
            
            # Importance indicator if available
            if memory.get("importance"):
                importance = int(memory["importance"])
                stars = "★" * importance + "☆" * (5 - importance)
                importance_label = QLabel(f"Importance: {stars}")
                self.memory_content_layout.addWidget(importance_label)
            
            # Add a separator
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            self.memory_content_layout.addWidget(separator)
            
            # Memory content
            content_label = QLabel(memory["content"])
            content_label.setWordWrap(True)
            content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            content_label.setStyleSheet("font-size: 12pt; margin: 10px;")
            self.memory_content_layout.addWidget(content_label)
            
            # Add a separator before responses
            separator2 = QFrame()
            separator2.setFrameShape(QFrame.HLine)
            separator2.setFrameShadow(QFrame.Sunken)
            self.memory_content_layout.addWidget(separator2)
            
            # Previous responses section
            responses_label = QLabel("Your Previous Responses:")
            responses_label.setFont(QFont("Arial", 12, QFont.Bold))
            self.memory_content_layout.addWidget(responses_label)
            
            # Get responses for this memory
            responses = self.memory_keeper.get_responses_for_memory(memory["id"])
            
            if responses:
                for response in responses:
                    response_date = datetime.fromisoformat(response["response_date"]).strftime("%B %d, %Y")
                    date_label = QLabel(f"Response from {response_date}")
                    date_label.setStyleSheet("font-weight: bold;")
                    self.memory_content_layout.addWidget(date_label)
                    
                    # Response mood if available
                    if response.get("response_mood"):
                        mood_label = QLabel(f"Mood: {response['response_mood']}")
                        self.memory_content_layout.addWidget(mood_label)
                    
                    # Response content
                    content_text = QLabel(response["response_content"])
                    content_text.setWordWrap(True)
                    self.memory_content_layout.addWidget(content_text)
                    
                    # Add a small spacer
                    spacer = QFrame()
                    spacer.setFrameShape(QFrame.HLine)
                    spacer.setFrameShadow(QFrame.Sunken)
                    self.memory_content_layout.addWidget(spacer)
            else:
                no_responses = QLabel("You haven't responded to this memory yet.")
                no_responses.setAlignment(Qt.AlignCenter)
                no_responses.setStyleSheet("font-style: italic; color: #666666;")
                self.memory_content_layout.addWidget(no_responses)
            
            # Add a final stretch to push everything up
            self.memory_content_layout.addStretch()

        except Exception as e:
            print(f"Error in display_memory_content: {str(e)}")
            error_label = QLabel(f"Error displaying memory content: {str(e)}")
            error_label.setStyleSheet("color: red;")
            error_label.setWordWrap(True)
            self.memory_content_layout.addWidget(error_label)

    def save_memory_response(self):
        """Save the user's response to the current memory."""
        if not self.current_memory_id:
            QMessageBox.warning(self, "No Memory Selected", "Please select a memory to respond to.")
            return
        
        # Get response content
        response_text = self.response_text_edit.toPlainText().strip()
        if not response_text:
            QMessageBox.warning(self, "Empty Response", "Please enter a reponse before saving.")
            return
        
        # Get selected mood
        mood = self.response_mood_combo.currentText()
        if mood == "Other":
            mood = None # Don't record "Other" as a mood

        try:
            # Save the response
            self.memory_keeper.add_response(
                memory_id = self.current_memory_id,
                response_content = response_text,
                mood = mood
            )

            # Show success message
            QMessageBox.information(self, "Response Saved",
                                    "Your response has been saved successfully.")
            
            # Clear the response area
            self.response_text_edit.clear()

            # Refresh the memory display to show the new response
            self.display_unlocked_memory(self.unlocked_memory_list.currentItem(), None)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save response: {str(e)}")
                            
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
            memory_id = self.memory_keeper.create_memory(
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

            # Detemine if memory is immediately unlockable
            is_unlockable = unlock_date <= datetime.now()

            # Refresh all affected tabs
            self.refresh_dashboard() # Always refresh the dashboard

            if is_unlockable:
                # If the memory is immediately unlockable, process it now
                self.memory_keeper.unlock_memory(memory_id)
                self.load_unlocked_memories() # Refresh unlocked memories tab
            else:
                # Otherwise, it goes to the vaule
                self.refresh_vault_memories() # Refresh vault tab

            # Switch to the Dashboard tab to show the updated stats
            self.tabs.setCurrentIndex(0)


        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save memory: {str(e)}")

    def check_unlockable_memories(self):
        """Check if there are any memories ready to be unlocked."""
        unlockable_memories = self.memory_keeper.get_unlockable_memories()

         # First, unlock all the memories that are ready
        unlocked_count = 0
        if unlockable_memories:
            for memory in unlockable_memories:
                success = self.memory_keeper.unlock_memory(memory["id"])
                if success:
                    unlocked_count += 1

        # Only show the notification if we've actually unlocked some memories
        if unlocked_count > 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Memories Unlocked")
            msg.setText(f"{unlocked_count} memories have been unlocked!")
            msg.setInformativeText("Would you like to view them now?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            if msg.exec_() == QMessageBox.Yes:
                # Switch to the unlocked memories tab
                self.tabs.setCurrentIndex(3)
                # Refresh the unlocked memories list
                self.load_unlocked_memories()

    def refresh_dashboard(self):
        """Refresh the dashboard with updated data."""
        # This is a placeholder - in the real implementation, this will update the dashboard
        # For now, we'll just recreate the dashboard tab
        new_dashboard = self.create_dashboard_tab()
        self.tabs.removeTab(0)
        self.tabs.insertTab(0, new_dashboard, "Dashboard")
        self.tabs.setCurrentIndex(0)

    def confirm_delete_memory(self, memory_id, is_locked = True):
        """
        Show confirmation dialog and delete memory if confirmed.

        Args:
            memory_id: ID of memory to delete
            is_locked: Whether the memory is in the locked vault (True) or in the unlocked tab (False)
        """
        confirm = QMessageBox()
        confirm.setIcon(QMessageBox.Warning)
        confirm.setWindowTitle("Confirm Deletion")
        confirm.setText("Are you sure you want to delete this memory?")
        confirm.setInformativeText("This action cannot be undone. All content and responses associated with "
                                    "this memory will be permanently deleted.")
        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm.setDefaultButton(QMessageBox.No)

        if confirm.exec_() == QMessageBox.Yes:
            # User confirmed deletion
            success = self.memory_keeper.delete_memory(memory_id)

            if success:
                QMessageBox.information(self, "Memory Deleted",
                                        "The memory has been permanently deleeted.")
                
                # Refresh the appropriate tab
                if is_locked:
                    self.refresh_vault_memories()
                else:
                    # For unlocked tab, clear the display and refresh list
                    self.current_memory_id = None
                    self.load_unlocked_memories()

                    # Clear the reponse area
                    self.response_text_edit.clear()
                    self.response_text_edit.setEnabled(False)
                    self.response_mood_combo.setEnabled(False)
                    self.save_response_button.setEnabled(False)

                    # Clear current selection
                    self.unlocked_memory_list.clearSelection()

            else:
                QMessageBox.critical(self, "Error,"
                                    "Failed to delete the memory. Please try again.")
                
    def unlock_and_view_memory(self, memory_id):
        """
        Unlock a memory and switch to the unlocked tab to view it.

        Args:
            memory_id: ID of the memory to unlock
        """
        try:
            # Unlock the memory
            success = self.memory_keeper.unlock_memory(memory_id)

            if success:
                QMessageBox.information(self, "Memory Unlocked",
                                        "The memory has been unlocked and is now available to view.")
                
                # Refresh the vault to remove the unlocked memory
                self.refresh_vault_memories()
                
                # Switch to the unlocked memories tab
                self.tabs.setCurrentIndex(3)

                # Refresh the unlocked memories list
                self.load_unlocked_memories()

                # Try to select and display the newly unlocked memory
                for i in range(self.unlocked_memory_list.count()):
                    item = self.unlocked_memory_list.item(i)
                    if item.date(Qt.UserRole) == memory_id:
                        self.unlocked_memory_list.setCurrentItem(item)
                        break
            
            else:
                QMessageBox.critical(self, "Error",
                                    "Failed to unlock the memory. Please try again.")
        except Exception as e:
            print(f"Error unlocking memory: {e}")
            QMessageBox.critical(self, "Error",
                                 f"An error occurred: {str(e)}")
            
    def export_memories(self):
        """Export all memories to a backup file."""
        # Initialize the import/export helper if it doesn't exist
        if not hasattr(self, 'import_export'):
            self.import_export = MemoryKeeperImportExport(self.memory_keeper)
        
        # Call the export function
        success, message = self.import_export.export_database()
        
        # Show result message
        if success:
            QMessageBox.information(self, "Export Complete", message)
        else:
            QMessageBox.warning(self, "Export Failed", message)
        
        # Refresh the dashboard
        self.refresh_dashboard()

    def import_memories(self):
        """Import memories from a backup file."""
        # Initialize the import/export helper if it doesn't exist
        if not hasattr(self, 'import_export'):
            self.import_export = MemoryKeeperImportExport(self.memory_keeper)
        
        # Ask user if they want to merge or replace
        choice_msg = QMessageBox()
        choice_msg.setIcon(QMessageBox.Question)
        choice_msg.setWindowTitle("Import Options")
        choice_msg.setText("How would you like to import memories?")
        choice_msg.setInformativeText("You can either merge the imported memories with your existing collection, or replace your current memories entirely.")
        
        merge_button = choice_msg.addButton("Merge", QMessageBox.ActionRole)
        replace_button = choice_msg.addButton("Replace", QMessageBox.ActionRole)
        cancel_button = choice_msg.addButton("Cancel", QMessageBox.RejectRole)
        
        choice_msg.exec_()
        
        # Handle user choice
        if choice_msg.clickedButton() == cancel_button:
            return
        
        merge_mode = (choice_msg.clickedButton() == merge_button)
        
        # Call the import function with the selected mode
        success, message = self.import_export.import_database(merge=merge_mode)
        
        # Show result message
        if success:
            QMessageBox.information(self, "Import Complete", message)
            
            # Refresh all tabs
            self.refresh_dashboard()
            self.refresh_vault_memories()
            self.load_unlocked_memories()
        else:
            QMessageBox.warning(self, "Import Failed", message)
            
class MemoryKeeperImportExport:
    """Helper class for handling import/export operations in MemoryKeeper."""

    def __init__(self, memory_keeper):
        """
        Initialize with a reference to the MemoryKeeper instance.

        Args:
            memory_keeper: Reference to the MemoryKeeper instance
        """
        self.memory_keeper = memory_keeper

    def export_database(self):
        """
        Export the entire database to a zip archive.
        
        Returns:
            Tuple (success: bool, message: str) indicating operation result
        """
        try:
            # Ask user for export location
            export_file, _ = QFileDialog.getSaveFileName(
                None, 
                "Export Memories", 
                str(Path.home() / "MemoryKeeper_Export.zip"),
                "Zip Files (*.zip)"
            )
            
            if not export_file:
                return False, "Export cancelled"
            
            # Get database path
            db_path = self.memory_keeper.db_path
            
            # Create a temporary directory for the export
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Copy database file
                db_dest = temp_path / "memorykeeper.db"
                shutil.copy2(db_path, db_dest)
                
                # Create metadata file
                metadata = {
                    "export_date": datetime.now().isoformat(),
                    "app_version": "1.0",  # You can update this with actual version
                    "memory_count": self.memory_keeper.get_memory_count()
                }
                
                with open(temp_path / "metadata.json", "w") as f:
                    json.dump(metadata, f, indent=2)
                
                # Create the zip file
                with zipfile.ZipFile(export_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add database and metadata files
                    zipf.write(db_dest, "memorykeeper.db")
                    zipf.write(temp_path / "metadata.json", "metadata.json")
            
            return True, f"Successfully exported to {export_file}"
        
        except Exception as e:
            return False, f"Export failed: {str(e)}"
        
    def import_database(self, merge=True):
        """
        Import a database from a previously exported zip archive.
        
        Args:
            merge: If True, merge imported memories with existing ones. 
                  If False, replace the existing database.
        
        Returns:
            Tuple (success: bool, message: str) indicating operation result
        """
        try:
            # Ask user for import file
            import_file, _ = QFileDialog.getOpenFileName(
                None, 
                "Import Memories", 
                str(Path.home()),
                "Zip Files (*.zip)"
            )
            
            if not import_file:
                return False, "Import cancelled"
            
            # Confirm import
            confirm_msg = QMessageBox()
            confirm_msg.setIcon(QMessageBox.Warning)
            confirm_msg.setWindowTitle("Confirm Import")
            
            if merge:
                confirm_msg.setText("Merge imported memories with your current memories?")
                confirm_msg.setInformativeText("This will add the imported memories to your existing collection.")
            else:
                confirm_msg.setText("Importing will replace your current memories.")
                confirm_msg.setInformativeText("Are you sure you want to proceed? This cannot be undone.")
            
            confirm_msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            confirm_msg.setDefaultButton(QMessageBox.No)
            
            if confirm_msg.exec_() != QMessageBox.Yes:
                return False, "Import cancelled"
            
            # Get database path
            db_path = self.memory_keeper.db_path
            
            # Create a temporary directory for the import
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract the zip file
                with zipfile.ZipFile(import_file, 'r') as zipf:
                    zipf.extractall(temp_path)
                
                # Verify this is a valid export
                if not (temp_path / "memorykeeper.db").exists():
                    return False, "Invalid export file: Missing database"
                
                if not (temp_path / "metadata.json").exists():
                    return False, "Invalid export file: Missing metadata"
                
                # Read metadata
                with open(temp_path / "metadata.json", "r") as f:
                    metadata = json.load(f)
                
                import_db_path = temp_path / "memorykeeper.db"
                
                if merge:
                    # Merge databases
                    imported_count = self._merge_databases(db_path, import_db_path)
                    return True, f"Successfully imported and merged {imported_count} memories"
                else:
                    # Close any existing database connections
                    if hasattr(self.memory_keeper, 'get_db_connection'):
                        try:
                            conn = self.memory_keeper.get_db_connection()
                            conn.close()
                        except:
                            pass
                    
                    # Create a backup of the current database
                    backup_path = str(db_path) + ".backup"
                    shutil.copy2(db_path, backup_path)
                    
                    # Replace the database
                    shutil.copy2(import_db_path, db_path)
                    
                    memory_count = metadata.get("memory_count", {})
                    total_count = memory_count.get("total", "unknown")
                    
                    return True, f"Successfully imported {total_count} memories"
            
        except Exception as e:
            # Restore from backup if available and not merging
            if not merge and 'backup_path' in locals():
                try:
                    shutil.copy2(backup_path, db_path)
                except Exception as backup_error:
                    return False, f"Import failed: {str(e)}\nAlso failed to restore backup: {str(backup_error)}"
            
            return False, f"Import failed: {str(e)}"
        
    def _merge_databases(self, current_db_path, import_db_path):
        """
        Merge two SQLite databases, importing memories from import_db to current_db.
        
        Args:
            current_db_path: Path to the current database
            import_db_path: Path to the database being imported
        
        Returns:
            Number of memories imported
        """
        # Connect to current database
        current_conn = sqlite3.connect(current_db_path)
        current_cursor = current_conn.cursor()
        
        # Connect to imported database
        import_conn = sqlite3.connect(import_db_path)
        import_conn.row_factory = sqlite3.Row
        import_cursor = import_conn.cursor()
        
        # Track how many memories we import
        imported_count = 0
        
        try:
            # Get all categories from the import database
            import_cursor.execute("SELECT id, name, description, icon FROM categories")
            categories = import_cursor.fetchall()
            
            # Get existing categories to avoid duplicates
            current_cursor.execute("SELECT id, name FROM categories")
            existing_categories = {row[1]: row[0] for row in current_cursor.fetchall()}
            
            # Import categories
            category_mapping = {}  # Maps imported category IDs to existing/new category IDs
            
            for category in categories:
                cat_id, cat_name, cat_desc, cat_icon = category
                
                # If category name already exists, map to existing ID
                if cat_name in existing_categories:
                    category_mapping[cat_id] = existing_categories[cat_name]
                else:
                    # Otherwise, insert the category with its original ID
                    current_cursor.execute(
                        "INSERT OR IGNORE INTO categories (id, name, description, icon) VALUES (?, ?, ?, ?)",
                        (cat_id, cat_name, cat_desc, cat_icon)
                    )
                    category_mapping[cat_id] = cat_id
            
            # Get all memories from the import database
            import_cursor.execute("""
                SELECT id, title, content, media_path, created_date, unlock_date,
                       unlock_type, unlock_conditions, is_unlocked, category, mood, importance
                FROM memories
            """)
            memories = import_cursor.fetchall()
            
            # Get existing memory IDs to avoid duplicates
            current_cursor.execute("SELECT id FROM memories")
            existing_memory_ids = {row[0] for row in current_cursor.fetchall()}
            
            # Import memories
            for memory in memories:
                memory_dict = dict(memory)
                memory_id = memory_dict['id']
                
                # Skip if memory already exists
                if memory_id in existing_memory_ids:
                    continue
                
                # Update category ID if needed
                if memory_dict['category'] in category_mapping:
                    memory_dict['category'] = category_mapping[memory_dict['category']]
                
                # Insert memory
                current_cursor.execute("""
                    INSERT INTO memories 
                    (id, title, content, media_path, created_date, unlock_date,
                     unlock_type, unlock_conditions, is_unlocked, category, mood, importance)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory_dict['id'], memory_dict['title'], memory_dict['content'],
                    memory_dict['media_path'], memory_dict['created_date'], memory_dict['unlock_date'],
                    memory_dict['unlock_type'], memory_dict['unlock_conditions'], memory_dict['is_unlocked'],
                    memory_dict['category'], memory_dict['mood'], memory_dict['importance']
                ))
                
                imported_count += 1
            
            # Get and import memory tags
            for memory_id in [m['id'] for m in memories if m['id'] not in existing_memory_ids]:
                import_cursor.execute("SELECT tag FROM memory_tags WHERE memory_id = ?", (memory_id,))
                tags = import_cursor.fetchall()
                
                for tag_row in tags:
                    current_cursor.execute(
                        "INSERT INTO memory_tags (memory_id, tag) VALUES (?, ?)",
                        (memory_id, tag_row[0])
                    )
            
            # Get and import responses
            for memory_id in [m['id'] for m in memories if m['id'] not in existing_memory_ids]:
                import_cursor.execute("""
                    SELECT id, response_content, response_date, response_mood
                    FROM responses WHERE memory_id = ?
                """, (memory_id,))
                responses = import_cursor.fetchall()
                
                for response in responses:
                    response_dict = dict(response)
                    current_cursor.execute("""
                        INSERT INTO responses 
                        (id, memory_id, response_content, response_date, response_mood)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        response_dict['id'], memory_id, response_dict['response_content'],
                        response_dict['response_date'], response_dict['response_mood']
                    ))
            
            # Commit all changes
            current_conn.commit()
            
            return imported_count
        
        except Exception as e:
            # Roll back on error
            current_conn.rollback()
            raise e
        
        finally:
            # Close connections
            current_conn.close()
            import_conn.close()

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