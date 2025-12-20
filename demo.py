#!/usr/bin/env python3
"""
Demo script to showcase the News Search CLI functionality
"""

from news_search import NewsDatabase, NewsFetcher

def demo():
    print("News Search CLI - Demo")
    print("=" * 40)
    
    # Initialize database and fetcher
    db = NewsDatabase()
    fetcher = NewsFetcher()
    
    # Show database stats
    news_count = len(db.get_recent_news(1000))
    sources = db.get_sources()
    
    print(f"Database contains {news_count} news items")
    print(f"From {len(sources)} different sources:")
    
    for source in sources:
        count = len(db.get_news_by_source(source['name']))
        print(f"  - {source['name']}: {count} articles")
    
    # Show categories
    categories = set(source['category'] for source in sources)
    print(f"\nCategories available: {', '.join(sorted(categories))}")
    
    # Demo search
    print(f"\nSearch demo - searching for 'AI':")
    ai_results = db.search_news('AI')
    print(f"Found {len(ai_results)} articles about AI")
    
    if ai_results:
        print(f"Latest AI article: {ai_results[0]['title']}")
    
    # Demo recent news
    print(f"\nLatest 3 news items:")
    recent = db.get_recent_news(3)
    for i, item in enumerate(recent, 1):
        print(f"{i}. {item['title']} ({item['source_name']})")
    
    # Demo markdown digest generation
    print(f"\nMarkdown Digest Feature:")
    md_file = db.generate_markdown_digest(recent, "demo_digest.md")
    print(f"Generated demo digest: {md_file}")
    
    # Check if news_digests directory exists and list files
    import os
    if os.path.exists("news_digests"):
        digest_files = [f for f in os.listdir("news_digests") if f.endswith(".md")]
        print(f"Total digest files in news_digests/: {len(digest_files)}")
    
    db.close()
    
    print(f"\nDemo completed!")
    print(f"Run './news_search.py' to use the interactive CLI")
    print(f"Markdown digests are saved in the 'news_digests/' directory")

if __name__ == "__main__":
    demo()