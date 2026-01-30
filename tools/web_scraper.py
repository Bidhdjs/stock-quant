#!/usr/bin/env
import asyncio
import argparse
import sys
import os
from typing import List, Optional
import re
from playwright.async_api import async_playwright
import html5lib
from multiprocessing import Pool
import time
from urllib.parse import urlparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

def _detect_charset(html_bytes: bytes, content_type: Optional[str]) -> str:
    """Best-effort charset detection for HTML bytes."""
    if content_type:
        match = re.search(r"charset=([^;]+)", content_type, re.IGNORECASE)
        if match:
            return match.group(1).strip().strip('"').strip("'")
    head = html_bytes[:4096].decode("ascii", errors="ignore")
    match = re.search(r"charset=([\\w-]+)", head, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    if "gbk" in head.lower() or "gb2312" in head.lower():
        return "gb18030"
    return "utf-8"


def _mojibake_score(text: str) -> int:
    if not text:
        return 10**9
    mojibake_markers = ["锟", "�", "\ufffd", "銆"]
    return sum(text.count(marker) for marker in mojibake_markers)


def _looks_garbled(text: str) -> bool:
    if not text:
        return True
    hits = _mojibake_score(text)
    return hits > max(5, len(text) // 200)


def _decode_html(html_bytes: bytes, content_type: Optional[str]) -> str:
    detected = _detect_charset(html_bytes, content_type)
    candidates = []
    for enc in [detected, "utf-8", "gb18030"]:
        if enc:
            try:
                candidates.append((enc, html_bytes.decode(enc, errors="replace")))
            except Exception:
                continue
    if not candidates:
        return html_bytes.decode("utf-8", errors="replace")
    # Pick the decoding with lowest mojibake score; prefer utf-8 on tie
    candidates.sort(key=lambda item: (_mojibake_score(item[1]), 0 if item[0] == "utf-8" else 1))
    return candidates[0][1]


def _decode_with_requests(url: str) -> Optional[str]:
    try:
        import requests
    except Exception:
        return None

    try:
        resp = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        content = resp.content
        encoding = resp.encoding
        if not encoding or encoding.lower() in {"iso-8859-1", "latin-1"}:
            try:
                import chardet  # type: ignore
                encoding = chardet.detect(content).get("encoding")
            except Exception:
                encoding = None
        if not encoding:
            try:
                from charset_normalizer import from_bytes  # type: ignore
                best = from_bytes(content).best()
                if best:
                    encoding = best.encoding
            except Exception:
                encoding = None
        if not encoding:
            encoding = _detect_charset(content, resp.headers.get("content-type"))
        try:
            return content.decode(encoding, errors="replace")
        except Exception:
            return _decode_html(content, resp.headers.get("content-type"))
    except Exception:
        return None


async def fetch_page(url: str, context) -> Optional[str]:
    """Asynchronously fetch a webpage's content."""
    page = await context.new_page()
    try:
        logger.info(f"Fetching {url}")
        response = await page.goto(url)
        await page.wait_for_load_state('networkidle')
        content_type = response.headers.get("content-type") if response else None
        content = None
        if response:
            html_bytes = await response.body()
            content = _decode_html(html_bytes, content_type)
            if _looks_garbled(content):
                try:
                    content = await response.text()
                except Exception:
                    pass
        if not content or _looks_garbled(content):
            content = await page.content()
        if _looks_garbled(content):
            fallback = _decode_with_requests(url)
            if fallback:
                content = fallback
        logger.info(f"Successfully fetched {url}")
        return content
    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
        return None
    finally:
        await page.close()

def parse_html(html_content: Optional[str]) -> str:
    """Parse HTML content and extract text with hyperlinks in markdown format."""
    if not html_content:
        return ""
    
    try:
        document = html5lib.parse(html_content)
        result = []
        seen_texts = set()  # To avoid duplicates
        
        def should_skip_element(elem) -> bool:
            """Check if the element should be skipped."""
            # Skip script and style tags
            if elem.tag in ['{http://www.w3.org/1999/xhtml}script', 
                          '{http://www.w3.org/1999/xhtml}style']:
                return True
            # Skip empty elements or elements with only whitespace
            if not any(text.strip() for text in elem.itertext()):
                return True
            return False
        
        def process_element(elem, depth=0):
            """Process an element and its children recursively."""
            if should_skip_element(elem):
                return
            
            # Handle text content
            if hasattr(elem, 'text') and elem.text:
                text = elem.text.strip()
                if text and text not in seen_texts:
                    # Check if this is an anchor tag
                    if elem.tag == '{http://www.w3.org/1999/xhtml}a':
                        href = None
                        for attr, value in elem.items():
                            if attr.endswith('href'):
                                href = value
                                break
                        if href and not href.startswith(('#', 'javascript:')):
                            # Format as markdown link
                            link_text = f"[{text}]({href})"
                            result.append("  " * depth + link_text)
                            seen_texts.add(text)
                    else:
                        result.append("  " * depth + text)
                        seen_texts.add(text)
            
            # Process children
            for child in elem:
                process_element(child, depth + 1)
            
            # Handle tail text
            if hasattr(elem, 'tail') and elem.tail:
                tail = elem.tail.strip()
                if tail and tail not in seen_texts:
                    result.append("  " * depth + tail)
                    seen_texts.add(tail)
        
        # Start processing from the body tag
        body = document.find('.//{http://www.w3.org/1999/xhtml}body')
        if body is not None:
            process_element(body)
        else:
            # Fallback to processing the entire document
            process_element(document)
        
        # Filter out common unwanted patterns
        filtered_result = []
        for line in result:
            # Skip lines that are likely to be noise
            if any(pattern in line.lower() for pattern in [
                'var ', 
                'function()', 
                '.js',
                '.css',
                'google-analytics',
                'disqus',
                '{',
                '}'
            ]):
                continue
            filtered_result.append(line)
        
        return '\n'.join(filtered_result)
    except Exception as e:
        logger.error(f"Error parsing HTML: {str(e)}")
        return ""

async def process_urls(urls: List[str], max_concurrent: int = 5) -> List[str]:
    """Process multiple URLs concurrently."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            # Create browser contexts
            n_contexts = min(len(urls), max_concurrent)
            contexts = [await browser.new_context() for _ in range(n_contexts)]
            
            # Create tasks for each URL
            tasks = []
            for i, url in enumerate(urls):
                context = contexts[i % len(contexts)]
                task = fetch_page(url, context)
                tasks.append(task)
            
            # Gather results
            html_contents = await asyncio.gather(*tasks)
            
            # Parse HTML contents in parallel
            with Pool() as pool:
                results = pool.map(parse_html, html_contents)
                
            return results
            
        finally:
            # Cleanup
            for context in contexts:
                await context.close()
            await browser.close()

def validate_url(url: str) -> bool:
    """Validate if the given string is a valid URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def main():
    parser = argparse.ArgumentParser(description='Fetch and extract text content from webpages.')
    parser.add_argument('urls', nargs='+', help='URLs to process')
    parser.add_argument('--max-concurrent', type=int, default=5,
                       help='Maximum number of concurrent browser instances (default: 5)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Validate URLs
    valid_urls = []
    for url in args.urls:
        if validate_url(url):
            valid_urls.append(url)
        else:
            logger.error(f"Invalid URL: {url}")
    
    if not valid_urls:
        logger.error("No valid URLs provided")
        sys.exit(1)
    
    start_time = time.time()
    try:
        results = asyncio.run(process_urls(valid_urls, args.max_concurrent))
        
        # Print results to stdout
        for url, text in zip(valid_urls, results):
            print(f"\n=== Content from {url} ===")
            print(text)
            print("=" * 80)
        
        logger.info(f"Total processing time: {time.time() - start_time:.2f}s")
        
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 
