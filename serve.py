#!/usr/bin/env python3
"""Simple HTTP server for testing the dashboard"""
import http.server
import socketserver
import os

PORT = 8080
DIRECTORY = "/home/dwatson/projects/plant_dashboard"

os.chdir(DIRECTORY)

Handler = http.server.SimpleHTTPRequestHandler
Handler.extensions_map.update({
    '.json': 'application/json',
})

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving at http://localhost:{PORT}")
    print(f"Dashboard: http://localhost:{PORT}/nuclear_dashboard_v2.html")
    print("Press Ctrl+C to stop")
    httpd.serve_forever()
