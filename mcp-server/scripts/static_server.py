#!/usr/bin/env python3
"""
Static file server for widget assets on port 4444 with CORS support.
This server serves the compiled widget JavaScript files from web/dist/
and is designed to be exposed via ngrok for ChatGPT to load widgets.
"""

import http.server
import socketserver
import os
from pathlib import Path
from urllib.parse import urlparse

# Get the project root directory (parent of mcp-server)
PROJECT_ROOT = Path(__file__).parent.parent
WEB_DIST_PATH = PROJECT_ROOT / "web" / "dist"
PORT = 4444


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with CORS headers enabled."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIST_PATH), **kwargs)
    
    def end_headers(self):
        """Add CORS headers to all responses."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Max-Age", "3600")
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight."""
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        """Custom log format."""
        print(f"[{self.address_string()}] {format % args}")


def main():
    """Start the static file server."""
    # Check if web/dist exists
    if not WEB_DIST_PATH.exists():
        print(f"❌ Error: Widget dist directory not found at {WEB_DIST_PATH}")
        print("   Please run 'cd web && npm run build' first")
        return 1
    
    # Check if dist directory has files
    dist_files = list(WEB_DIST_PATH.glob("*.js"))
    if not dist_files:
        print(f"⚠ Warning: No .js files found in {WEB_DIST_PATH}")
        print("   Run 'cd web && npm run build' to create widget bundles")
    
    print("🚀 Starting static file server for widget assets...")
    print(f"📁 Serving: {WEB_DIST_PATH}")
    print(f"🌐 Port: {PORT}")
    print(f"🔓 CORS: Enabled")
    print(f"📦 Found {len(dist_files)} widget bundle(s)")
    print("")
    print(f"👉 Access widgets at: http://localhost:{PORT}/<widget-file>.js")
    print(f"👉 Example: http://localhost:{PORT}/reconciliationCard-L7VCB262.js")
    print("")
    print("💡 After starting ngrok on port 4444, set BASE_URL in .env to the ngrok URL")
    print("   Example: BASE_URL=https://your-ngrok-url.ngrok-free.app")
    print("")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        with socketserver.TCPServer(("", PORT), CORSRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        return 0
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Error: Port {PORT} is already in use")
            print(f"   Another process is using port {PORT}")
            print(f"   Kill it with: lsof -ti:{PORT} | xargs kill -9")
        else:
            print(f"❌ Error starting server: {e}")
        return 1


if __name__ == "__main__":
    exit(main())

