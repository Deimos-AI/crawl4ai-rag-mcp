#!/usr/bin/env python3
"""
Debug script to demonstrate and fix the import error.

The issue occurs because utils/embeddings.py uses relative imports like:
    from ..core.logging import logger

While other utils modules use absolute imports like:
    from core.logging import logger

When executed as the main script, Python cannot resolve the relative imports
because there's no parent package context.
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, '/home/krashnicov/crawl4aimcp/src')

def test_imports():
    """Test the import issue by importing the problematic function."""
    print("Testing imports...")
    
    try:
        # This should work - absolute import in url_helpers.py
        from utils.url_helpers import extract_domain_from_url
        print("✓ Successfully imported extract_domain_from_url")
        
        # Test the function itself
        result = extract_domain_from_url("https://example.com/path")
        print(f"✓ Function works: extract_domain_from_url('https://example.com/path') = {result}")
        
    except Exception as e:
        print(f"✗ Failed to import extract_domain_from_url: {e}")
        return False
    
    try:
        # This might fail because of relative imports in embeddings.py
        from utils.embeddings import add_documents_to_database
        print("✓ Successfully imported add_documents_to_database")
        
    except Exception as e:
        print(f"✗ Failed to import add_documents_to_database: {e}")
        print(f"Error type: {type(e).__name__}")
        return False
    
    return True

def simulate_crawling_scenario():
    """Simulate the exact scenario from the error log."""
    print("\nSimulating crawling scenario...")
    
    try:
        # Import the exact function from the exact line that fails
        from utils.url_helpers import extract_domain_from_url
        
        # Call it with a test URL (line 376 in crawling.py)
        result = {"url": "https://example.com/test"}
        source_id = extract_domain_from_url(result["url"])
        
        print(f"✓ extract_domain_from_url worked: {source_id}")
        
        # Now test the add_documents_to_database import (line 389 in crawling.py) 
        from utils import add_documents_to_database
        print("✓ add_documents_to_database import worked")
        
        return True
        
    except Exception as e:
        print(f"✗ Simulation failed: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Debug script for import error: 'attempted relative import beyond top-level package'")
    print("=" * 80)
    
    success = test_imports()
    if success:
        success = simulate_crawling_scenario()
    
    print("\n" + "=" * 80)
    if success:
        print("✓ All tests passed - imports are working correctly")
    else:
        print("✗ Tests failed - relative import issue confirmed")
        print("\nThe fix is to change relative imports in utils/embeddings.py to absolute imports")
        print("Change: from ..core.logging import logger")
        print("To:     from core.logging import logger")