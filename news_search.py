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
                category TEXT
            )
        ''')
        
        self.conn.commit()
    
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
    
    def get_recent_news(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent news items."""
        cursor = self.conn.cursor()
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
    
    def get_news_by_source(self, source_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get news items from a specific source."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT id, title, description, url, source_name, published_date, fetched_date
            FROM news_items
            WHERE source_name = ?
            ORDER BY fetched_date DESC
            LIMIT ?
        ''', (source_name, limit))
        
        return [dict(zip(['id', 'title', 'description', 'url', 'source_name', 'published_date', 'fetched_date'], row))
                for row in cursor.fetchall()]
    
    def get_sources(self) -> List[Dict[str, Any]]:
        """Get all news sources."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT name, category FROM sources ORDER BY name')
        
        return [dict(zip(['name', 'category'], row)) for row in cursor.fetchall()]
    
    def get_news_by_category(self, category: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get news items by category."""
        cursor = self.conn.cursor()
        
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
    
    def generate_markdown_digest(self, news_items: List[Dict[str, Any]], filename: str = None) -> str:
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
                    f.write(f"**URL:** [{item['url']}]({item['url']})  \n\n")
                    
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
        
        for feed in self.feeds:
            try:
                parsed_feed = feedparser.parse(feed['url'])
                
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
                    
            except Exception as e:
                print(f"Error fetching {feed['name']}: {e}")
        
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
        
        print(f"\nURL: {item['url']}")
        print("-" * 60)
    
    def fetch_and_store_news(self):
        """Fetch news from all feeds and store in database."""
        print("Fetching news from RSS feeds...")
        
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
        
        # Get news from the last 24 hours
        news_items = self.db.get_recent_news(50)
        
        if not news_items:
            print("No news items found. Try fetching news first.")
            input("\nPress Enter to continue...")
            return
        
        # Display summary
        print(f"Showing {len(news_items)} recent news items\n")
        
        # Display first 10 items with indices
        for i, item in enumerate(news_items[:10]):
            self.display_news_item(item, i + 1)
        
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
            self.display_news_item(news_items[i], i + 1)
        
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
        
        sources = self.db.get_sources()
        
        if not sources:
            print("No sources available.")
            input("Press Enter to continue...")
            return
        
        print("Available sources:")
        for i, source in enumerate(sources, 1):
            print(f"{i}. {source['name']} ({source['category']})")
        
        print(f"\n1-{len(sources)}: Select source")
        print("q: Back to main menu")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == 'q':
            return
        elif choice.isdigit() and 1 <= int(choice) <= len(sources):
            selected_source = sources[int(choice) - 1]['name']
            news_items = self.db.get_news_by_source(selected_source)
            
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
        
        # Get unique categories
        sources = self.db.get_sources()
        categories = set(source['category'] for source in sources)
        
        if not categories:
            print("No categories available.")
            input("Press Enter to continue...")
            return
        
        print("Available categories:")
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
            news_items = self.db.get_news_by_category(selected_category)
            
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
        print("2. Today's News Dashboard")
        print("3. Search News")
        print("4. Browse by Source")
        print("5. Browse by Category")
        print("6. Generate Markdown Digest (from existing news)")
        print("7. Exit")
        
        choice = input("\nEnter your choice (1-7): ").strip()
        
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
            print("Goodbye!")
            self.db.close()
            sys.exit(0)
        else:
            print("Invalid choice. Please try again.")
            input("Press Enter to continue...")
            self.show_main_menu()
    
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
                print(f"{i}. {source['name']}")
            
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
        
        print(f"\nGenerating Markdown digest for {len(news_items)} news items...")
        
        # Ask for custom filename
        custom_filename = input("Enter custom filename (leave blank for auto-generated): ").strip()
        filename = custom_filename if custom_filename else None
        
        md_file = self.db.generate_markdown_digest(news_items, filename)
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