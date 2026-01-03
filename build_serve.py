"""Build and/or serve the litterbot-wrapped site."""

import argparse
import asyncio
import http.server
import socketserver
import webbrowser
from pathlib import Path

from fetch_data import main as fetch_main


def serve_site(port: int = 8000):
    """Start a simple HTTP server for the site directory."""
    site_dir = Path("site")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(site_dir), **kwargs)

    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"\nServing site at http://localhost:{port}")
        print("Press Ctrl+C to stop\n")
        httpd.serve_forever()


async def main():
    parser = argparse.ArgumentParser(description="Build and serve litterbot-wrapped")
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Only fetch data and build, don't serve",
    )
    args = parser.parse_args()

    # Fetch fresh data
    print("Fetching data from Litter-Robot API...")
    success = await fetch_main()

    if not success:
        print("\nFailed to fetch data. Check your credentials.")
        return

    if args.build_only:
        print("\nBuild complete. site/data.json updated.")
        return

    print("\nStarting local server...")
    webbrowser.open("http://localhost:8000")
    serve_site()


if __name__ == "__main__":
    asyncio.run(main())
