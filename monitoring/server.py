#!/usr/bin/env python3
"""
Adelie Agent 모니터링 대시보드 서버

사용법:
  python monitoring/server.py
  
브라우저에서 http://localhost:8090 접속
"""

import http.server
import socketserver
import os
import sys

PORT = 8090
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()


def main():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"""
🐧 Adelie Agent Monitor
========================
대시보드: http://localhost:{PORT}

로그를 보려면 브라우저에서 채팅창과 함께 사용하세요.
종료하려면 Ctrl+C를 누르세요.
""")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 모니터링 서버 종료")
            sys.exit(0)


if __name__ == "__main__":
    main()
