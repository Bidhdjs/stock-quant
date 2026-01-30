#!/usr/bin/env python3

import argparse
import sys
import time
from ddgs import DDGS

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

_WINDOWS = sys.platform.startswith("win")

def _safe_text(value: str) -> str:
    if not isinstance(value, str):
        value = str(value)
    if _WINDOWS:
        return value.encode("gbk", errors="replace").decode("gbk")
    return value

def _safe_print(*args, **kwargs) -> None:
    safe_args = [_safe_text(a) for a in args]
    print(*safe_args, **kwargs)

def search_with_retry(query, max_results=10, max_retries=3):
    """
    Search using DuckDuckGo and return results with URLs and text snippets.
    
    Args:
        query (str): Search query
        max_results (int): Maximum number of results to return
        max_retries (int): Maximum number of retry attempts
    """
    for attempt in range(max_retries):
        try:
            _safe_print(
                f"DEBUG: Searching for query: {query} (attempt {attempt + 1}/{max_retries})",
                file=sys.stderr,
            )
            
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                
            if not results:
                _safe_print("DEBUG: No results found", file=sys.stderr)
                return []
            
            _safe_print(f"DEBUG: Found {len(results)} results", file=sys.stderr)
            return results
                
        except Exception as e:
            _safe_print(
                f"ERROR: Attempt {attempt + 1}/{max_retries} failed: {str(e)}",
                file=sys.stderr,
            )
            if attempt < max_retries - 1:  # If not the last attempt
                _safe_print("DEBUG: Waiting 1 second before retry...", file=sys.stderr)
                time.sleep(1)  # Wait 1 second before retry
            else:
                _safe_print(f"ERROR: All {max_retries} attempts failed", file=sys.stderr)
                raise

def format_results(results):
    """Format and print search results."""
    for i, r in enumerate(results, 1):
        _safe_print(f"\n=== Result {i} ===")
        _safe_print(f"URL: {r.get('href', 'N/A')}")
        _safe_print(f"Title: {r.get('title', 'N/A')}")
        _safe_print(f"Snippet: {r.get('body', 'N/A')}")

def search(query, max_results=10, max_retries=3):
    """
    Main search function that handles search with retry mechanism.
    
    Args:
        query (str): Search query
        max_results (int): Maximum number of results to return
        max_retries (int): Maximum number of retry attempts
    """
    try:
        results = search_with_retry(query, max_results, max_retries)
        if results:
            format_results(results)
            
    except Exception as e:
        _safe_print(f"ERROR: Search failed: {str(e)}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Search using DuckDuckGo API")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--max-results", type=int, default=10,
                      help="Maximum number of results (default: 10)")
    parser.add_argument("--max-retries", type=int, default=3,
                      help="Maximum number of retry attempts (default: 3)")
    
    args = parser.parse_args()
    search(args.query, args.max_results, args.max_retries)

if __name__ == "__main__":
    main()
