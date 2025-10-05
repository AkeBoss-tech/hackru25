#!/usr/bin/env python3
"""
Network Camera Sender - Enhanced version with network discovery
Run this on any machine with a camera to send video to the main processing server
"""

import cv2
import requests
import base64
import time
import sys
import json
import argparse
import socket
import threading
from datetime import datetime

# Configuration
DEFAULT_SERVER_URL = "http://localhost:5002"
DEFAULT_CLIENT_NAME = "Camera_Client"
DEFAULT_CAMERA_INDEX = 0
SEND_INTERVAL = 0.1  # Send frames every 100ms

def find_server_on_network():
    """Try to find the server on the local network."""
    print("🔍 Searching for server on local network...")
    
    # Get local IP range
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    network_base = '.'.join(local_ip.split('.')[:-1])
    
    print(f"📡 Local IP: {local_ip}")
    print(f"🌐 Searching network: {network_base}.x")
    
    found_servers = []
    
    # Check common ports
    ports_to_check = [5002, 5000, 8080, 8000]
    
    for port in ports_to_check:
        print(f"🔍 Checking port {port}...")
        
        # Check a few IPs in the network range
        for i in range(1, 255):
            if i == int(local_ip.split('.')[-1]):
                continue  # Skip our own IP
                
            test_ip = f"{network_base}.{i}"
            
            try:
                # Try to connect to the server
                response = requests.get(f"http://{test_ip}:{port}/api/distributed/stats", timeout=1)
                if response.status_code == 200:
                    server_url = f"http://{test_ip}:{port}"
                    found_servers.append(server_url)
                    print(f"✅ Found server: {server_url}")
            except:
                continue
    
    return found_servers

def test_server_connection(server_url):
    """Test if server is accessible."""
    try:
        response = requests.get(f"{server_url}/api/distributed/stats", timeout=5)
        return response.status_code == 200
    except:
        return False

def discover_cameras():
    """Discover available cameras."""
    cameras = []
    print("🔍 Discovering cameras...")
    
    for i in range(5):  # Check first 5 camera indices
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                cameras.append(i)
                print(f"✅ Camera {i} found")
            cap.release()
        else:
            cap.release()
    
    return cameras

def send_frame_to_server(server_url, client_name, camera_index, frame_data, frame_number, timestamp):
    """Send frame data to server."""
    try:
        # Convert frame to base64
        _, buffer = cv2.imencode('.jpg', frame_data)
        frame_b64 = base64.b64encode(buffer).decode('utf-8')
        
        # Prepare data
        data = {
            'client_id': client_name,
            'camera_index': camera_index,
            'frame_data': frame_b64,
            'frame_number': frame_number,
            'timestamp': timestamp
        }
        
        # Send to server
        response = requests.post(f"{server_url}/api/send_frame", 
                               json=data, 
                               timeout=5)
        
        if response.status_code == 200:
            return True
        else:
            print(f"❌ Server error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending frame: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Network Camera Sender')
    parser.add_argument('--server', '-s', help='Server URL (e.g., http://192.168.1.100:5002)')
    parser.add_argument('--name', '-n', help='Client name (e.g., Office_Camera)')
    parser.add_argument('--camera', '-c', type=int, help='Camera index (default: 0)')
    parser.add_argument('--discover', '-d', action='store_true', help='Discover servers on network')
    parser.add_argument('--list-cameras', '-l', action='store_true', help='List available cameras')
    
    args = parser.parse_args()
    
    print("🎥 Network Camera Sender")
    print("=" * 50)
    
    # List cameras if requested
    if args.list_cameras:
        cameras = discover_cameras()
        if cameras:
            print(f"📷 Available cameras: {cameras}")
        else:
            print("❌ No cameras found")
        return
    
    # Discover servers if requested
    server_url = args.server
    if args.discover or not server_url:
        found_servers = find_server_on_network()
        
        if not found_servers:
            print("❌ No servers found on network")
            print("💡 Make sure the main server is running and accessible")
            return
        
        if len(found_servers) == 1:
            server_url = found_servers[0]
            print(f"🎯 Using server: {server_url}")
        else:
            print("🔍 Multiple servers found:")
            for i, server in enumerate(found_servers):
                print(f"  {i+1}. {server}")
            
            try:
                choice = int(input("Select server (1-{}): ".format(len(found_servers))))
                server_url = found_servers[choice-1]
            except (ValueError, IndexError):
                print("❌ Invalid selection")
                return
    
    # Set default values
    client_name = args.name or DEFAULT_CLIENT_NAME
    camera_index = args.camera if args.camera is not None else DEFAULT_CAMERA_INDEX
    
    print(f"📡 Server: {server_url}")
    print(f"📷 Client name: {client_name}")
    print(f"🎥 Camera index: {camera_index}")
    
    # Test server connection
    if not test_server_connection(server_url):
        print("❌ Cannot connect to server")
        print("💡 Check if server is running and network is accessible")
        return
    
    print("✅ Server connection successful")
    
    # Test camera
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"❌ Cannot open camera {camera_index}")
        print("💡 Try --list-cameras to see available cameras")
        return
    
    print(f"✅ Camera {camera_index} opened successfully")
    
    # Start sending frames
    print("🚀 Starting to send frames...")
    print("Press Ctrl+C to stop")
    
    frame_number = 0
    last_status_time = time.time()
    frames_sent = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to read from camera")
                break
            
            timestamp = datetime.now().isoformat()
            success = send_frame_to_server(server_url, client_name, camera_index, 
                                         frame, frame_number, timestamp)
            
            if success:
                frames_sent += 1
            else:
                print("❌ Failed to send frame")
            
            frame_number += 1
            
            # Show status every 10 seconds
            if time.time() - last_status_time > 10:
                print(f"📊 Status: {frames_sent} frames sent, {frame_number} total frames")
                last_status_time = time.time()
            
            time.sleep(SEND_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping camera sender...")
    
    finally:
        cap.release()
        print(f"✅ Camera sender stopped. Sent {frames_sent} frames.")

if __name__ == "__main__":
    main()
