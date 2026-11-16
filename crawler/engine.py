"""Crawler engine that handles HTTP requests, recursion, and content summarization."""
import sys
import time
import urllib.robotparser
from urllib.parse import urlparse, urljoin
from collections import deque
from typing import Set, List, Optional
import requests

from .models import CrawlResult, PageData, PageMetadata
from .parser import WebContentParser

class CrawlerEngine:
    def __init__(
        self,
        user_agent: str = "NexusCrawler/1.0 (+https://github.com/buildsprint/nexus-crawler)",
        timeout: int = 15,
        max_pages: int = 1,
        max_depth: int = 1,
        respect_robots: bool = True,
        polite_delay: float = 0.5
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_pages = max(1, min(max_pages, 20)) # Safety bound: 1..20
        self.max_depth = max(1, min(max_depth, 3))   # Safety bound: 1..3
        self.respect_robots = respect_robots
        self.polite_delay = polite_delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        })

    def _can_fetch(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            # Short timeout for robots.txt
            r = self.session.get(robots_url, timeout=5)
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
                return rp.can_fetch(self.user_agent, url)
            elif r.status_code in (401, 403):
                return False
            return True
        except Exception as e:
            # If robots.txt cannot be fetched or parsed, assume allowed by standard
            return True

    def _fetch_page(self, url: str) -> Optional[PageData]:
        sys.stderr.write(f"[*] Fetching: {url}\n")
        sys.stderr.flush()

        try:
            start_req = time.time()
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            elapsed = time.time() - start_req

            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                sys.stderr.write(f"[-] Skipping non-HTML resource: {content_type}\n")
                return None

            parser = WebContentParser(base_url=resp.url)
            parser.feed(resp.text)
            parser.finish()

            total_words = sum(len(p.split()) for p in parser.paragraphs)

            sys.stderr.write(
                f"[+] Successfully fetched {resp.url} (Status: {resp.status_code}, "
                f"Words: {total_words}, Links: {len(parser.links)}, Time: {elapsed:.2f}s)\n"
            )
            sys.stderr.flush()

            return PageData(
                url=resp.url,
                status_code=resp.status_code,
                content_type=content_type,
                metadata=parser.metadata,
                headings=parser.headings,
                paragraphs=parser.paragraphs,
                links=parser.links,
                word_count=total_words
            )
        except requests.exceptions.Timeout:
            sys.stderr.write(f"[!] Timeout error connecting to {url}\n")
            raise TimeoutError(f"Connection to {url} timed out after {self.timeout}s.")
        except requests.exceptions.SSLError as e:
            sys.stderr.write(f"[!] SSL certificate verification failed for {url}\n")
            raise ConnectionError(f"SSL certificate verification failed: {e}")
        except requests.exceptions.ConnectionError as e:
            sys.stderr.write(f"[!] Connection failed for {url}\n")
            raise ConnectionError(f"Could not connect to {url}. Host may be unreachable or DNS failed.")
        except Exception as e:
            sys.stderr.write(f"[!] Unexpected error fetching {url}: {e}\n")
            raise e

    def _generate_summary(self, pages: List[PageData]) -> str:
        if not pages:
            return "No content could be extracted."

        primary = pages[0]
        summary_lines = []

        title = primary.metadata.title or "Untitled Page"
        summary_lines.append(f"### Website Summary for {title}")
        summary_lines.append(f"**URL:** {primary.url}")

        if primary.metadata.description:
            summary_lines.append(f"\n**Meta Description:** {primary.metadata.description}")

        # Headings
        h1s = primary.headings.get("h1", [])
        h2s = primary.headings.get("h2", [])
        if h1s:
            summary_lines.append(f"\n**Main Topics (H1):** {', '.join(h1s)}")
        if h2s:
            summary_lines.append(f"**Key Sections (H2):** {', '.join(h2s[:5])}")

        # Core Paragraphs
        if primary.paragraphs:
            summary_lines.append("\n**Core Content Highlights:**")
            # Select top 3 informative paragraphs
            for p in primary.paragraphs[:4]:
                if len(p.split()) > 5:
                    summary_lines.append(f"- {p}")

        # Multi-page insights
        if len(pages) > 1:
            summary_lines.append(f"\n**Crawl Depth & Multi-page Insights:**")
            summary_lines.append(f"Successfully traversed {len(pages)} pages across domain.")
            for p in pages[1:]:
                p_title = p.metadata.title or p.url
                summary_lines.append(f"- [{p_title}]({p.url}) ({p.word_count} words)")

        # Link Summary
        internal_count = sum(1 for p in pages for l in p.links if not l.is_external)
        external_count = sum(1 for p in pages for l in p.links if l.is_external)
        summary_lines.append(f"\n**Page Connectivity:** {internal_count} internal navigation links, {external_count} external outbound links.")

        return "\n".join(summary_lines)

    def crawl(self, start_url: str) -> CrawlResult:
        start_time = time.time()
        parsed_start = urlparse(start_url)
        base_domain = parsed_start.netloc.lower()

        if not parsed_start.scheme or not parsed_start.netloc:
            return CrawlResult(
                target_url=start_url,
                success=False,
                status="failed",
                pages_crawled=0,
                total_links_found=0,
                crawl_depth=self.max_depth,
                error="Invalid URL provided: Missing scheme or hostname."
            )

        # Check robots.txt
        if not self._can_fetch(start_url):
            return CrawlResult(
                target_url=start_url,
                success=False,
                status="blocked_by_robots",
                pages_crawled=0,
                total_links_found=0,
                crawl_depth=self.max_depth,
                error=f"Crawling disallowed by robots.txt on {base_domain}."
            )

        visited: Set[str] = set()
        crawled_pages: List[PageData] = []
        total_links = 0

        # Queue items: (url, current_depth)
        queue = deque([(start_url, 1)])

        try:
            while queue and len(crawled_pages) < self.max_pages:
                current_url, depth = queue.popleft()

                # Normalize URL (strip fragment)
                clean_url = current_url.split("#")[0].rstrip("/")
                if clean_url in visited:
                    continue
                visited.add(clean_url)

                try:
                    page_data = self._fetch_page(current_url)
                except Exception as e:
                    if not crawled_pages:
                        # Root failed
                        return CrawlResult(
                            target_url=start_url,
                            success=False,
                            status="failed",
                            pages_crawled=0,
                            total_links_found=0,
                            crawl_depth=self.max_depth,
                            execution_time_seconds=round(time.time() - start_time, 2),
                            error=str(e)
                        )
                    continue

                if page_data:
                    crawled_pages.append(page_data)
                    total_links += len(page_data.links)

                    # Enqueue child links if depth allows
                    if depth < self.max_depth and len(crawled_pages) < self.max_pages:
                        for link in page_data.links:
                            if not link.is_external:
                                child_clean = link.url.split("#")[0].rstrip("/")
                                if child_clean not in visited:
                                    queue.append((link.url, depth + 1))

                # Polite rate limiting between page hits
                if queue and len(crawled_pages) < self.max_pages:
                    time.sleep(self.polite_delay)

            summary = self._generate_summary(crawled_pages)
            execution_time = round(time.time() - start_time, 2)

            return CrawlResult(
                target_url=start_url,
                success=True,
                status="completed",
                pages_crawled=len(crawled_pages),
                total_links_found=total_links,
                crawl_depth=self.max_depth,
                pages=crawled_pages,
                executive_summary=summary,
                execution_time_seconds=execution_time
            )

        except Exception as e:
            return CrawlResult(
                target_url=start_url,
                success=False,
                status="failed",
                pages_crawled=len(crawled_pages),
                total_links_found=total_links,
                crawl_depth=self.max_depth,
                execution_time_seconds=round(time.time() - start_time, 2),
                error=f"Crawl execution error: {str(e)}"
            )

