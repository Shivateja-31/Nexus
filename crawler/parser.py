"""HTML parser implementation for extracting structured data from HTML pages."""
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Tuple
from .models import PageMetadata, ExtractedLink

class WebContentParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.parsed_base = urlparse(base_url)
        self.base_domain = self.parsed_base.netloc.lower()

        # State tracking
        self.current_tag = None
        self.current_heading_level = None
        self.in_script_or_style = False
        self.in_title = False
        self.current_link_url = None
        self.current_link_text = []

        # Collected data
        self.title_parts = []
        self.metadata = PageMetadata()
        self.headings: Dict[str, List[str]] = {f"h{i}": [] for i in range(1, 7)}
        self.current_heading_text = []
        self.paragraphs: List[str] = []
        self.current_para_text = []
        self.links: List[ExtractedLink] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]):
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        tag_lower = tag.lower()
        self.current_tag = tag_lower

        if tag_lower in ("script", "style", "noscript"):
            self.in_script_or_style = True
            return

        if tag_lower == "title":
            self.in_title = True
            return

        if tag_lower == "meta":
            name = attr_dict.get("name", "").lower()
            prop = attr_dict.get("property", "").lower()
            content = attr_dict.get("content", "").strip()

            if name == "description":
                self.metadata.description = content
            elif name == "keywords":
                self.metadata.keywords = [k.strip() for k in content.split(",") if k.strip()]
            elif name == "author":
                self.metadata.author = content
            elif prop == "og:title":
                self.metadata.og_title = content
            elif prop == "og:description":
                self.metadata.og_description = content
            elif prop == "og:image":
                self.metadata.og_image = content

        elif tag_lower == "link":
            rel = attr_dict.get("rel", "").lower()
            if rel == "canonical":
                self.metadata.canonical_url = attr_dict.get("href", "")

        elif tag_lower == "html":
            lang = attr_dict.get("lang")
            if lang:
                self.metadata.language = lang

        elif tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.current_heading_level = tag_lower
            self.current_heading_text = []

        elif tag_lower in ("p", "article", "section", "li", "blockquote"):
            if self.current_para_text:
                full_text = " ".join("".join(self.current_para_text).split())
                if len(full_text) > 10:
                    self.paragraphs.append(full_text)
            self.current_para_text = []

        elif tag_lower == "a":
            href = attr_dict.get("href", "").strip()
            if href and not href.startswith(("javascript:", "mailto:", "tel:", "#")):
                resolved_url = urljoin(self.base_url, href)
                self.current_link_url = resolved_url
                self.current_link_text = []

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "noscript"):
            self.in_script_or_style = False
            return

        if tag_lower == "title":
            self.in_title = False
            self.metadata.title = " ".join("".join(self.title_parts).split())
            return

        if tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            if self.current_heading_level:
                text = " ".join("".join(self.current_heading_text).split())
                if text:
                    self.headings[self.current_heading_level].append(text)
            self.current_heading_level = None
            self.current_heading_text = []

        elif tag_lower in ("p", "article", "section", "li", "blockquote"):
            if self.current_para_text:
                full_text = " ".join("".join(self.current_para_text).split())
                if len(full_text) > 10:
                    self.paragraphs.append(full_text)
            self.current_para_text = []

        elif tag_lower == "a":
            if self.current_link_url:
                text = " ".join("".join(self.current_link_text).split())
                target_domain = urlparse(self.current_link_url).netloc.lower()
                is_ext = target_domain != self.base_domain and bool(target_domain)
                self.links.append(ExtractedLink(
                    text=text or self.current_link_url,
                    url=self.current_link_url,
                    is_external=is_ext
                ))
            self.current_link_url = None
            self.current_link_text = []

    def handle_data(self, data: str):
        if self.in_script_or_style:
            return

        if self.in_title:
            self.title_parts.append(data)

        if self.current_heading_level:
            self.current_heading_text.append(data)

        if self.current_tag in ("p", "article", "section", "li", "blockquote", "div", "span"):
            self.current_para_text.append(data)

        if self.current_link_url is not None:
            self.current_link_text.append(data)

    def finish(self):
        """Finalize any pending tags."""
        if self.current_para_text:
            full_text = " ".join("".join(self.current_para_text).split())
            if len(full_text) > 10:
                self.paragraphs.append(full_text)
            self.current_para_text = []

        # Deduplicate paragraphs while preserving order
        unique_paras = []
        seen = set()
        for p in self.paragraphs:
            if p not in seen and len(p.split()) >= 3:
                seen.add(p)
                unique_paras.append(p)
        self.paragraphs = unique_paras

        # Clean empty heading keys
        self.headings = {k: v for k, v in self.headings.items() if v}
