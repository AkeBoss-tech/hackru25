#!/usr/bin/env python3
"""
Debug script for the Flask web application.
"""

import os
import sys
import traceback

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

print("🔍 Debugging Flask Web Application")
print("=" * 50)

try:
    print("1. Testing imports...")
    from flask import Flask, render_template, request, jsonify
    print("✅ Flask imported successfully")
    
    from flask_socketio import SocketIO
    print("✅ Flask-SocketIO imported successfully")
    
    print("2. Testing backend imports...")
    try:
        from video_processor import VideoProcessor
        from camera_handler import CameraHandler
        from config import Config
        print("✅ Backend modules imported successfully (direct import)")
    except ImportError:
        # Fallback to backend module import
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from backend.video_processor import VideoProcessor
        from backend.camera_handler import CameraHandler
        from backend.config import Config
        print("✅ Backend modules imported successfully (module import)")
    
    print("3. Creating Flask app...")
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret-key'
    print("✅ Flask app created successfully")
    
    print("4. Testing template...")
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
    if os.path.exists(template_path):
        print("✅ Template file exists")
    else:
        print("❌ Template file not found:", template_path)
    
    print("5. Testing route...")
    @app.route('/')
    def test_route():
        return "Hello World - Flask is working!"
    
    @app.route('/api/test')
    def test_api():
        return jsonify({"status": "success", "message": "API is working!"})
    
    print("✅ Routes defined successfully")
    
    print("6. Testing app startup...")
    print("✅ All tests passed! Flask app should work correctly.")
    
    print("\n🚀 Starting test server...")
    print("📱 Open http://localhost:5001 in your browser")
    print("⏹️  Press Ctrl+C to stop")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\n📋 Full traceback:")
    traceback.print_exc()
