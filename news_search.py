#!/usr/bin/env python3
"""
News Search CLI Application

An interactive CLI tool for aggregating, storing, and browsing news from RSS feeds.
"""

import sqlite3
import yaml
import feedparser
from datetime import datetime, timedelta
import textwrap
import os
from typing import List, Dict, Any, Optional
import sys

# Database setup
DB_NAME = "news.db"
MD_OUTPUT_DIR = "news_digests"

class NewsDatabase:
    """Handles all database operations for the news application."""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self._create_tables()
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """Ensure the markdown output directory exists."""
        if not os.path.exists(MD_OUTPUT_DIR):
            os.makedirs(MD_OUTPUT_DIR)
    
    def _add_missing_columns(self):
        """Add missing columns to existing tables for backward compatibility."""
        cursor = self.conn.cursor()
        
        # Check if is_active column exists
        cursor.execute("PRAGMA table_info(sources)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_active' not in columns:
            cursor.execute('ALTER TABLE sources ADD COLUMN is_active BOOLEAN DEFAULT 1')
            print("Added 'is_active' column to sources table")
        
        if 'last_fetched' not in columns:
            cursor.execute('ALTER TABLE sources ADD COLUMN last_fetched TEXT')
            print("Added 'last_fetched' column to sources table")
        
        self.conn.commit()
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # News items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                url TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_url TEXT,
                category TEXT,
                published_date TEXT,
                fetched_date TEXT NOT NULL,
                UNIQUE(url)
            )
        ''')
        
        # Sources table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                url TEXT,
                category TEXT,
                is_active BOOLEAN DEFAULT 1,
                last_fetched TEXT
            )
        ''')
        
        self.conn.commit()
        
        # Add new columns to existing table if they don't exist
        self._add_missing_columns()
    
    def add_news_item(self, title: str, description: str, url: str, source_name: str, 
                     source_url: str, category: str, published_date: str) -> bool:
        """Add a news item to the database. Returns True if added, False if already exists."""
        cursor = self.conn.cursor()
        fetched_date = datetime.now().isoformat()
        
        try:
            cursor.execute('''
                INSERT INTO news_items (title, description, url, source_name, source_url, 
                                      category, published_date, fetched_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, description, url, source_name, source_url, category, published_date, fetched_date))
            
            # Ensure source exists
            cursor.execute('''
                INSERT OR IGNORE INTO sources (name, url, category)
                VALUES (?, ?, ?)
            ''', (source_name, source_url, category))
            
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Item already exists
            return False
    
    def get_recent_news(self, limit: int = 20, active_only: bool = False) -> List[Dict[str, Any]]:
        """Get recent news items."""
        cursor = self.conn.cursor()
        
        if active_only:
            cursor.execute('''
                SELECT id, title, description, url, source_name, published_date, fetched_date
                FROM news_items
                WHERE source_name IN (
                    SELECT name FROM sources WHERE is_active = 1
                )
                ORDER BY fetched_date DESC
                LIMIT ?
            ''', (limit,))
        else:
            cursor.execute('''
                SELECT id, title, description, url, source_name, published_date, fetched_date
                FROM news_items
                ORDER BY fetched_date DESC
                LIMIT ?
            ''', (limit,))
        
        return [dict(zip(['id', 'title', 'description', 'url', 'source_name', 'published_date', 'fetched_date'], row))
                for row in cursor.fetchall()]
    
    def search_news(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search news items by query."""
        cursor = self.conn.cursor()
        search_term = f"%{query}%"
        
        cursor.execute('''
            SELECT id, title, description, url, source_name, published_date, fetched_date
            FROM news_items
            WHERE title LIKE ? OR description LIKE ?
            ORDER BY fetched_date DESC
            LIMIT ?
        ''', (search_term, search_term, limit))
        
        return [dict(zip(['id', 'title', 'description', 'url', 'source_name', 'published_date', 'fetched_date'], row))
                for row in cursor.fetchall()]
    
    def get_news_by_source(self, source_name: str, limit: int = 20, active_only: bool = False) -> List[Dict[str, Any]]:
        """Get news items from a specific source."""
        cursor = self.conn.cursor()
        
        if active_only:
            cursor.execute('''
                SELECT id, title, description, url, source_name, published_date, fetched_date
                FROM news_items
                WHERE source_name = ? AND source_name IN (
                    SELECT name FROM sources WHERE is_active = 1
                )
                ORDER BY fetched_date DESC
                LIMIT ?
            ''', (source_name, limit))
        else:
            cursor.execute('''
                SELECT id, title, description, url, source_name, published_date, fetched_date
                FROM news_items
                WHERE source_name = ?
                ORDER BY fetched_date DESC
                LIMIT ?
            ''', (source_name, limit))
        
        return [dict(zip(['id', 'title', 'description', 'url', 'source_name', 'published_date', 'fetched_date'], row))
                for row in cursor.fetchall()]
    
    def get_sources(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """Get all news sources, optionally filtered by active status."""
        cursor = self.conn.cursor()
        
        if active_only:
            cursor.execute('''
                SELECT name, category, is_active, last_fetched 
                FROM sources 
                WHERE is_active = 1 
                ORDER BY name
            ''')
        else:
            cursor.execute('''
                SELECT name, category, is_active, last_fetched 
                FROM sources 
                ORDER BY name
            ''')
        
        return [dict(zip(['name', 'category', 'is_active', 'last_fetched'], row)) 
                for row in cursor.fetchall()]
    
    def get_active_sources(self) -> List[Dict[str, Any]]:
        """Get only active news sources."""
        return self.get_sources(active_only=True)
    
    def sync_sources_with_config(self, fetcher=None) -> None:
        """Sync database sources with current config file."""
        if fetcher is None:
            # For backward compatibility, try to use internal fetcher if available
            try:
                current_sources = {feed['name'] for feed in self.fetcher.feeds}
            except AttributeError:
                print("Error: No fetcher provided and no internal fetcher available.")
                return
        else:
            current_sources = {feed['name'] for feed in fetcher.feeds}
        
        cursor = self.conn.cursor()
        
        # Mark all sources as inactive initially
        cursor.execute('UPDATE sources SET is_active = 0')
        
        # Mark current sources as active and update last_fetched
        now = datetime.now().isoformat()
        for source_name in current_sources:
            cursor.execute('''
                UPDATE sources 
                SET is_active = 1, last_fetched = ?
                WHERE name = ?
            ''', (now, source_name))
        
        self.conn.commit()
        print(f"Source sync complete. {len(current_sources)} sources marked as active.")
    
    def deactivate_obsolete_sources(self, fetcher=None) -> int:
        """Mark sources not in config as inactive. Returns number of sources deactivated."""
        if fetcher is None:
            # For backward compatibility, try to use internal fetcher if available
            try:
                current_sources = {feed['name'] for feed in self.fetcher.feeds}
            except AttributeError:
                print("Error: No fetcher provided and no internal fetcher available.")
                return 0
        else:
            current_sources = {feed['name'] for feed in fetcher.feeds}
        
        cursor = self.conn.cursor()
        
        # Find sources that are currently active but not in config
        cursor.execute('''
            SELECT name FROM sources 
            WHERE is_active = 1 AND name NOT IN ({})
        '''.format(','.join(['?'] * len(current_sources))), tuple(current_sources))
        
        obsolete_sources = [row[0] for row in cursor.fetchall()]
        
        if obsolete_sources:
            cursor.execute('''
                UPDATE sources 
                SET is_active = 0
                WHERE name IN ({})
            '''.format(','.join(['?'] * len(obsolete_sources))), tuple(obsolete_sources))
            self.conn.commit()
        
        return len(obsolete_sources)
    
    def cleanup_inactive_sources(self, confirm: bool = True) -> int:
        """Remove inactive sources from database. Returns number of sources removed."""
        cursor = self.conn.cursor()
        
        # Get count of inactive sources
        cursor.execute('SELECT COUNT(*) FROM sources WHERE is_active = 0')
        inactive_count = cursor.fetchone()[0]
        
        if inactive_count == 0:
            print("No inactive sources to clean up.")
            return 0
        
        if confirm:
            response = input(f"WARNING: This will permanently delete {inactive_count} inactive sources. Continue? (y/N): ")
            if response.lower() != 'y':
                print("Cleanup cancelled.")
                return 0
        
        # Get inactive sources for display
        cursor.execute('SELECT name FROM sources WHERE is_active = 0')
        inactive_sources = [row[0] for row in cursor.fetchall()]
        
        print(f"Removing inactive sources: {', '.join(inactive_sources)}...")
        
        # Delete inactive sources
        cursor.execute('DELETE FROM sources WHERE is_active = 0')
        self.conn.commit()
        
        return inactive_count
    
    def get_news_by_category(self, category: str, limit: int = 20, active_only: bool = False) -> List[Dict[str, Any]]:
        """Get news items by category."""
        cursor = self.conn.cursor()
        
        if active_only:
            cursor.execute('''
                SELECT id, title, description, url, source_name, published_date, fetched_date
                FROM news_items
                WHERE category = ? AND source_name IN (
                    SELECT name FROM sources WHERE is_active = 1
                )
                ORDER BY fetched_date DESC
                LIMIT ?
            ''', (category, limit))
        else:
            cursor.execute('''
                SELECT id, title, description, url, source_name, published_date, fetched_date
                FROM news_items
                WHERE category = ?
                ORDER BY fetched_date DESC
                LIMIT ?
            ''', (category, limit))
        
        return [dict(zip(['id', 'title', 'description', 'url', 'source_name', 'published_date', 'fetched_date'], row))
                for row in cursor.fetchall()]
    
    def close(self):
        """Close the database connection."""
        self.conn.close()
    
    def generate_markdown_digest(self, news_items: List[Dict[str, Any]], filename: str = None, active_only: bool = False) -> str:
        """Generate a Markdown file with news digest."""
        if filename is None:
            # Generate filename with current date/time
            now = datetime.now()
            filename = now.strftime("%Y-%m-%d_%H-%M-%S_news_digest.md")
        
        filepath = os.path.join(MD_OUTPUT_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# 📰 News Digest\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Items:** {len(news_items)}\n\n")
            
            # Group by source
            sources = {}
            for item in news_items:
                source_name = item['source_name']
                if source_name not in sources:
                    sources[source_name] = []
                sources[source_name].append(item)
            
            # Write each source section
            for source_name, items in sources.items():
                # Check if source is active if filtering is enabled
                if active_only:
                    cursor = self.conn.cursor()
                    cursor.execute('SELECT is_active FROM sources WHERE name = ?', (source_name,))
                    source_info = cursor.fetchone()
                    if source_info and not source_info[0]:
                        continue  # Skip inactive sources
                
                f.write(f"## {source_name}\n\n")
                
                for item in items:
                    f.write(f"### {item['title']}\n\n")
                    
                    # Format date
                    try:
                        date_obj = datetime.fromisoformat(item['published_date'])
                        date_str = date_obj.strftime('%Y-%m-%d %H:%M')
                    except:
                        date_str = item['published_date']
                    
                    f.write(f"**Source:** {item['source_name']}  \n")
                    f.write(f"**Published:** {date_str}  \n")
                    # Extract domain from URL for cleaner display
                    domain = self.extract_domain(item['url'])
                    f.write(f"**URL:** [{domain}]({item['url']})  \n\n")
                    
                    if item['description']:
                        # Clean up description for markdown
                        desc = item['description'].replace('\n', ' ').strip()
                        f.write(f"{desc}\n\n")
                    
                    f.write("---\n\n")
        
        return filepath

class NewsFetcher:
    """Handles fetching and parsing RSS feeds."""
    
    def __init__(self, config_file: str = "feeds.yaml"):
        self.config_file = config_file
        self.feeds = self._load_feeds()
    
    def _load_feeds(self) -> List[Dict[str, Any]]:
        """Load RSS feeds from YAML configuration."""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
                return config.get('feeds', [])
        except FileNotFoundError:
            print(f"Error: Configuration file {self.config_file} not found.")
            return []
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file: {e}")
            return []
    
    def fetch_all_feeds(self) -> List[Dict[str, Any]]:
        """Fetch all RSS feeds and return parsed news items."""
        all_items = []
        successful_feeds = 0
        failed_feeds = 0
        
        print(f"Attempting to fetch {len(self.feeds)} RSS feeds...")
        
        for feed in self.feeds:
            try:
                print(f"  Fetching: {feed['name']} ({feed['url']})")
                parsed_feed = feedparser.parse(feed['url'])
                
                # Check if feed parsing failed
                if parsed_feed.bozo:
                    print(f"    ❌ Invalid RSS feed: {parsed_feed.bozo_exception}")
                    failed_feeds += 1
                    continue
                
                item_count = len(parsed_feed.entries)
                if item_count == 0:
                    print(f"    ⚠️  No items found in feed")
                    failed_feeds += 1
                    continue
                    
                print(f"    ✅ Success: Found {item_count} items")
                
                for entry in parsed_feed.entries:
                    # Extract published date if available
                    published_date = None
                    if hasattr(entry, 'published_parsed'):
                        published_date = datetime(*entry.published_parsed[:6]).isoformat()
                    elif hasattr(entry, 'updated_parsed'):
                        published_date = datetime(*entry.updated_parsed[:6]).isoformat()
                    
                    item = {
                        'title': entry.get('title', 'No title'),
                        'description': entry.get('description', entry.get('summary', 'No description')),
                        'url': entry.link,
                        'source_name': feed['name'],
                        'source_url': feed['url'],
                        'category': feed['category'],
                        'published_date': published_date or datetime.now().isoformat()
                    }
                    all_items.append(item)
                
                successful_feeds += 1
                
            except Exception as e:
                print(f"    ❌ Error: {e}")
                failed_feeds += 1
        
        print(f"\n📊 Feed Fetch Summary:")
        print(f"  ✅ Successfully fetched from {successful_feeds} feeds")
        print(f"  ❌ Failed to fetch from {failed_feeds} feeds")
        print(f"  📰 Total items collected: {len(all_items)}")
        
        return all_items

class NewsCLI:
    """Interactive CLI for the news application."""
    
    def __init__(self):
        self.db = NewsDatabase()
        self.fetcher = NewsFetcher()
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_header(self, title: str):
        """Display a formatted header."""
        print("=" * 60)
        print(f"  {title.upper()}")
        print("=" * 60)

    def extract_domain(self, url: str) -> str:
        """Extract domain from URL for cleaner display."""
        if '://' in url:
            domain = url.split('://')[-1].split('/')[0]
        else:
            domain = url.split('/')[0]
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain

    def hyperlink(self, text: str, url: str) -> str:
        """Create a clickable hyperlink using ANSI escape codes (OSC 8)."""
        # OSC 8 format: \033]8;;URL\033\\TEXT\033]8;;\033\\ 
        return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"

    def supports_hyperlinks(self) -> bool:
        """Check if terminal supports hyperlinks by testing environment."""
        # Check for common terminal types that support OSC 8 hyperlinks
        term = os.environ.get('TERM', '')
        
        # Terminals known to support hyperlinks
        supported_terms = [
            'xterm', 'xterm-256color', 'screen', 'screen-256color',
            'tmux', 'tmux-256color', 'alacritty', 'kitty',
            'vte', 'vte-256color', 'gnome', 'konsole',
            'foot', 'wezterm', 'hyper'
        ]
        
        # Check if terminal type contains any supported term
        return any(supported_term in term for supported_term in supported_terms)
    
    def display_news_item(self, item: Dict[str, Any], index: int = None):
        """Display a single news item in a formatted way."""
        if index is not None:
            print(f"\n[{index}] {item['title']}")
        else:
            print(f"\n{item['title']}")
        
        print(f"Source: {item['source_name']}")
        
        if item['published_date']:
            try:
                date_obj = datetime.fromisoformat(item['published_date'])
                print(f"Published: {date_obj.strftime('%Y-%m-%d %H:%M')}")
            except:
                print(f"Published: {item['published_date']}")
        
        if item['description']:
            wrapped_desc = textwrap.fill(item['description'], width=70)
            print(f"\n{wrapped_desc}")
        
        # Extract domain from URL for cleaner display
        domain = self.extract_domain(item['url'])
        if self.supports_hyperlinks():
            # Use clickable hyperlink if terminal supports it
            hyperlinked_domain = self.hyperlink(domain, item['url'])
            print(f"\nURL: {hyperlinked_domain}")
        else:
            # Fallback for terminals without hyperlink support
            print(f"\nURL: {domain} (press 'o' to open full URL)")
        print("-" * 60)

    def display_news_item_compact(self, item: Dict[str, Any], index: int = None):
        """Display a single news item in a clean two-line format."""
        # Format date if available
        date_str = ""
        if item['published_date']:
            try:
                date_obj = datetime.fromisoformat(item['published_date'])
                date_str = date_obj.strftime('%Y-%m-%d')
            except:
                date_str = item['published_date']
        
        # First line: index, date, title, source
        if index is not None:
            if date_str:
                print(f"[{index}] {date_str} - {item['title']} ({item['source_name']})")
            else:
                print(f"[{index}] {item['title']} ({item['source_name']})")
        else:
            if date_str:
                print(f"{date_str} - {item['title']} ({item['source_name']})")
            else:
                print(f"{item['title']} ({item['source_name']})")
        
        # Second line: indented URL with link emoji - show domain only
        domain = self.extract_domain(item['url'])
        if self.supports_hyperlinks():
            # Use clickable hyperlink if terminal supports it
            hyperlinked_domain = self.hyperlink(domain, item['url'])
            print(f"  🔗 {hyperlinked_domain}")
        else:
            # Fallback for terminals without hyperlink support
            print(f"  🔗 {domain} (press 'o' to open)")
    
    def fetch_and_store_news(self):
        """Fetch news from all feeds and store in database."""
        print("Fetching news from RSS feeds...")
        
        # Sync sources with config before fetching
        print("Syncing sources with configuration...")
        self.db.sync_sources_with_config()
        
        items = self.fetcher.fetch_all_feeds()
        added_count = 0
        new_items = []  # Only store items that were actually added
        
        for item in items:
            if self.db.add_news_item(
                title=item['title'],
                description=item['description'],
                url=item['url'],
                source_name=item['source_name'],
                source_url=item['source_url'],
                category=item['category'],
                published_date=item['published_date']
            ):
                added_count += 1
                new_items.append(item)  # Only add items that were successfully stored
        
        print(f"Fetched and stored {added_count} new news items.")
        
        # Generate markdown digest only for new items
        if new_items:
            print("Generating Markdown digest...")
            md_file = self.db.generate_markdown_digest(new_items)
            print(f"Markdown digest saved to: {md_file}")
        
        input("\nPress Enter to continue...")
    
    def show_todays_news(self):
        """Show today's news dashboard."""
        self.clear_screen()
        self.display_header("Today's News Dashboard")
        
        # Ask if user wants to filter by active sources only
        print("Filter options:")
        print("1. Show all news")
        print("2. Show only news from active sources")
        print("q: Back to main menu")
        
        filter_choice = input("\nEnter your choice (1-2, q): ").strip().lower()
        
        if filter_choice == 'q':
            return
        
        active_only = filter_choice == '2'
        
        # Get news from the last 24 hours
        news_items = self.db.get_recent_news(50, active_only=active_only)
        
        if not news_items:
            print("No news items found. Try fetching news first.")
            input("\nPress Enter to continue...")
            return
        
        # Display summary
        filter_text = "from active sources only" if active_only else "from all sources"
        print(f"Showing {len(news_items)} recent news items {filter_text}\n")
        
        # Display first 10 items with indices in compact format
        for i, item in enumerate(news_items[:10]):
            self.display_news_item_compact(item, i + 1)
        
        # Navigation menu
        print("\nNavigation:")
        print("1-10: View specific news item")
        print("n: Next page")
        print("s: Search news")
        print("b: Browse by source")
        print("c: Browse by category")
        print("f: Fetch new news")
        print("q: Back to main menu")
        
        choice = input("\nEnter your choice: ").strip().lower()
        
        if choice == 'q':
            return
        elif choice == 'f':
            self.fetch_and_store_news()
            self.show_todays_news()
        elif choice == 's':
            self.search_news()
        elif choice == 'b':
            self.browse_by_source()
        elif choice == 'c':
            self.browse_by_category()
        elif choice == 'n':
            self.show_news_page(news_items, start_index=10)
        elif choice.isdigit() and 1 <= int(choice) <= len(news_items):
            self.show_news_item_detail(news_items[int(choice) - 1])
        else:
            print("Invalid choice.")
            input("Press Enter to continue...")
            self.show_todays_news()
    
    def show_news_page(self, news_items: List[Dict[str, Any]], start_index: int = 0):
        """Show a page of news items."""
        self.clear_screen()
        self.display_header("News Items")
        
        end_index = min(start_index + 10, len(news_items))
        
        for i in range(start_index, end_index):
            self.display_news_item_compact(news_items[i], i + 1)
        
        # Navigation
        print(f"\nShowing items {start_index + 1}-{end_index} of {len(news_items)}")
        print("\nNavigation:")
        print(f"1-{end_index}: View specific news item")
        
        if start_index > 0:
            print("p: Previous page")
        
        if end_index < len(news_items):
            print("n: Next page")
        
        print("q: Back to main menu")
        
        choice = input("\nEnter your choice: ").strip().lower()
        
        if choice == 'q':
            return
        elif choice == 'p' and start_index > 0:
            self.show_news_page(news_items, start_index - 10)
        elif choice == 'n' and end_index < len(news_items):
            self.show_news_page(news_items, end_index)
        elif choice.isdigit() and 1 <= int(choice) <= len(news_items):
            self.show_news_item_detail(news_items[int(choice) - 1])
        else:
            print("Invalid choice.")
            input("Press Enter to continue...")
            self.show_news_page(news_items, start_index)
    
    def show_news_item_detail(self, item: Dict[str, Any]):
        """Show detailed view of a news item."""
        self.clear_screen()
        self.display_header("News Item Detail")
        
        self.display_news_item(item)
        
        # Show full URL in detail view
        print(f"\nFull URL: {item['url']}")
        
        print("\nOptions:")
        print("o: Open URL in browser")
        print("b: Back to news list")
        print("q: Back to main menu")
        
        choice = input("\nEnter your choice: ").strip().lower()
        
        if choice == 'o':
            self.open_in_browser(item['url'])
        elif choice == 'b':
            return  # Will go back to previous menu
        elif choice == 'q':
            return  # Will go back to main menu
        else:
            print("Invalid choice.")
            input("Press Enter to continue...")
            self.show_news_item_detail(item)
    
    def open_in_browser(self, url: str):
        """Open URL in default browser."""
        try:
            import webbrowser
            webbrowser.open(url)
            print(f"Opening {url} in browser...")
        except ImportError:
            print("Browser opening not supported on this system.")
        except Exception as e:
            print(f"Error opening browser: {e}")
        
        input("Press Enter to continue...")
    
    def search_news(self):
        """Search news by keyword."""
        self.clear_screen()
        self.display_header("Search News")
        
        query = input("Enter search terms: ").strip()
        
        if not query:
            print("No search terms entered.")
            input("Press Enter to continue...")
            return
        
        results = self.db.search_news(query)
        
        if not results:
            print(f"No results found for '{query}'")
            input("Press Enter to continue...")
            return
        
        print(f"\nFound {len(results)} results for '{query}':\n")
        
        # Show first page of results
        self.show_news_page(results)
    
    def browse_by_source(self):
        """Browse news by source."""
        self.clear_screen()
        self.display_header("Browse by Source")
        
        # Ask if user wants to filter by active sources only
        print("Filter options:")
        print("1. Show all sources")
        print("2. Show only active sources")
        print("q: Back to main menu")
        
        filter_choice = input("\nEnter your choice (1-2, q): ").strip().lower()
        
        if filter_choice == 'q':
            return
        elif filter_choice == '2':
            sources = self.db.get_sources(active_only=True)
            active_only = True
        else:
            sources = self.db.get_sources()
            active_only = False
        
        if not sources:
            print("No sources available.")
            input("Press Enter to continue...")
            return
        
        print(f"\nAvailable sources ({'active only' if active_only else 'all'}):")
        for i, source in enumerate(sources, 1):
            status = "🟢" if source.get('is_active', True) else "🔴"
            print(f"{i}. {source['name']} ({source['category']}) {status}")
        
        print(f"\n1-{len(sources)}: Select source")
        print("q: Back to main menu")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == 'q':
            return
        elif choice.isdigit() and 1 <= int(choice) <= len(sources):
            selected_source = sources[int(choice) - 1]['name']
            news_items = self.db.get_news_by_source(selected_source, active_only=active_only)
            
            if news_items:
                self.clear_screen()
                self.display_header(f"News from {selected_source}")
                self.show_news_page(news_items)
            else:
                print(f"No news items found for {selected_source}")
                input("Press Enter to continue...")
        else:
            print("Invalid choice.")
            input("Press Enter to continue...")
            self.browse_by_source()
    
    def browse_by_category(self):
        """Browse news by category."""
        self.clear_screen()
        self.display_header("Browse by Category")
        
        # Ask if user wants to filter by active sources only
        print("Filter options:")
        print("1. Show all categories")
        print("2. Show only categories with active sources")
        print("q: Back to main menu")
        
        filter_choice = input("\nEnter your choice (1-2, q): ").strip().lower()
        
        if filter_choice == 'q':
            return
        elif filter_choice == '2':
            sources = self.db.get_sources(active_only=True)
            active_only = True
        else:
            sources = self.db.get_sources()
            active_only = False
        
        # Get unique categories
        categories = set(source['category'] for source in sources)
        
        if not categories:
            print("No categories available.")
            input("Press Enter to continue...")
            return
        
        print(f"\nAvailable categories ({'active sources only' if active_only else 'all sources'}):")
        category_list = sorted(list(categories))
        for i, category in enumerate(category_list, 1):
            print(f"{i}. {category}")
        
        print(f"\n1-{len(category_list)}: Select category")
        print("q: Back to main menu")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == 'q':
            return
        elif choice.isdigit() and 1 <= int(choice) <= len(category_list):
            selected_category = category_list[int(choice) - 1]
            news_items = self.db.get_news_by_category(selected_category, active_only=active_only)
            
            if news_items:
                self.clear_screen()
                self.display_header(f"News: {selected_category}")
                self.show_news_page(news_items)
            else:
                print(f"No news items found for category {selected_category}")
                input("Press Enter to continue...")
        else:
            print("Invalid choice.")
            input("Press Enter to continue...")
            self.browse_by_category()
    
    def show_main_menu(self):
        """Display the main menu."""
        self.clear_screen()
        self.display_header("News Search CLI")
        
        print("Main Menu:")
        print("1. Fetch Latest News")
        print("2. Browse Today's News Dashboard")
        print("3. Search News")
        print("4. Browse by Source")
        print("5. Browse by Category")
        print("6. Generate Markdown Digest (from existing news)")
        print("7. Manage Sources")
        print("8. Exit")
        
        choice = input("\nEnter your choice (1-8): ").strip()
        
        if choice == '1':
            self.fetch_and_store_news()
            self.show_main_menu()
        elif choice == '2':
            self.show_todays_news()
            self.show_main_menu()
        elif choice == '3':
            self.search_news()
            self.show_main_menu()
        elif choice == '4':
            self.browse_by_source()
            self.show_main_menu()
        elif choice == '5':
            self.browse_by_category()
            self.show_main_menu()
        elif choice == '6':
            self.generate_digest_from_existing()
            self.show_main_menu()
        elif choice == '7':
            self.show_source_management_menu()
            self.show_main_menu()
        elif choice == '8':
            print("Goodbye!")
            self.db.close()
            sys.exit(0)
        else:
            print("Invalid choice. Please try again.")
            input("Press Enter to continue...")
            self.show_main_menu()
    
    def show_source_management_menu(self):
        """Display the source management menu."""
        self.clear_screen()
        self.display_header("Source Management")
        
        print("Source Management Menu:")
        print("1. Sync Sources with Config File")
        print("2. Deactivate Obsolete Sources")
        print("3. Cleanup Inactive Sources")
        print("4. View Source Status")
        print("5. Back to Main Menu")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            self.sync_sources_with_config()
        elif choice == '2':
            self.deactivate_obsolete_sources()
        elif choice == '3':
            self.cleanup_inactive_sources()
        elif choice == '4':
            self.view_source_status()
        elif choice == '5':
            return
        else:
            print("Invalid choice. Please try again.")
            input("Press Enter to continue...")
            self.show_source_management_menu()
    
    def sync_sources_with_config(self):
        """Sync database sources with current config file."""
        self.clear_screen()
        self.display_header("Sync Sources with Config")
        
        print("Syncing sources with feeds.yaml configuration...")
        self.db.sync_sources_with_config()
        
        # Show results
        all_sources = self.db.get_sources()
        active_sources = [s for s in all_sources if s['is_active']]
        inactive_sources = [s for s in all_sources if not s['is_active']]
        
        print(f"\nSync Results:")
        print(f"  Total sources in database: {len(all_sources)}")
        print(f"  Active sources: {len(active_sources)}")
        print(f"  Inactive sources: {len(inactive_sources)}")
        
        if inactive_sources:
            print(f"\nInactive sources: {', '.join([s['name'] for s in inactive_sources])}")
        
        input("\nPress Enter to continue...")
    
    def deactivate_obsolete_sources(self):
        """Mark sources not in config as inactive."""
        self.clear_screen()
        self.display_header("Deactivate Obsolete Sources")
        
        print("Checking for sources not in current config...")
        count = self.db.deactivate_obsolete_sources()
        
        if count > 0:
            print(f"Deactivated {count} obsolete sources.")
        else:
            print("No obsolete sources found.")
        
        input("\nPress Enter to continue...")
    
    def cleanup_inactive_sources(self):
        """Remove inactive sources from database."""
        self.clear_screen()
        self.display_header("Cleanup Inactive Sources")
        
        print("This will permanently remove all inactive sources from the database.")
        print("Note: News items from these sources will remain in the database.\n")
        
        count = self.db.cleanup_inactive_sources()
        
        if count > 0:
            print(f"Removed {count} inactive sources.")
        
        input("\nPress Enter to continue...")
    
    def view_source_status(self):
        """View status of all sources."""
        self.clear_screen()
        self.display_header("Source Status")
        
        all_sources = self.db.get_sources()
        
        if not all_sources:
            print("No sources found in database.")
            input("\nPress Enter to continue...")
            return
        
        print("All Sources:")
        print("-" * 80)
        
        active_sources = [s for s in all_sources if s['is_active']]
        inactive_sources = [s for s in all_sources if not s['is_active']]
        
        print("\n🟢 ACTIVE SOURCES:")
        if active_sources:
            for i, source in enumerate(active_sources, 1):
                status = "Active"
                last_fetched = source.get('last_fetched', 'Never')
                if last_fetched and last_fetched != 'Never':
                    try:
                        date_obj = datetime.fromisoformat(last_fetched)
                        last_fetched = date_obj.strftime('%Y-%m-%d %H:%M')
                    except:
                        pass
                print(f"{i}. {source['name']} ({source['category']}) - {status} - Last fetched: {last_fetched}")
        else:
            print("  No active sources found.")
        
        print("\n🔴 INACTIVE SOURCES:")
        if inactive_sources:
            for i, source in enumerate(inactive_sources, 1):
                status = "Inactive"
                last_fetched = source.get('last_fetched', 'Never')
                if last_fetched and last_fetched != 'Never':
                    try:
                        date_obj = datetime.fromisoformat(last_fetched)
                        last_fetched = date_obj.strftime('%Y-%m-%d %H:%M')
                    except:
                        pass
                print(f"{i}. {source['name']} ({source['category']}) - {status} - Last fetched: {last_fetched}")
        else:
            print("  No inactive sources found.")
        
        print(f"\nTotal: {len(all_sources)} sources ({len(active_sources)} active, {len(inactive_sources)} inactive)")
        
        input("\nPress Enter to continue...")
    
    def generate_digest_from_existing(self):
        """Generate a Markdown digest from existing news in database."""
        self.clear_screen()
        self.display_header("Generate Markdown Digest")
        
        print("Generate digest from:")
        print("1. All news")
        print("2. Today's news")
        print("3. Specific source")
        print("4. Specific category")
        print("5. Custom date range")
        print("q. Back to main menu")
        
        choice = input("\nEnter your choice: ").strip().lower()
        
        if choice == 'q':
            return
        
        news_items = []
        
        if choice == '1':
            # All news
            news_items = self.db.get_recent_news(10000)
        elif choice == '2':
            # Today's news (last 24 hours)
            news_items = self.db.get_recent_news(100)
        elif choice == '3':
            # Specific source
            sources = self.db.get_sources()
            if not sources:
                print("No sources available.")
                input("Press Enter to continue...")
                return
            
            print("\nAvailable sources:")
            for i, source in enumerate(sources, 1):
                status = "🟢" if source.get('is_active', True) else "🔴"
                print(f"{i}. {source['name']} {status}")
            
            source_choice = input("\nSelect source (1-{}) or q to cancel: ".format(len(sources))).strip()
            
            if source_choice == 'q':
                return
            elif source_choice.isdigit() and 1 <= int(source_choice) <= len(sources):
                selected_source = sources[int(source_choice) - 1]['name']
                news_items = self.db.get_news_by_source(selected_source, 1000)
            else:
                print("Invalid choice.")
                input("Press Enter to continue...")
                return
        elif choice == '4':
            # Specific category
            sources = self.db.get_sources()
            categories = set(source['category'] for source in sources)
            
            if not categories:
                print("No categories available.")
                input("Press Enter to continue...")
                return
            
            print("\nAvailable categories:")
            category_list = sorted(list(categories))
            for i, category in enumerate(category_list, 1):
                print(f"{i}. {category}")
            
            category_choice = input("\nSelect category (1-{}) or q to cancel: ".format(len(category_list))).strip()
            
            if category_choice == 'q':
                return
            elif category_choice.isdigit() and 1 <= int(category_choice) <= len(category_list):
                selected_category = category_list[int(category_choice) - 1]
                news_items = self.db.get_news_by_category(selected_category, 1000)
            else:
                print("Invalid choice.")
                input("Press Enter to continue...")
                return
        elif choice == '5':
            print("Custom date range not yet implemented.")
            input("Press Enter to continue...")
            return
        else:
            print("Invalid choice.")
            input("Press Enter to continue...")
            return
        
        if not news_items:
            print("No news items found for selected criteria.")
            input("Press Enter to continue...")
            return
        
        # Ask if user wants to filter by active sources only
        print("\nFilter options:")
        print("1. Include all sources")
        print("2. Include only active sources")
        
        filter_choice = input("Enter your choice (1-2): ").strip()
        active_only = filter_choice == '2'
        
        print(f"\nGenerating Markdown digest for {len(news_items)} news items...")
        
        # Ask for custom filename
        custom_filename = input("Enter custom filename (leave blank for auto-generated): ").strip()
        filename = custom_filename if custom_filename else None
        
        md_file = self.db.generate_markdown_digest(news_items, filename, active_only=active_only)
        print(f"Markdown digest saved to: {md_file}")
        
        input("\nPress Enter to continue...")
    
    def run(self):
        """Run the CLI application."""
        self.show_main_menu()

def main():
    """Main entry point."""
    # Check if feedparser is installed
    try:
        import feedparser
    except ImportError:
        print("Error: feedparser library is required.")
        print("Install it with: pip install feedparser")
        sys.exit(1)
    
    # Check if PyYAML is installed
    try:
        import yaml
    except ImportError:
        print("Error: PyYAML library is required.")
        print("Install it with: pip install pyyaml")
        sys.exit(1)
    
    # Create CLI instance and run
    cli = NewsCLI()
    cli.run()

if __name__ == "__main__":
    main()
