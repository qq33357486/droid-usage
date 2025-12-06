#!/usr/bin/env python3
"""
简单的HTTP服务器，用于运行API Key用量查询网页
解决本地文件访问API时的CORS问题，并提供API代理功能
"""

import http.server
import socketserver
import os
import sys
import signal
import urllib.request
import urllib.error
import time
import re
import threading
from collections import defaultdict

PORT = 8003
API_URL = 'https://app.factory.ai/api/organization/members/chat-usage'

RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW = 60

request_counts = defaultdict(list)

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def get_client_ip(self):
        forwarded = self.headers.get('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return self.client_address[0]
    
    def is_rate_limited(self):
        client_ip = self.get_client_ip()
        now = time.time()
        request_counts[client_ip] = [t for t in request_counts[client_ip] if now - t < RATE_LIMIT_WINDOW]
        if len(request_counts[client_ip]) >= RATE_LIMIT_REQUESTS:
            return True
        request_counts[client_ip].append(now)
        return False
    
    def validate_auth_header(self, auth_header):
        if not auth_header:
            return False, 'Authorization header is required'
        if not auth_header.startswith('Bearer '):
            return False, 'Invalid Authorization format'
        token = auth_header[7:]
        if len(token) < 20 or len(token) > 200:
            return False, 'Invalid token length'
        if not re.match(r'^[a-zA-Z0-9_\-]+$', token):
            return False, 'Invalid token format'
        return True, token
    
    def do_GET(self):
        if self.path.startswith('/api/proxy'):
            self.handle_api_proxy()
        else:
            super().do_GET()
    
    def handle_api_proxy(self):
        """处理API代理请求，转发到目标API服务器"""
        try:
            if self.is_rate_limited():
                self.send_response(429)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "Too many requests"}')
                return
            
            auth_header = self.headers.get('Authorization')
            valid, result = self.validate_auth_header(auth_header)
            if not valid:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(f'{{"error": "{result}"}}'.encode())
                return
            
            req = urllib.request.Request(API_URL)
            req.add_header('Authorization', auth_header)
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()
                content_type = response.getheader('Content-Type', 'application/json')
                
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.end_headers()
                self.wfile.write(content)
        
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_msg = 'Unauthorized' if e.code == 401 else 'API request failed'
            self.wfile.write(f'{{"error": "{error_msg}"}}'.encode())
        
        except urllib.error.URLError:
            self.send_response(503)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "Service unavailable"}')
        
        except Exception:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "Internal server error"}')
    
    def end_headers(self):
        # 添加CORS头，允许所有来源
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, User-Agent, Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        # 处理预检请求
        self.send_response(200)
        self.end_headers()

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True
    
    def serve_forever_with_shutdown(self, shutdown_flag):
        """可中断的serve_forever，通过检查shutdown_flag退出"""
        import selectors
        with selectors.DefaultSelector() as selector:
            selector.register(self.socket, selectors.EVENT_READ)
            while not shutdown_flag[0]:
                ready = selector.select(timeout=0.5)
                if ready:
                    self._handle_request_noblock()

def self_check():
    """启动后自检，验证服务是否正常运行"""
    import socket
    time.sleep(0.5)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('127.0.0.1', PORT))
        sock.close()
        if result == 0:
            print(f"[自检] 端口 {PORT} 监听正常")
        else:
            print(f"[自检] 端口 {PORT} 未监听")
    except Exception as e:
        print(f"[自检] 检测失败: {e}")

def main():
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # 启动日志
    print("=" * 50)
    print(f"[启动] Python版本: {sys.version}")
    print(f"[启动] 工作目录: {script_dir}")
    print(f"[启动] 监听端口: {PORT}")
    print(f"[启动] 启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    httpd = None
    shutdown_flag = [False]
    
    def signal_handler(signum, frame):
        print("\n[停止] 收到停止信号...")
        shutdown_flag[0] = True
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        httpd = ThreadedTCPServer(("", PORT), MyHTTPRequestHandler)
        print(f"[启动] 服务器已启动，运行在 http://localhost:{PORT}")
        
        # 启动自检线程
        threading.Thread(target=self_check, daemon=True).start()
        
        httpd.serve_forever_with_shutdown(shutdown_flag)
        
    except Exception as e:
        print(f"[错误] 启动服务器时出错: {e}")
        sys.exit(1)
    finally:
        if httpd:
            print("[停止] 正在清理资源...")
            httpd.server_close()
            print("[停止] 服务器已停止")

if __name__ == "__main__":
    main()