#!/bin/bash
# Network Camera Sender Startup Script
# Run this on any computer with a camera to connect to the distributed system

echo "🌐 Network Camera Sender"
echo "=========================="
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo "💡 Please install Python 3 and try again"
    exit 1
fi

# Check if required packages are installed
echo "🔍 Checking dependencies..."
python3 -c "import cv2, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Installing required packages..."
    pip3 install opencv-python requests
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install packages"
        echo "💡 Try: pip3 install opencv-python requests"
        exit 1
    fi
fi

echo "✅ Dependencies OK"
echo ""

# Check if network_camera_sender.py exists
if [ ! -f "network_camera_sender.py" ]; then
    echo "❌ network_camera_sender.py not found"
    echo "💡 Make sure you're in the correct directory"
    echo "💡 Or download the script from the main server"
    exit 1
fi

echo "🎥 Starting Network Camera Sender..."
echo "💡 This will auto-discover servers on your network"
echo "💡 Press Ctrl+C to stop"
echo ""

# Run the network camera sender with auto-discovery
python3 network_camera_sender.py --discover
