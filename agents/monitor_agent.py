"""
Policy Monitor Agent - Web Scraper & Tracker
==============================================
Responsibilities:
- Access Google Drive to read policy source URLs
- Use Google Search to find official policy pages
- Extract policy text from websites
- Store snapshots of current policies
"""

import logging
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PolicySnapshot:
    """Represents a snapshot of a policy at a point in time"""
    policy_name: str
    source_url: str
    content: str
    extracted_at: datetime
    character_count: int
    word_count: int
    status_code: int
    error: Optional[str] = None


class PolicyMonitorAgent:
    """
    Agent that monitors official policy sources
    
    Responsibilities:
    1. Read policy sources from Google Drive
    2. Fetch current content from official URLs
    3. Extract text from web pages
    4. Store snapshots for comparison
    5. Handle errors gracefully
    """
    
    def __init__(self, timeout: int = 30):
        """
        Initialize the monitor agent
        
        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self.policy_snapshots: List[PolicySnapshot] = []
        self.session = requests.Session()
        
        # Set user agent to avoid blocking
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        logger.info(f"Monitor Agent initialized (timeout: {timeout}s)")
    
    async def scan_policy_sources(self, policy_name: str) -> Dict:
        """
        Scan official policy sources for updates
        
        Args:
            policy_name: Name of the policy to scan
            
        Returns:
            Dictionary with scan results
        """
        logger.info(f"Scanning policy sources for: {policy_name}")
        
        try:
            # Step 1: Get policy sources from Google Drive
            # In production, this would fetch from Drive MCP
            sources = await self._get_policy_sources(policy_name)
            
            if not sources:
                return {
                    "success": False,
                    "error": f"No sources found for {policy_name}"
                }
            
            # Step 2: Fetch content from each source
            snapshots = []
            for source_url in sources:
                snapshot = await self._fetch_policy_content(policy_name, source_url)
                snapshots.append(snapshot)
                
                # Small delay to avoid overwhelming servers
                await asyncio.sleep(1)
            
            # Store snapshots
            self.policy_snapshots.extend(snapshots)
            
            # Step 3: Analyze fetched content
            successful_fetches = sum(1 for s in snapshots if s.status_code == 200)
            total_fetches = len(snapshots)
            
            logger.info(
                f"Scanned {total_fetches} sources for {policy_name}, "
                f"{successful_fetches} successful"
            )
            
            return {
                "success": True,
                "policy_name": policy_name,
                "sources_count": total_fetches,
                "successful_fetches": successful_fetches,
                "snapshots": snapshots,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error scanning policy sources: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_policy_sources(self, policy_name: str) -> List[str]:
        """
        Get policy sources from Google Drive Policy_Sources sheet
        
        Args:
            policy_name: Name of the policy
            
        Returns:
            List of official URLs to monitor
            
        NOTE: In production, this would use Google Drive MCP
        """
        # Mock implementation for demonstration
        # In production: fetch from Google Sheet via Drive MCP
        
        sources_map = {
            "CDC COVID Guidelines": [
                "https://www.cdc.gov/coronavirus/2019-ncov/index.html",
                "https://www.cdc.gov/coronavirus/2019-ncov/downloads/index.html"
            ],
            "OSHA Safety Rules": [
                "https://www.osha.gov/regulations/osha-standards",
                "https://www.osha.gov/injury-tracking"
            ],
            "Event Planning Policy": [
                "https://www.example-event-org.com/policies"
            ],
            "Workplace Safety Policy": [
                "https://www.example-corp.com/safety-guidelines"
            ]
        }
        
        return sources_map.get(policy_name, [])
    
    async def _fetch_policy_content(
        self,
        policy_name: str,
        source_url: str
    ) -> PolicySnapshot:
        """
        Fetch content from a policy URL
        
        Args:
            policy_name: Name of the policy
            source_url: URL to fetch from
            
        Returns:
            PolicySnapshot with fetched content
        """
        logger.info(f"Fetching policy from: {source_url}")
        
        try:
            # Make HTTP request
            response = self.session.get(source_url, timeout=self.timeout)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {source_url}: {response.status_code}")
                return PolicySnapshot(
                    policy_name=policy_name,
                    source_url=source_url,
                    content="",
                    extracted_at=datetime.now(),
                    character_count=0,
                    word_count=0,
                    status_code=response.status_code,
                    error=f"HTTP {response.status_code}"
                )
            
            # Extract text from HTML
            content = self._extract_text_from_html(response.text, source_url)
            
            # Normalize and clean content
            content = self._normalize_policy_text(content)
            
            # Calculate metrics
            character_count = len(content)
            word_count = len(content.split())
            
            logger.info(
                f"Successfully fetched {policy_name}: "
                f"{character_count} chars, {word_count} words"
            )
            
            snapshot = PolicySnapshot(
                policy_name=policy_name,
                source_url=source_url,
                content=content,
                extracted_at=datetime.now(),
                character_count=character_count,
                word_count=word_count,
                status_code=response.status_code
            )
            
            return snapshot
            
        except requests.Timeout:
            logger.error(f"Timeout fetching {source_url}")
            return PolicySnapshot(
                policy_name=policy_name,
                source_url=source_url,
                content="",
                extracted_at=datetime.now(),
                character_count=0,
                word_count=0,
                status_code=0,
                error="Timeout"
            )
        
        except requests.RequestException as e:
            logger.error(f"Request error fetching {source_url}: {str(e)}")
            return PolicySnapshot(
                policy_name=policy_name,
                source_url=source_url,
                content="",
                extracted_at=datetime.now(),
                character_count=0,
                word_count=0,
                status_code=0,
                error=str(e)
            )
        
        except Exception as e:
            logger.error(f"Unexpected error fetching {source_url}: {str(e)}")
            return PolicySnapshot(
                policy_name=policy_name,
                source_url=source_url,
                content="",
                extracted_at=datetime.now(),
                character_count=0,
                word_count=0,
                status_code=0,
                error=str(e)
            )
    
    def _extract_text_from_html(self, html_content: str, source_url: str) -> str:
        """
        Extract clean text from HTML content
        
        Args:
            html_content: Raw HTML content
            source_url: URL for relative link resolution
            
        Returns:
            Extracted and cleaned text
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try to find main content area first
            main_content = soup.find('main')
            if main_content:
                text = main_content.get_text()
            else:
                # Fall back to body
                body = soup.find('body')
                if body:
                    text = body.get_text()
                else:
                    text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logger.warning(f"Error extracting text from HTML: {str(e)}")
            return ""
    
    def _normalize_policy_text(self, text: str) -> str:
        """
        Normalize policy text for comparison
        
        Args:
            text: Raw policy text
            
        Returns:
            Normalized text
        """
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Standardize line breaks
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _estimate_complexity(self, content: str) -> Dict:
        """
        Estimate policy complexity based on content
        
        Args:
            content: Policy content text
            
        Returns:
            Dictionary with complexity metrics
        """
        word_count = len(content.split())
        sentence_count = len([s for s in content.split('.') if s.strip()])
        paragraph_count = len([p for p in content.split('\n') if p.strip()])
        
        # Simple complexity scoring
        if word_count < 500:
            complexity = "simple"
        elif word_count < 2000:
            complexity = "moderate"
        else:
            complexity = "complex"
        
        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "complexity_level": complexity
        }
    
    def get_latest_snapshot(self, policy_name: str) -> Optional[PolicySnapshot]:
        """
        Get the most recent snapshot for a policy
        
        Args:
            policy_name: Name of the policy
            
        Returns:
            Latest PolicySnapshot or None
        """
        matching_snapshots = [
            s for s in self.policy_snapshots
            if s.policy_name == policy_name
        ]
        
        if not matching_snapshots:
            return None
        
        return max(matching_snapshots, key=lambda s: s.extracted_at)
    
    def get_monitoring_status(self) -> Dict:
        """
        Get overall monitoring status
        
        Returns:
            Dictionary with monitoring statistics
        """
        total_snapshots = len(self.policy_snapshots)
        successful_snapshots = sum(
            1 for s in self.policy_snapshots
            if s.status_code == 200
        )
        failed_snapshots = sum(
            1 for s in self.policy_snapshots
            if s.status_code != 200
        )
        
        unique_policies = len(set(s.policy_name for s in self.policy_snapshots))
        unique_sources = len(set(s.source_url for s in self.policy_snapshots))
        
        return {
            "total_snapshots": total_snapshots,
            "successful_snapshots": successful_snapshots,
            "failed_snapshots": failed_snapshots,
            "success_rate": (successful_snapshots / total_snapshots * 100) if total_snapshots > 0 else 0,
            "unique_policies": unique_policies,
            "unique_sources": unique_sources,
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        monitor = PolicyMonitorAgent()
        
        # Scan a policy
        result = await monitor.scan_policy_sources("CDC COVID Guidelines")
        print(f"Scan result: {result['success']}")
        print(f"Snapshots collected: {result.get('successful_fetches', 0)}")
    
    asyncio.run(main())
