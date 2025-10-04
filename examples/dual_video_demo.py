#!/usr/bin/env python3
"""
Demo script for the dual video feed functionality.
Shows both raw and processed video feeds in the web interface.
"""

import requests
import time
import json

# Web app base URL
BASE_URL = "http://localhost:5001"

def demo_dual_video_feeds():
    """Demo the dual video feed functionality."""
    print("🎥 YOLOv8 Dual Video Feed Demo")
    print("=" * 50)
    
    # Check server status
    print("1. Checking server status...")
    try:
        response = requests.get(f"{BASE_URL}/api/status")
        data = response.json()
        print(f"✅ Server is running - Processing: {data['is_processing']}")
    except Exception as e:
        print(f"❌ Server not accessible: {e}")
        return
    
    # Get cameras
    print("\n2. Getting available cameras...")
    try:
        response = requests.get(f"{BASE_URL}/api/cameras")
        data = response.json()
        cameras = data['cameras']
        print(f"✅ Found {len(cameras)} cameras")
        for camera in cameras:
            props = camera['properties']
            print(f"   - Camera {camera['id']}: {props['width']}x{props['height']} @ {props['fps']} FPS")
    except Exception as e:
        print(f"❌ Error getting cameras: {e}")
        return
    
    # Start camera processing
    print("\n3. Starting camera processing...")
    try:
        response = requests.post(f"{BASE_URL}/api/start_camera", json={
            'camera_index': 0,
            'confidence': 0.25,
            'enable_tracking': True
        })
        data = response.json()
        if data.get('status') == 'started':
            print("✅ Camera processing started successfully")
        else:
            print(f"❌ Failed to start processing: {data}")
            return
    except Exception as e:
        print(f"❌ Error starting camera: {e}")
        return
    
    # Monitor processing for 15 seconds
    print("\n4. Monitoring dual video feed processing...")
    print("   📱 Open http://localhost:5001 in your browser to see:")
    print("   📹 Raw camera feed (left side)")
    print("   🎯 Processed feed with detections (right side)")
    print("   📊 Live statistics and detection counts")
    
    for i in range(15):
        time.sleep(1)
        try:
            response = requests.get(f"{BASE_URL}/api/status")
            data = response.json()
            stats = data.get('stats', {})
            print(f"   Frame {stats.get('total_frames', 0)}: {stats.get('total_detections', 0)} detections, {stats.get('fps', 0):.1f} FPS")
        except:
            pass
    
    # Stop processing
    print("\n5. Stopping camera processing...")
    try:
        response = requests.post(f"{BASE_URL}/api/stop_processing")
        data = response.json()
        if data.get('status') == 'stopped':
            print("✅ Camera processing stopped")
    except Exception as e:
        print(f"❌ Error stopping processing: {e}")
    
    print("\n🎉 Dual video feed demo completed!")
    print("\n📋 Features demonstrated:")
    print("   ✅ Raw camera feed display")
    print("   ✅ Processed feed with object detection")
    print("   ✅ Real-time object tracking")
    print("   ✅ Live statistics and detection counts")
    print("   ✅ WebSocket communication for live updates")
    print("   ✅ Responsive web interface")

def main():
    """Main demo function."""
    print("🚀 Starting dual video feed demonstration...")
    print(f"🌐 Make sure the web app is running at {BASE_URL}")
    print("⏹️  Press Ctrl+C to cancel")
    
    try:
        demo_dual_video_feeds()
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")

if __name__ == '__main__':
    main()
