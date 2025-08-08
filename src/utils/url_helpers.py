"""URL helper utilities for the Crawl4AI MCP server."""

from urllib.parse import urldefrag, urlparse
from xml.etree import ElementTree as ET

import requests

from core.logging import logger


def is_sitemap(url: str) -> bool:
    """
    Check if a URL is a sitemap.

    Args:
        url: URL to check

    Returns:
        True if the URL is a sitemap, False otherwise
    """
    return url.endswith("sitemap.xml") or "sitemap" in urlparse(url).path


def is_txt(url: str) -> bool:
    """
    Check if a URL is a text file.

    Args:
        url: URL to check

    Returns:
        True if the URL is a text file, False otherwise
    """
    return url.endswith(".txt")


def parse_sitemap(sitemap_url: str) -> list[str]:
    """
    Parse a sitemap and extract URLs.

    Args:
        sitemap_url: URL of the sitemap

    Returns:
        List of URLs found in the sitemap
    """
    resp = requests.get(sitemap_url)
    urls = []

    if resp.status_code == 200:
        try:
            tree = ET.fromstring(resp.content)
            urls = [loc.text for loc in tree.findall(".//{*}loc")]
        except Exception as e:
            logger.error(f"Error parsing sitemap XML: {e}")

    return urls


def normalize_url(url: str) -> str:
    """
    Normalize a URL by removing the fragment.

    Args:
        url: URL to normalize

    Returns:
        Normalized URL without fragment
    """
    return urldefrag(url)[0]


def sanitize_url_for_logging(url: str) -> str:
    """
    Sanitize a URL for safe logging by removing sensitive information.

    This function removes authentication tokens, API keys, and other sensitive
    parameters from URLs before they are logged.

    Args:
        url: URL to sanitize

    Returns:
        Sanitized URL safe for logging
    """
    if not url:
        return ""

    try:
        parsed = urlparse(url)

        # Build sanitized URL without query parameters and fragments
        sanitized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        # If there were query parameters, indicate that they were removed
        if parsed.query:
            sanitized += "?[PARAMS_REMOVED]"

        # If there was a fragment, indicate that it was removed
        if parsed.fragment:
            sanitized += "#[FRAGMENT_REMOVED]"

        # Additional check for common auth patterns in the URL path
        if any(
            sensitive in parsed.path.lower()
            for sensitive in ["token", "key", "auth", "secret", "password"]
        ):
            # Replace the path with a generic message
            sanitized = f"{parsed.scheme}://{parsed.netloc}/[SENSITIVE_PATH]"

        return sanitized

    except Exception:
        # If parsing fails, return a generic placeholder
        return "[INVALID_URL]"


def clean_url(url: str) -> str:
    """
    Clean and normalize a URL for processing.

    This function:
    - Strips whitespace
    - Removes quotes
    - Ensures proper URL format

    Args:
        url: URL to clean

    Returns:
        Cleaned URL or empty string if invalid
    """
    if not url:
        return ""

    # Strip whitespace and quotes
    cleaned = url.strip().strip("\"'")

    # Basic validation - must start with http:// or https://
    if not cleaned.startswith(("http://", "https://")):
        return ""

    return cleaned


def extract_domain_from_url(url: str) -> str | None:
    """
    Extract domain from URL for use as source identifier.
    
    Examples:
        - "https://example.com/path" -> "example.com"
        - "https://www.example.com/path" -> "example.com"
        - "https://subdomain.example.com/path" -> "subdomain.example.com"
        - Invalid URL -> None
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain string or None if extraction fails
    """
    if not url:
        return None
        
    try:
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        if not parsed.netloc:
            return None
            
        domain = parsed.netloc.lower()
        
        # Remove 'www.' prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
            
        return domain
    except Exception:
        return None
