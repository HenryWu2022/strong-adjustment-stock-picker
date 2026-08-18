#!/usr/bin/env python3
"""HTTP 服务 — 供浏览器加载结果"""
import http.server, subprocess, sys, os, webbrowser, threading, time

DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(DIR)
PORT = 8899

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, f, *a): pass

def main():
    try: import baostock
    except ImportError: subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'baostock', '-q'])

    server = http.server.HTTPServer(('127.0.0.1', PORT), Handler)
    url = f'http://127.0.0.1:{PORT}/index.html'
    print(f'  http://127.0.0.1:{PORT}')
    threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()
    try: server.serve_forever()
    except KeyboardInterrupt: server.shutdown()

if __name__ == '__main__': main()
