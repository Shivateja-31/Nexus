#!/usr/bin/env python3
"""
NexusCrawler CLI Tool
Usage:
    python -m crawler.cli --url https://example.com --format json
    python site-crawler.py --url https://example.com --max-pages 2
"""
import sys
import os
import json
import argparse
from datetime import datetime

# Allow running directly or as module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.engine import CrawlerEngine
from crawler.models import CrawlResult

def parse_args():
    parser = argparse.ArgumentParser(
        prog="site-crawler",
        description="Autonomous CLI website crawler, parser, and structured information extractor.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--url", "-u", required=True, help="Target URL to crawl (must start with http:// or https://)")
    parser.add_argument("--max-pages", "-p", type=int, default=1, help="Maximum number of pages to traverse (1-20)")
    parser.add_argument("--max-depth", "-d", type=int, default=1, help="Maximum traversal link depth (1-3)")
    parser.add_argument("--timeout", "-t", type=int, default=15, help="Request timeout per page in seconds")
    parser.add_argument("--format", "-f", choices=["json", "summary", "full"], default="json", help="Output format")
    parser.add_argument("--output-file", "-o", type=str, default=None, help="Save structured output to file path")
    parser.add_argument("--ignore-robots", action="store_true", help="Bypass robots.txt restrictions (use responsibly)")
    parser.add_argument("--user-agent", type=str, default="NexusCrawler/1.0 (+https://github.com/buildsprint/nexus-crawler)", help="Custom User-Agent header")
    return parser.parse_args()

def main():
    args = parse_args()
    start_time = datetime.utcnow()

    sys.stderr.write(f"====================================================\n")
    sys.stderr.write(f"  NEXUS-CRAWLER CLI TOOL v1.0.0\n")
    sys.stderr.write(f"  Target: {args.url}\n")
    sys.stderr.write(f"  Max Pages: {args.max_pages} | Max Depth: {args.max_depth} | Timeout: {args.timeout}s\n")
    sys.stderr.write(f"  Started: {start_time.isoformat()}Z\n")
    sys.stderr.write(f"====================================================\n")
    sys.stderr.flush()

    # Basic input checks
    if not args.url.startswith(("http://", "https://")):
        sys.stderr.write(f"[ERROR] Invalid URL: Must start with http:// or https://. Received '{args.url}'\n")
        sys.exit(2)

    try:
        engine = CrawlerEngine(
            user_agent=args.user_agent,
            timeout=args.timeout,
            max_pages=args.max_pages,
            max_depth=args.max_depth,
            respect_robots=not args.ignore_robots
        )

        result = engine.crawl(args.url)

        if not result.success:
            sys.stderr.write(f"[ERROR] Crawl failed: {result.error}\n")
            # Output structured failure JSON to stdout so backend receives structured error details
            if args.format == "json" or args.format == "full":
                sys.stdout.write(json.dumps(result.model_dump(), indent=2) + "\n")
            else:
                sys.stdout.write(f"ERROR: {result.error}\n")
            sys.exit(1)

        sys.stderr.write(f"[OK] Crawl finished successfully in {result.execution_time_seconds}s. Pages: {result.pages_crawled}, Links: {result.total_links_found}\n")

        # Handle output format
        if args.format == "json":
            json_output = json.dumps(result.model_dump(), indent=2)
            sys.stdout.write(json_output + "\n")
            if args.output_file:
                with open(args.output_file, "w", encoding="utf-8") as f:
                    f.write(json_output)
                sys.stderr.write(f"[+] Output written to {args.output_file}\n")

        elif args.format == "summary":
            sys.stdout.write(result.executive_summary + "\n")

        elif args.format == "full":
            output_obj = {
                "summary": result.executive_summary,
                "data": result.model_dump()
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + "\n")

        sys.exit(0)

    except KeyboardInterrupt:
        sys.stderr.write(f"\n[!] Crawl interrupted by user.\n")
        sys.exit(130)
    except Exception as e:
        sys.stderr.write(f"[FATAL] Uncaught exception: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()

