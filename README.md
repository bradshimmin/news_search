# News Search CLI

An interactive command-line application for aggregating, storing, and browsing news from RSS feeds.

## Features

- **Fetch and store news**: Automatically retrieve news from multiple RSS feeds and store them in a SQLite database
- **Today's News Dashboard**: View the most recent news items in a nicely formatted interface
- **Search functionality**: Search news items by keywords in titles and descriptions
- **Browse by source**: Filter news by specific news sources
- **Browse by category**: Filter news by categories (general, technology, world, etc.)
- **Active Source Filtering**: Focus on currently tracked sources while preserving historical data
- **Source Management**: Sync, deactivate, cleanup, and view source status
- **Interactive navigation**: Easy-to-use menu system with pagination
- **Persistent storage**: All fetched news is stored locally for offline browsing
- **Markdown Digest Generation**: Automatically generate nicely formatted Markdown files with fetched news for external reference
- **Custom Digest Creation**: Create Markdown digests from existing news based on various criteria (all news, today's news, specific sources, categories, active sources only)

## Installation

1. Clone this repository or download the files
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the application:

```bash
python news_search.py
```

Or make it executable and run directly:

```bash
chmod +x news_search.py
./news_search.py
```

## Configuration

Edit the `feeds.yaml` file to add, remove, or modify RSS feeds. Each feed should have:

- `name`: The display name of the news source
- `url`: The RSS feed URL
- `category`: The category (e.g., general, technology, world)

## Active Source Filtering

The application now includes comprehensive source management and active source filtering capabilities:

### Source Management Menu

Access the source management features through the main menu (option 7):

1. **Sync Sources with Config File**: Update source status based on current `feeds.yaml` configuration
2. **Deactivate Obsolete Sources**: Mark sources not in config as inactive
3. **Cleanup Inactive Sources**: Remove inactive sources (with confirmation)
4. **View Source Status**: Display all sources with status indicators (🟢 ACTIVE, 🔴 INACTIVE)

### Active Source Filtering

All browsing and display functions support active source filtering:

- **Today's News Dashboard**: Choose between "Show all news" or "Show only news from active sources"
- **Browse by Source**: Filter source list by active status
- **Browse by Category**: Filter categories by active sources
- **Generate Markdown Digest**: Filter digest content by active sources

### Benefits

- **Clean Reports**: Focus on currently tracked sources
- **Data Preservation**: Historical data from inactive sources remains accessible
- **Flexibility**: Choose between comprehensive or focused views
- **Automatic Sync**: Sources are automatically synced during news fetching

## Database

The application uses SQLite to store news items in a file called `news.db`. This file will be created automatically when you first run the application.

## Markdown Digests

The application automatically generates Markdown files containing news digests:

- **Automatic generation**: When fetching new news, a Markdown file is automatically created in the `news_digests/` directory
- **Custom generation**: You can create digests from existing news based on various criteria (all news, today's news, specific sources, categories)
- **File naming**: Auto-generated files include timestamp (e.g., `2023-12-20_15-30-45_news_digest.md`)
- **Format**: Well-structured Markdown with headers, metadata, and clickable links

Example digest structure:
```markdown
# 📰 News Digest

**Generated:** 2023-12-20 15:30:45
**Total Items:** 50

## BBC News

### Breaking News Title

**Source:** BBC News
**Published:** 2023-12-20 14:25
**URL:** [https://bbc.com/news](https://bbc.com/news)

News description goes here...

---
```

## Requirements

- Python 3.6+
- feedparser library
- PyYAML library

## License

This project is open source and available under the MIT License.