#!/usr/bin/env python3
"""
Simple test Flask app to verify basic functionality.
"""

from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello World - Flask is working!"

@app.route('/api/test')
def test():
    return {"status": "success", "message": "API is working!"}

if __name__ == '__main__':
    print("🚀 Starting simple test server...")
    print("📱 Open your browser and go to: http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)
