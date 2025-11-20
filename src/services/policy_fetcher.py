"""
Policy Fetcher Service

This module handles fetching policy documents from various sources:
- HTTP/HTTPS web pages
- PDF documents
- Google Drive documents
- Local files

It extracts and cleans the text content for processing by agents.
"""

import logging
import requests
from typing import Optional, Dict, Tuple
from datetime import datetime
from urllib.parse import urlparse
import re


class PolicyFetcher:
    """
    Service for fetching policy documents from various sources.

    Supports:
    - HTTP/HTTPS web pages
    - PDF documents
    - Google Drive documents
    - Local files
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the policy fetcher.

        Args:
            logger: Logger instance for tracking operations
        """
        self.logger = logger or logging.getLogger(__name__)
        self.fetch_history: Dict = {}

    def fetch_policy_from_url(
        self,
        url: str,
        timeout: int = 10
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Fetch policy text from a URL.

        Args:
            url: URL to fetch policy from
            timeout: Request timeout in seconds

        Returns:
            Tuple of (success, text_content, metadata)
        """
        try:
            self.logger.info(f"Fetching policy from URL: {url}")

            # Add user agent to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()

            # Extract text content
            content = self._extract_text_from_html(response.text)

            metadata = {
                "source": url,
                "fetch_timestamp": datetime.now().isoformat(),
                "status_code": response.status_code,
                "content_length": len(content),
                "encoding": response.encoding
            }

            self.logger.info(
                f"Successfully fetched policy from {url} "
                f"({len(content)} characters)"
            )

            self.fetch_history[url] = metadata

            return True, content, metadata

        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch URL {url}: {str(e)}")
            return False, "", {
                "error": str(e),
                "source": url,
                "fetch_timestamp": datetime.now().isoformat()
            }

    def fetch_policy_from_file(
        self,
        filepath: str
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Fetch policy text from a local file.

        Supports .txt and .md files.

        Args:
            filepath: Path to the policy file

        Returns:
            Tuple of (success, text_content, metadata)
        """
        try:
            self.logger.info(f"Fetching policy from file: {filepath}")

            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            metadata = {
                "source": filepath,
                "fetch_timestamp": datetime.now().isoformat(),
                "content_length": len(content),
                "file_type": filepath.split('.')[-1]
            }

            self.logger.info(
                f"Successfully fetched policy from {filepath} "
                f"({len(content)} characters)"
            )

            self.fetch_history[filepath] = metadata

            return True, content, metadata

        except FileNotFoundError:
            self.logger.error(f"File not found: {filepath}")
            return False, "", {
                "error": "File not found",
                "source": filepath,
                "fetch_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error reading file {filepath}: {str(e)}")
            return False, "", {
                "error": str(e),
                "source": filepath,
                "fetch_timestamp": datetime.now().isoformat()
            }

    def _extract_text_from_html(self, html_content: str) -> str:
        """
        Extract readable text from HTML content.

        Args:
            html_content: Raw HTML content

        Returns:
            Extracted text content
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            self.logger.warning(
                "BeautifulSoup4 not available, using regex extraction"
            )
            return self._extract_text_with_regex(html_content)

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            return text

        except Exception as e:
            self.logger.warning(f"BeautifulSoup extraction failed: {str(e)}")
            return self._extract_text_with_regex(html_content)

    def _extract_text_with_regex(self, html_content: str) -> str:
        """
        Fallback regex-based HTML text extraction.

        Args:
            html_content: Raw HTML content

        Returns:
            Extracted text content
        """
        # Remove script and style tags
        content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)

        # Remove HTML tags
        content = re.sub(r'<[^>]+>', ' ', content)

        # Decode HTML entities
        import html
        content = html.unescape(content)

        # Clean up whitespace
        content = re.sub(r'\s+', ' ', content)

        return content.strip()

    def fetch_policy_from_google_docs(
        self,
        doc_id: str,
        export_format: str = "txt"
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Fetch policy from Google Docs (requires authentication).

        Args:
            doc_id: Google Docs document ID
            export_format: Export format ('txt', 'pdf', 'docx')

        Returns:
            Tuple of (success, text_content, metadata)
        """
        try:
            # This requires Google Docs API setup
            # For now, return a template response
            self.logger.info(f"Fetching from Google Docs: {doc_id}")

            # This would be implemented with google-api-client
            # For now, return placeholder
            return False, "", {
                "error": "Google Docs integration not yet configured",
                "source": f"docs.google.com/document/d/{doc_id}",
                "requires": "google-api-client library and OAuth2 setup"
            }

        except Exception as e:
            self.logger.error(f"Failed to fetch from Google Docs: {str(e)}")
            return False, "", {"error": str(e)}

    def normalize_policy_text(self, text: str) -> str:
        """
        Normalize policy text for comparison.

        Handles:
        - Extra whitespace
        - Line breaks
        - Special characters
        - HTML entities

        Args:
            text: Raw policy text

        Returns:
            Normalized text
        """
        # Decode HTML entities
        import html
        text = html.unescape(text)

        # Replace multiple spaces with single space
        text = re.sub(r'  +', ' ', text)

        # Replace multiple newlines with double newline
        text = re.sub(r'\n\n\n+', '\n\n', text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def get_policy_summary(
        self,
        text: str,
        max_length: int = 500
    ) -> str:
        """
        Generate a summary of policy text.

        Args:
            text: Full policy text
            max_length: Maximum length of summary

        Returns:
            Summary text
        """
        # Get first paragraph or first max_length characters
        first_para = text.split('\n\n')[0] if '\n\n' in text else text

        if len(first_para) > max_length:
            return first_para[:max_length].rstrip() + "..."
        else:
            return first_para

    def get_fetch_history(self) -> Dict:
        """Get history of all policy fetches."""
        return self.fetch_history

    def estimate_policy_complexity(self, text: str) -> Dict:
        """
        Estimate complexity metrics for a policy document.

        Args:
            text: Policy text

        Returns:
            Dictionary with complexity metrics
        """
        word_count = len(text.split())
        line_count = len(text.split('\n'))
        paragraph_count = len(text.split('\n\n'))

        # Estimate reading time (avg 200 words per minute)
        reading_time_minutes = word_count / 200

        return {
            "word_count": word_count,
            "line_count": line_count,
            "paragraph_count": paragraph_count,
            "estimated_reading_time_minutes": round(reading_time_minutes, 1),
            "complexity_level": (
                "simple" if word_count < 500 else
                "moderate" if word_count < 2000 else
                "complex"
            )
        }


class CachedPolicyFetcher(PolicyFetcher):
    """
    Policy fetcher with caching to avoid redundant fetches.

    Useful for frequently accessed policy sources.
    """

    def __init__(self, cache_ttl_seconds: int = 3600, logger: Optional[logging.Logger] = None):
        """
        Initialize cached fetcher.

        Args:
            cache_ttl_seconds: Cache time-to-live in seconds (default 1 hour)
            logger: Logger instance
        """
        super().__init__(logger)
        self.cache = {}
        self.cache_ttl = cache_ttl_seconds
        self.logger.info(f"Initialized cached policy fetcher (TTL: {cache_ttl_seconds}s)")

    def fetch_policy_from_url(
        self,
        url: str,
        timeout: int = 10,
        use_cache: bool = True
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Fetch policy from URL with optional caching.

        Args:
            url: URL to fetch
            timeout: Request timeout
            use_cache: Whether to use cached result if available

        Returns:
            Tuple of (success, text_content, metadata)
        """
        # Check cache
        if use_cache and url in self.cache:
            cached_data, timestamp = self.cache[url]
            age_seconds = (datetime.now() - timestamp).total_seconds()

            if age_seconds < self.cache_ttl:
                self.logger.info(f"Using cached policy for {url} (age: {age_seconds:.0f}s)")
                return cached_data

        # Fetch fresh
        success, content, metadata = super().fetch_policy_from_url(url, timeout)

        if success:
            self.cache[url] = ((success, content, metadata), datetime.now())

        return success, content, metadata

    def clear_cache(self, url: Optional[str] = None) -> None:
        """
        Clear cache entries.

        Args:
            url: Specific URL to clear, or None to clear all
        """
        if url:
            if url in self.cache:
                del self.cache[url]
                self.logger.info(f"Cleared cache for {url}")
        else:
            self.cache.clear()
            self.logger.info("Cleared entire cache")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        total_cached = len(self.cache)
        total_size = sum(
            len(data[0][1]) for data in self.cache.values()
        )

        return {
            "total_cached_items": total_cached,
            "total_cache_size_bytes": total_size,
            "cache_ttl_seconds": self.cache_ttl
        }
