#!/usr/bin/env python3
"""
Minimal Flask app for testing.
"""

from flask import Flask, render_template, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'running',
        'message': 'Server is working!'
    })

@app.route('/api/cameras')
def cameras():
    return jsonify({
        'cameras': [
            {'id': 0, 'properties': {'width': 1920, 'height': 1080, 'fps': 24}},
            {'id': 1, 'properties': {'width': 1920, 'height': 1080, 'fps': 15}}
        ]
    })

if __name__ == '__main__':
    print("🚀 Starting minimal Flask app...")
    app.run(debug=True, host='0.0.0.0', port=5001)
