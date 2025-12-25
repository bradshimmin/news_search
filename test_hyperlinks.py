#!/usr/bin/env python3
"""
Test terminal hyperlink support using ANSI escape codes.
This tests OSC 8 hyperlink support which is supported by many modern terminals.
"""

def hyperlink(text: str, url: str) -> str:
    """Create a clickable hyperlink using ANSI escape codes (OSC 8)."""
    # OSC 8 format: \033]8;;URL\033\\TEXT\033]8;;\033\\ 
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"

def main():
    print("Testing Terminal Hyperlink Support")
    print("=" * 50)
    
    # Test 1: Basic hyperlink
    print("Test 1 - Basic hyperlink:")
    print(hyperlink("GitHub Repository", "https://github.com/mistralai/mistral-vibe"))
    
    print("\n" + "=" * 50)
    
    # Test 2: Domain-style hyperlink
    print("Test 2 - Domain hyperlink:")
    print(hyperlink("github.com", "https://github.com/mistralai/mistral-vibe"))
    
    print("\n" + "=" * 50)
    
    # Test 3: Multiple hyperlinks
    print("Test 3 - Multiple hyperlinks:")
    print(f"Visit {hyperlink('GitHub', 'https://github.com')} or {hyperlink('Mistral', 'https://mistral.ai')}")
    
    print("\n" + "=" * 50)
    
    # Test 4: Hyperlink with emoji
    print("Test 4 - Hyperlink with emoji:")
    print(f"🔗 {hyperlink('mistral.ai', 'https://mistral.ai')}")
    
    print("\n" + "=" * 50)
    
    # Test 5: Fallback for terminals that don't support hyperlinks
    print("Test 5 - Fallback (plain text):")
    print("🔗 mistral.ai (https://mistral.ai)")
    
    print("\n" + "=" * 50)
    print("If you can click on the links above, your terminal supports OSC 8 hyperlinks!")
    print("Try clicking on the domain names to test.")

if __name__ == "__main__":
    main()