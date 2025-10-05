#!/bin/bash
# Simple script to run the camera sender with virtual environment

echo "🎥 Starting Camera Sender..."
echo "Make sure the main server is running at http://localhost:5002"
echo ""

# Activate virtual environment and run camera sender
source venv/bin/activate && python3 simple_camera_sender.py
