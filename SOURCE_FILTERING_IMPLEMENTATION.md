# Active Source Filtering Implementation

## Overview

This implementation adds comprehensive source management and active source filtering capabilities to the News Search application. It allows users to focus reports and dashboards on currently tracked sources while preserving historical data from sources no longer in the configuration.

## Problem Solved

Previously, all sources that had ever been fetched were stored in the database and displayed in reports, even if they were no longer tracked in the `feeds.yaml` configuration. This led to cluttered reports and dashboards showing obsolete sources.

## Solution

### 1. Database Schema Enhancement

Added two new columns to the `sources` table:

- **`is_active`** (BOOLEAN, default: 1): Tracks whether a source is currently active
- **`last_fetched`** (TEXT): Records when a source was last fetched

```sql
ALTER TABLE sources ADD COLUMN is_active BOOLEAN DEFAULT 1;
ALTER TABLE sources ADD COLUMN last_fetched TEXT;
```

### 2. Core Functionality

#### Source Synchronization

The `sync_sources_with_config()` method:
- Marks all sources as inactive initially
- Marks sources present in the current config as active
- Updates `last_fetched` timestamp for active sources
- Automatically runs during news fetching

#### Source Management Methods

- **`sync_sources_with_config(fetcher)`**: Sync database sources with config file
- **`deactivate_obsolete_sources(fetcher)`**: Mark sources not in config as inactive
- **`cleanup_inactive_sources(confirm=True)`**: Remove inactive sources (with confirmation)
- **`get_sources(active_only=False)`**: Get sources with optional filtering
- **`get_active_sources()`**: Convenience method for active sources only

### 3. Active Source Filtering

All news retrieval methods now support an `active_only` parameter:

- **`get_recent_news(limit, active_only=False)`**: Get recent news
- **`get_news_by_source(source_name, active_only=False)`**: Get news by source
- **`get_news_by_category(category, active_only=False)`**: Get news by category
- **`search_news(query, limit)`**: Search functionality (filtering coming soon)
- **`generate_markdown_digest(news_items, filename, active_only=False)`**: Generate digests

### 4. CLI Integration

#### New Menu Option

Added "Manage Sources" (option 7) to the main menu with submenu:

1. **Sync Sources with Config File**: Update source status based on current config
2. **Deactivate Obsolete Sources**: Mark removed sources as inactive
3. **Cleanup Inactive Sources**: Remove inactive sources (with confirmation)
4. **View Source Status**: Display all sources with status indicators
5. **Back to Main Menu**: Return to main menu

#### Enhanced Existing Menus

Added active source filtering options to:

- **Today's News Dashboard**: Choose between all sources or active only
- **Browse by Source**: Filter source list by active status
- **Browse by Category**: Filter categories by active sources
- **Generate Markdown Digest**: Filter digest content by active sources

#### Visual Indicators

- **🟢 ACTIVE**: Currently tracked sources
- **🔴 INACTIVE**: Sources no longer in config

### 5. Automatic Integration

- **Automatic Sync**: Sources are automatically synced during news fetching
- **Backward Compatibility**: All existing method calls work unchanged
- **Data Preservation**: Inactive sources are marked, not deleted

## Usage Examples

### CLI Usage

```bash
# Launch the application
python3 news_search.py

# Use the new source management features:
1. Fetch Latest News (automatically syncs sources)
7. Manage Sources
   1. Sync Sources with Config File
   2. Deactivate Obsolete Sources  
   3. Cleanup Inactive Sources
   4. View Source Status

# Filter views by active sources:
2. Browse Today's News Dashboard → Choose "active sources only"
4. Browse by Source → Choose "active sources only"
5. Browse by Category → Choose "active sources only"
```

### Programmatic Usage

```python
from news_search import NewsDatabase, NewsFetcher

db = NewsDatabase()
fetcher = NewsFetcher()

# Sync sources with config
db.sync_sources_with_config(fetcher)

# Get only active sources
active_sources = db.get_sources(active_only=True)

# Get news from active sources only
active_news = db.get_recent_news(50, active_only=True)

# Generate digest with active sources only
db.generate_markdown_digest(news_items, active_only=True)

# Clean up (with confirmation)
# db.cleanup_inactive_sources()
```

## Database Migration

The implementation includes automatic database migration:

- Existing installations will automatically get the new columns added
- All existing sources are marked as active by default
- No data loss occurs during migration

## Benefits

1. **Clean Reports**: Focus on currently tracked sources
2. **Flexibility**: Choose between comprehensive or focused views
3. **Data Preservation**: Historical data remains accessible
4. **Easy Maintenance**: Simple sync process
5. **User Control**: Manual override capabilities
6. **Backward Compatible**: No breaking changes

## Testing

Comprehensive testing was performed:

- ✅ Database schema migration works correctly
- ✅ Source synchronization matches config exactly
- ✅ Active source filtering reduces item count appropriately
- ✅ All source management methods work correctly
- ✅ Backward compatibility maintained
- ✅ Data integrity preserved
- ✅ CLI integration works smoothly

## Implementation Details

### Files Modified

- **`news_search.py`**: Main implementation file
  - Enhanced `NewsDatabase` class with new methods
  - Enhanced `NewsCLI` class with new menu options
  - Updated all news retrieval methods
  - Added automatic database migration

### Key Methods Added

```python
# Database methods
def sync_sources_with_config(self, fetcher=None):
def deactivate_obsolete_sources(self, fetcher=None):
def cleanup_inactive_sources(self, confirm=True):
def get_sources(self, active_only=False):
def get_active_sources(self):

# CLI methods
def show_source_management_menu(self):
def sync_sources_with_config(self):
def deactivate_obsolete_sources(self):
def cleanup_inactive_sources(self):
def view_source_status(self):
```

### SQL Queries

Active source filtering uses subqueries like:

```sql
SELECT * FROM news_items
WHERE source_name IN (
    SELECT name FROM sources WHERE is_active = 1
)
ORDER BY fetched_date DESC
LIMIT ?
```

## Future Enhancements

Potential future improvements:

1. **Scheduled Cleanup**: Automatic cleanup of old inactive sources
2. **Source Statistics**: Track usage statistics per source
3. **Source Reactivation**: Easy way to reactivate previously inactive sources
4. **Export/Import**: Export source configuration and import to other instances
5. **API Integration**: REST API endpoints for source management

## Conclusion

This implementation provides a robust, flexible solution for managing news sources and focusing reports on currently tracked sources. It maintains data integrity, provides user control, and preserves historical data while offering clean, focused views of active content.