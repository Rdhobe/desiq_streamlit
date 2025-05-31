#!/usr/bin/env python
"""
Simple port binding test for Render.com deployment
"""
import os
import sys
import socket
import time

# Get PORT from environment variable
port = int(os.environ.get('PORT', 8000))

print(f"===== PORT BINDING TEST =====")
print(f"Starting port binding test on port {port}")

# Try to create a socket and bind to the port
try:
    print(f"Attempting to bind to port {port}...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(5)
    print(f"Successfully bound to port {port}")
    
    # Print environment info
    print("\nEnvironment variables:")
    for key, value in sorted(os.environ.items()):
        if key.lower() in ['port', 'host', 'bind', 'listen', 'gunicorn', 'django']:
            print(f"  {key}={value}")
    
    # Keep the server running for a minute to allow Render to detect the port
    print(f"\nKeeping port {port} open for 60 seconds...")
    time.sleep(60)
    
    server_socket.close()
    print("Socket closed")
    
except Exception as e:
    print(f"Error binding to port {port}: {str(e)}")
    sys.exit(1)

print("===== PORT BINDING TEST COMPLETE =====") 