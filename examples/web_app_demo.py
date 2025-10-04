#!/usr/bin/env python3
"""
Demo script for the YOLOv8 Video Processing Web Application.
Shows how to use the web app programmatically.
"""

import requests
import time
import json
from pathlib import Path

# Web app base URL
BASE_URL = "http://localhost:5001"

def test_web_app():
    """Test the web application endpoints."""
    print("🧪 Testing YOLOv8 Web Application")
    print("=" * 50)
    
    # Test 1: Check if server is running
    print("\n1. Testing server connection...")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the web app is running.")
        print("   Run: cd web_app && python run.py")
        return False
    
    # Test 2: Get available cameras
    print("\n2. Getting available cameras...")
    try:
        response = requests.get(f"{BASE_URL}/api/cameras")
        data = response.json()
        if 'cameras' in data:
            cameras = data['cameras']
            print(f"✅ Found {len(cameras)} cameras:")
            for camera in cameras:
                props = camera['properties']
                print(f"   - Camera {camera['id']}: {props['width']}x{props['height']} @ {props['fps']} FPS")
        else:
            print("❌ No cameras found or error:", data.get('error', 'Unknown error'))
    except Exception as e:
        print(f"❌ Error getting cameras: {e}")
    
    # Test 3: Get configuration
    print("\n3. Getting configuration...")
    try:
        response = requests.get(f"{BASE_URL}/api/config")
        data = response.json()
        print("✅ Configuration:")
        print(f"   - Model: {data.get('model_path', 'Unknown')}")
        print(f"   - Confidence: {data.get('confidence_threshold', 'Unknown')}")
        print(f"   - Tracking: {data.get('enable_tracking', 'Unknown')}")
        print(f"   - Device: {data.get('device', 'Unknown')}")
    except Exception as e:
        print(f"❌ Error getting config: {e}")
    
    # Test 4: Get status
    print("\n4. Getting processing status...")
    try:
        response = requests.get(f"{BASE_URL}/api/status")
        data = response.json()
        print("✅ Status:")
        print(f"   - Processing: {data.get('is_processing', False)}")
        print(f"   - Mode: {data.get('mode', 'None')}")
        print(f"   - Frames: {data.get('stats', {}).get('total_frames', 0)}")
        print(f"   - Detections: {data.get('stats', {}).get('total_detections', 0)}")
    except Exception as e:
        print(f"❌ Error getting status: {e}")
    
    print("\n✅ Web application tests completed!")
    print("\n📱 To use the web interface:")
    print(f"   1. Open your browser")
    print(f"   2. Go to: {BASE_URL}")
    print("   3. Select camera or upload a video")
    print("   4. Click 'Start Processing'")
    
    return True

def demo_camera_processing():
    """Demo camera processing via API."""
    print("\n🎥 Demo: Starting camera processing...")
    
    # Start camera processing
    try:
        response = requests.post(f"{BASE_URL}/api/start_camera", json={
            'camera_index': 0,
            'confidence': 0.25,
            'enable_tracking': True
        })
        
        data = response.json()
        if data.get('status') == 'started':
            print("✅ Camera processing started")
            
            # Monitor for a few seconds
            print("📊 Monitoring processing for 10 seconds...")
            for i in range(10):
                time.sleep(1)
                status_response = requests.get(f"{BASE_URL}/api/status")
                status_data = status_response.json()
                stats = status_data.get('stats', {})
                print(f"   Frame {stats.get('total_frames', 0)}: {stats.get('total_detections', 0)} detections")
            
            # Stop processing
            stop_response = requests.post(f"{BASE_URL}/api/stop_processing")
            if stop_response.json().get('status') == 'stopped':
                print("✅ Camera processing stopped")
            
        else:
            print(f"❌ Failed to start camera processing: {data.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error in camera demo: {e}")

def demo_video_upload():
    """Demo video upload processing."""
    print("\n📁 Demo: Video upload processing...")
    
    # Check if we have a sample video
    sample_videos = [
        "sample_video.mp4",
        "test_video.avi",
        "../bus.jpg"  # We can use the bus image as a test
    ]
    
    video_path = None
    for video in sample_videos:
        if Path(video).exists():
            video_path = video
            break
    
    if not video_path:
        print("❌ No sample video found. Please provide a video file to test upload.")
        return
    
    print(f"📹 Using sample video: {video_path}")
    
    try:
        # Upload video
        with open(video_path, 'rb') as f:
            files = {'video': f}
            data = {
                'confidence': '0.25',
                'enable_tracking': 'true'
            }
            
            response = requests.post(f"{BASE_URL}/api/upload_video", files=files, data=data)
            result = response.json()
            
            if result.get('status') == 'started':
                print("✅ Video upload and processing started")
                
                # Monitor processing
                print("📊 Monitoring video processing...")
                for i in range(15):  # Monitor for 15 seconds
                    time.sleep(1)
                    status_response = requests.get(f"{BASE_URL}/api/status")
                    status_data = status_response.json()
                    stats = status_data.get('stats', {})
                    print(f"   Frame {stats.get('total_frames', 0)}: {stats.get('total_detections', 0)} detections")
                    
                    # Stop if processing is complete
                    if not status_data.get('is_processing', False):
                        print("✅ Video processing completed")
                        break
                
                # Stop processing if still running
                if status_data.get('is_processing', False):
                    stop_response = requests.post(f"{BASE_URL}/api/stop_processing")
                    if stop_response.json().get('status') == 'stopped':
                        print("✅ Video processing stopped")
            else:
                print(f"❌ Failed to start video processing: {result.get('error', 'Unknown error')}")
                
    except Exception as e:
        print(f"❌ Error in video upload demo: {e}")

def main():
    """Main demo function."""
    print("🚀 YOLOv8 Web Application Demo")
    print("=" * 60)
    
    # Test basic functionality
    if not test_web_app():
        return
    
    # Ask user what demo to run
    print("\n🎯 Available demos:")
    print("1. Camera processing demo")
    print("2. Video upload demo")
    print("3. Both demos")
    print("4. Skip demos")
    
    try:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            demo_camera_processing()
        elif choice == '2':
            demo_video_upload()
        elif choice == '3':
            demo_camera_processing()
            demo_video_upload()
        elif choice == '4':
            print("⏭️  Skipping demos")
        else:
            print("❌ Invalid choice")
            
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo error: {e}")
    
    print("\n🎉 Demo completed!")
    print(f"🌐 Open {BASE_URL} in your browser to use the web interface")

if __name__ == '__main__':
    main()
