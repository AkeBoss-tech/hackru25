#!/usr/bin/env python3
"""
Simple startup script for the YOLOv8 Video Processing Web Application.
Uses basic Flask without SocketIO for testing.
"""

import os
import sys
import subprocess
import signal
import time
import socket
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def kill_process_on_port(port):
    """Kill any process running on the specified port."""
    try:
        # Find processes using the port
        result = subprocess.run(['lsof', '-ti', f':{port}'], 
                              capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            print(f"🔧 Found {len(pids)} process(es) using port {port}, killing them...")
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGKILL)
                    print(f"   ✅ Killed process {pid}")
                except (ValueError, ProcessLookupError):
                    pass
            time.sleep(1)  # Give processes time to die
        else:
            print(f"✅ Port {port} is available")
    except FileNotFoundError:
        print(f"⚠️  Cannot check port {port} status (lsof not available)")

def find_available_port(start_port=5001, max_attempts=10):
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return start_port  # Fallback to original port

# Import and run the Flask app (without SocketIO)
from app import app

if __name__ == '__main__':
    print("🚀 Starting YOLOv8 Video Processing Web Application (Simple Mode)...")
    print("🔧 Checking and cleaning up port conflicts...")
    
    # Kill any existing processes on port 5001
    kill_process_on_port(5001)
    
    # Find available port
    port = find_available_port(5001)
    
    if port != 5001:
        print(f"⚠️  Port 5001 was busy, using port {port} instead")
    
    print(f"📱 Open your browser and go to: http://localhost:{port}")
    print("⏹️  Press Ctrl+C to stop the server")
    print("⚠️  Note: This is simple mode without real-time features")
    print("-" * 60)
    
    try:
        app.run(debug=True, host='0.0.0.0', port=port)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)
