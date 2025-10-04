#!/usr/bin/env python3
"""
Simple startup script for the YOLOv8 Video Processing Web Application.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import and run the Flask app
from web_app.app import app, socketio

if __name__ == '__main__':
    print("🚀 Starting YOLOv8 Video Processing Web Application...")
    print("📱 Open your browser and go to: http://localhost:5001")
    print("⏹️  Press Ctrl+C to stop the server")
    print("-" * 60)
    
    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)
