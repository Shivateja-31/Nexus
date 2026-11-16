"""Data models for crawler results and CLI interchange."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class PageMetadata(BaseModel):
    title: str = ""
    description: str = ""
    keywords: List[str] = Field(default_factory=list)
    author: Optional[str] = None
    language: Optional[str] = None
    canonical_url: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None

class ExtractedLink(BaseModel):
    text: str
    url: str
    is_external: bool

class PageData(BaseModel):
    url: str
    status_code: int
    content_type: str = ""
    metadata: PageMetadata = Field(default_factory=PageMetadata)
    headings: Dict[str, List[str]] = Field(default_factory=dict)
    paragraphs: List[str] = Field(default_factory=list)
    links: List[ExtractedLink] = Field(default_factory=list)
    word_count: int = 0
    crawl_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class CrawlResult(BaseModel):
    target_url: str
    success: bool
    status: str
    pages_crawled: int
    total_links_found: int
    crawl_depth: int
    pages: List[PageData] = Field(default_factory=list)
    executive_summary: str = ""
    execution_time_seconds: float = 0.0
    error: Optional[str] = None

