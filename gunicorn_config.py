"""
Gunicorn configuration file for memory-efficient operation on Render.com.
"""
import multiprocessing
import os
import logging

# Explicitly bind to PORT environment variable
port = int(os.environ.get('PORT', '8000'))
bind = f"0.0.0.0:{port}"

# Print binding information for debugging
print(f"Gunicorn binding to: {bind}")

# Number of worker processes
# Use fewer workers to reduce memory usage
workers = int(os.environ.get('WEB_CONCURRENCY', '2'))  # Reduced to 2 workers

# Number of threads per worker
threads = int(os.environ.get('GUNICORN_THREADS', '4'))  # Increased threads to handle concurrency

# Worker type
# 'sync' is standard, consider 'gevent' for higher concurrency
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'sync')

# Timeout for a worker's processing of a request (seconds)
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '120'))  # Increased from 60 to 120

# Maximum number of requests a worker will process before restarting
# This helps prevent memory leaks
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', '300'))  # Reduced from 500
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', '50'))

# Logging configuration
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr
capture_output = True
access_log_format = '%({X-Forwarded-For}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# DO NOT preload application to improve memory usage
preload_app = False

# Graceful timeout (seconds) - how long to wait for workers to finish their current requests
graceful_timeout = int(os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', '30'))

# For HTTPS behind a proxy
forwarded_allow_ips = '*'
secure_scheme_headers = {
    'X-Forwarded-Proto': 'https',
}

# Keep-alive settings
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', '2'))

# Worker connections (only for async workers)
worker_connections = int(os.environ.get('GUNICORN_WORKER_CONNECTIONS', '750'))  # Reduced from 1000

# Process naming
proc_name = 'desiq_gunicorn'

# Worker check interval (seconds)
check_worker_timeout = 15

# Worker abort checks
def worker_check_memory_usage(worker):
    try:
        import psutil, os
        process = psutil.Process(worker.pid)
        memory_info = process.memory_info()
        memory_usage_mb = memory_info.rss / 1024 / 1024  # Convert to MB
        memory_limit_mb = int(os.environ.get('WORKER_MEMORY_LIMIT_MB', '450'))
        
        if memory_usage_mb > memory_limit_mb:
            worker.log.warning(f"Worker {worker.pid} using too much memory: {memory_usage_mb:.2f} MB (limit: {memory_limit_mb} MB). Recycling worker.")
            return True  # Abort the worker
        return False
    except Exception as e:
        worker.log.error(f"Error checking worker memory: {str(e)}")
        return False

# Server hooks for better orchestration
def on_starting(server):
    """Log when server starts"""
    server.log.info("Starting Gunicorn server...")

def on_exit(server):
    """Log when server exits"""
    server.log.info("Shutting down Gunicorn server...")

def post_fork(server, worker):
    """Actions to take after forking a worker"""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def worker_abort(worker):
    """Log worker abort"""
    worker.log.warning(f"Worker aborted (pid: {worker.pid})")
    
    # Try to gather information about the worker state
    try:
        import psutil, traceback, sys
        process = psutil.Process(worker.pid)
        memory_info = process.memory_info()
        memory_usage_mb = memory_info.rss / 1024 / 1024  # Convert to MB
        cpu_percent = process.cpu_percent(interval=1.0)
        
        worker.log.warning(f"Aborted worker stats - Memory: {memory_usage_mb:.2f}MB, CPU: {cpu_percent:.1f}%")
    except:
        worker.log.error(f"Could not gather worker stats: {traceback.format_exc()}")

def worker_int(worker):
    """Log worker interrupt"""
    worker.log.info(f"Worker interrupted (pid: {worker.pid})")

def pre_exec(server):
    """Log before exec"""
    server.log.info("Forking master process")

def worker_exit(server, worker):
    """Log worker exit and gather stats"""
    try:
        worker.log.info(f"Worker exiting (pid: {worker.pid})")
    except:
        pass

def child_exit(server, worker):
    """Handler for SIGCHLD"""
    worker_count = len(server.WORKERS)
    server.log.info(f"Child exit, current workers: {worker_count}")
    
    # If too few workers, log critical warning
    if worker_count < server.cfg.workers // 2:
        server.log.critical(f"WARNING: Only {worker_count} workers left out of {server.cfg.workers}")

# Setup a health check endpoint
def when_ready(server):
    """Actions to take when server is ready to accept connections"""
    # Set up a simple HTTP server for health checks
    import threading
    import http.server
    import socketserver
    
    class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(404)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Not Found")
                
        def log_message(self, format, *args):
            # Suppress logging
            pass
    
    def run_health_server():
        try:
            health_port = int(os.environ.get("HEALTH_PORT", "8081"))
            with socketserver.TCPServer(("", health_port), HealthCheckHandler) as httpd:
                server.log.info(f"Health check server started on port {health_port}")
                httpd.serve_forever()
        except Exception as e:
            server.log.error(f"Health check server error: {str(e)}")
    
    # Start the health check server in a separate thread
    health_thread = threading.Thread(target=run_health_server)
    health_thread.daemon = True
    health_thread.start()
    
    server.log.info("Gunicorn server is ready!") 