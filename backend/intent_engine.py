"""Intent understanding layer: Parses natural-language tasks into structured CLI instructions."""
import os
import re
import json
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class TaskIntent(BaseModel):
    intent_type: str = "cli_task" # "cli_task", "conversational", "error"
    tool_name: Optional[str] = "site-crawler"
    target_url: Optional[str] = None
    cli_args: List[str] = Field(default_factory=list)
    args_dict: Dict[str, Any] = Field(default_factory=dict)
    requires_json: bool = True
    requires_summary: bool = True
    explanation: str = ""
    error_message: Optional[str] = None

class IntentEngine:
    def __init__(self):
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")

    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs or plausible domains from text, cleaning trailing punctuation."""
        # Standard URL regex
        url_matches = re.findall(r"https?://[^\s<>\"')]+", text, re.IGNORECASE)
        clean_urls = []
        for u in url_matches:
            cleaned = u.rstrip(".,;:!?'\"`)}]<>")
            if cleaned:
                clean_urls.append(cleaned)
        if clean_urls:
            return clean_urls

        # Domain regex without protocol (e.g. example.com, hacker-news.com)
        domain_matches = re.findall(r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s<>\"')]+)?\b", text, re.IGNORECASE)
        valid_domains = []
        for d in domain_matches:
            cleaned = d.rstrip(".,;:!?'\"`)}]<>")
            if not cleaned.endswith((".py", ".js", ".json", ".txt", ".md", ".html", ".exe")):
                valid_domains.append(f"https://{cleaned}")
        return valid_domains

    def _parse_heuristic(self, text: str) -> TaskIntent:
        """Deterministic NLP intent extraction using pattern analysis."""
        text_lower = text.lower()
        extracted_urls = self._extract_urls(text)

        # Conversational greetings or capability questions
        if not extracted_urls and any(g in text_lower for g in ["hello", "hi", "help", "who are you", "what can you do", "features"]):
            return TaskIntent(
                intent_type="conversational",
                tool_name=None,
                explanation="Detected informational or conversational greeting.",
                requires_json=False,
                requires_summary=False
            )

        # Check for DNS inspection intent
        if any(term in text_lower for term in ["dns", "ip address", "resolve", "host lookup"]) and extracted_urls:
            url = extracted_urls[0]
            domain = re.sub(r"^https?://", "", url).split("/")[0]
            return TaskIntent(
                intent_type="cli_task",
                tool_name="dns-inspector",
                target_url=url,
                cli_args=["--domain", domain, "--format", "json"],
                args_dict={"domain": domain, "format": "json"},
                requires_json=True,
                requires_summary=False,
                explanation=f"Identified DNS inspection task for domain '{domain}' using CLI tool 'dns-inspector'."
            )

        # Crawling / Extraction task
        crawl_triggers = ["crawl", "scrape", "extract", "fetch", "gather", "summarize", "summary", "analyze", "visit", "get info", "collect"]
        is_crawl_intent = any(t in text_lower for t in crawl_triggers) or bool(extracted_urls)

        if not is_crawl_intent or not extracted_urls:
            if is_crawl_intent and not extracted_urls:
                return TaskIntent(
                    intent_type="error",
                    tool_name="site-crawler",
                    error_message="A website URL was not found in your request. Please provide a URL (e.g., https://example.com) to crawl."
                )
            return TaskIntent(
                intent_type="conversational",
                tool_name=None,
                explanation="No actionable CLI task detected.",
                requires_json=False,
                requires_summary=False
            )

        target_url = extracted_urls[0]

        # Extract options
        requires_json = "json" in text_lower
        requires_summary = any(k in text_lower for k in ["summary", "summarise", "summarize", "overview", "important information"])

        # Page count detection
        max_pages = 1
        page_match = re.search(r"(\d+)\s*(?:pages?|sites?)", text_lower)
        if page_match:
            try:
                max_pages = max(1, min(int(page_match.group(1)), 10))
            except ValueError:
                max_pages = 1

        # Depth detection
        max_depth = 1
        depth_match = re.search(r"(?:depth|level)\s*(\d+)", text_lower)
        if depth_match:
            try:
                max_depth = max(1, min(int(depth_match.group(1)), 3))
            except ValueError:
                max_depth = 1

        # Build CLI arguments
        cli_args = [
            "--url", target_url,
            "--max-pages", str(max_pages),
            "--max-depth", str(max_depth),
            "--timeout", "15",
            "--format", "json"
        ]

        args_dict = {
            "url": target_url,
            "max_pages": max_pages,
            "max_depth": max_depth,
            "timeout": 15,
            "format": "json"
        }

        explanation = (
            f"Detected website extraction task for '{target_url}'. "
            f"Prepared CLI invocation of 'site-crawler' (max_pages={max_pages}, max_depth={max_depth}, format=JSON)."
        )

        return TaskIntent(
            intent_type="cli_task",
            tool_name="site-crawler",
            target_url=target_url,
            cli_args=cli_args,
            args_dict=args_dict,
            requires_json=requires_json,
            requires_summary=requires_summary,
            explanation=explanation
        )

    def parse(self, text: str) -> TaskIntent:
        """Parse natural language request into TaskIntent."""
        # We start with the robust NLP parser
        intent = self._parse_heuristic(text)
        return intent
