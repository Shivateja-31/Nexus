#!/usr/bin/env python3
"""
NexusCLI - Application Server Entrypoint
Usage:
    python run.py
    python run.py --port 8000
"""
import sys
import os
import argparse
import uvicorn

def main():
    parser = argparse.ArgumentParser(description="Start NexusCLI Agent Web Application")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable hot reload for development")
    args = parser.parse_args()

    print("=" * 65)
    print("   _   _                     ____ _     ___ ")
    print("  | \\ | | _____  ___   _ ___/ ___| |   |_ _|")
    print("  |  \\| |/ _ \\ \\/ / | | / __| |   | |    | | ")
    print("  | |\\  |  __/>  <| |_| \\__ \\ |___| |___ | | ")
    print("  |_| \\_|\\___/_/\\_\\\\__,_|___/\\____|_____|___|")
    print("   CLI-Driven AI Chat Execution for Complex Tasks")
    print("   BUILDSPRINT ROUND 2 PROTOTYPE")
    print("=" * 65)
    print(f"[*] Server initializing on http://{args.host}:{args.port}")
    print(f"[*] Approved CLI Tools:")
    print(f"    - site-crawler  (Autonomous web crawler & structured extractor)")
    print(f"    - dns-inspector (Host & network record inspector)")
    print(f"[*] SSRF Defense: Active (Blocking private/loopback/metadata subnets)")
    print(f"[*] Open http://localhost:{args.port} in your browser to start the demo.")
    print("=" * 65)

    uvicorn.run(
        "backend.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )

if __name__ == "__main__":
    main()

