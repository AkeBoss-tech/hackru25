#!/bin/bash
# Camera Client Startup Script
# This script starts a camera client that connects to the main backend server

# Configuration
SERVER_URL="http://localhost:5002"
CLIENT_ID="camera_client_$(hostname)_$(date +%s)"
MAX_CAMERAS=5
QUALITY=80
FPS=15

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎥 Starting Camera Client${NC}"
echo -e "${BLUE}========================${NC}"
echo -e "Server URL: ${YELLOW}$SERVER_URL${NC}"
echo -e "Client ID: ${YELLOW}$CLIENT_ID${NC}"
echo -e "Max Cameras: ${YELLOW}$MAX_CAMERAS${NC}"
echo -e "Quality: ${YELLOW}$QUALITY${NC}"
echo -e "FPS: ${YELLOW}$FPS${NC}"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 is not installed or not in PATH${NC}"
    exit 1
fi

# Check if the camera client script exists
if [ ! -f "camera_client.py" ]; then
    echo -e "${RED}❌ camera_client.py not found in current directory${NC}"
    exit 1
fi

# Check if required packages are installed
echo -e "${BLUE}🔍 Checking dependencies...${NC}"
python3 -c "import cv2, socketio, numpy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Required Python packages not found${NC}"
    echo -e "${YELLOW}Please install required packages:${NC}"
    echo "pip install opencv-python python-socketio numpy"
    exit 1
fi

echo -e "${GREEN}✅ Dependencies OK${NC}"
echo ""

# Start the camera client
echo -e "${BLUE}🚀 Starting camera client...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

python3 camera_client.py \
    --server "$SERVER_URL" \
    --client-id "$CLIENT_ID" \
    --max-cameras "$MAX_CAMERAS" \
    --quality "$QUALITY" \
    --fps "$FPS"

echo -e "${BLUE}👋 Camera client stopped${NC}"
