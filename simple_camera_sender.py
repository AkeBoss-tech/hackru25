#!/usr/bin/env python3
"""
Simple Camera Sender - Just sends camera feed to the central server
Run this on any machine with a camera to send video to the main processing server
"""

import cv2
import requests
import base64
import time
import sys
import json

# Simple setup
SERVER_URL = "http://localhost:5002"  # Change this to your main server IP
CLIENT_NAME = "Camera_1"  # Change this to identify your camera

print(f"🎥 Starting Simple Camera Sender")
print(f"📡 Server: {SERVER_URL}")
print(f"📷 Client name: {CLIENT_NAME}")

# Test server connection
try:
    response = requests.get(f"{SERVER_URL}/api/distributed/stats", timeout=5)
    if response.status_code == 200:
        print("✅ Server is running")
    else:
        print("❌ Server not responding")
        sys.exit(1)
except Exception as e:
    print(f"❌ Cannot connect to server: {e}")
    sys.exit(1)

# Find a working camera
camera = None
for i in range(5):
    print(f"Testing camera {i}...")
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            camera = cap
            print(f"✅ Found working camera {i}")
            break
        cap.release()

if camera is None:
    print("❌ No working camera found!")
    sys.exit(1)

print("🚀 Starting video stream...")
print("Press Ctrl+C to stop")

try:
    frame_count = 0
    while True:
        ret, frame = camera.read()
        if ret:
            # Compress and encode frame
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_data = base64.b64encode(buffer).decode('utf-8')
            
            # Send frame via HTTP (simpler than WebSocket for now)
            try:
                response = requests.post(f"{SERVER_URL}/api/send_frame", json={
                    'client_id': CLIENT_NAME,
                    'camera_index': 0,
                    'frame_data': frame_data,
                    'frame_number': frame_count,
                    'timestamp': time.time()
                }, timeout=1)
                
                if response.status_code == 200:
                    if frame_count % 30 == 0:  # Print every 30 frames
                        print(f"📡 Sent frame {frame_count}")
                else:
                    print(f"❌ Server error: {response.status_code}")
                    
            except Exception as e:
                if frame_count % 30 == 0:  # Don't spam errors
                    print(f"❌ Send error: {e}")
            
            frame_count += 1
        
        time.sleep(1/15)  # 15 FPS

except KeyboardInterrupt:
    print("\n🛑 Stopping camera sender...")
finally:
    camera.release()
    print("👋 Done!")
