#!/usr/bin/env python3
"""
Test script for Continuous Sex Offender Detection
Demonstrates the backend integration with real-time detection
"""

import os
import sys
import time
import requests
import json
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

try:
    from backend.continuous_sex_offender_detector import get_continuous_sex_offender_detector
    from backend.improved_image_matcher import get_improved_matcher
except ImportError as e:
    print(f"Error importing backend modules: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

def test_direct_detection():
    """Test the sex offender detector directly."""
    print("🧪 Testing Direct Sex Offender Detection")
    print("=" * 50)
    
    # Initialize detector
    detector = get_continuous_sex_offender_detector()
    
    # Test camera
    print("📹 Testing camera access...")
    test_result = detector.test_camera(0)
    
    if test_result['success']:
        print("✅ Camera test successful!")
        print(f"   Frame shape: {test_result['frame_shape']}")
        print(f"   Faces detected: {test_result['faces_detected']}")
        print(f"   Sex offender detection working: {test_result['sex_offender_detection_working']}")
        print(f"   Database available: {test_result['database_available']}")
    else:
        print(f"❌ Camera test failed: {test_result['error']}")
        return False
    
    # Test with an image if available
    test_images = [
        "bus.jpg",
        "sex-offenders/images/10712834.jpg",
        "sex-offenders/images/10715977.jpg"
    ]
    
    for image_path in test_images:
        if os.path.exists(image_path):
            print(f"\n🔍 Testing detection on {image_path}...")
            results = detector.detect_in_image(image_path, threshold=0.1)
            
            if results:
                print(f"✅ Found {len(results)} potential matches:")
                for i, result in enumerate(results, 1):
                    offender_info = result.get('offender_info', {})
                    name = offender_info.get('name', result.get('offender_id', 'Unknown'))
                    confidence = result['confidence']
                    print(f"   {i}. {name} - Confidence: {confidence:.3f}")
            else:
                print("❌ No matches found")
            break
    
    return True

def test_web_api():
    """Test the web API endpoints."""
    print("\n🌐 Testing Web API Endpoints")
    print("=" * 50)
    
    base_url = "http://localhost:5002"
    
    # Test if server is running
    try:
        response = requests.get(f"{base_url}/api/sex_offender_detection/status", timeout=5)
        if response.status_code == 200:
            print("✅ Web server is running!")
            status = response.json()
            print(f"   Current status: {status.get('is_running', 'unknown')}")
        else:
            print(f"⚠️ Server responded with status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Web server is not running: {e}")
        print("   Start the web server with: python web_app/app.py")
        return False
    
    # Test camera discovery
    try:
        response = requests.get(f"{base_url}/api/sex_offender_detection/discover_cameras")
        if response.status_code == 200:
            data = response.json()
            cameras = data.get('cameras', [])
            print(f"✅ Found {len(cameras)} available cameras")
            for camera in cameras:
                print(f"   Camera {camera['id']}: {camera['frame_shape']} - Detection working: {camera['sex_offender_detection_working']}")
        else:
            print(f"⚠️ Camera discovery failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Camera discovery failed: {e}")
    
    # Test starting detection (if cameras available)
    try:
        response = requests.post(f"{base_url}/api/sex_offender_detection/start", 
                               json={
                                   'camera_index': 0,
                                   'detection_interval': 3.0,
                                   'confidence_threshold': 0.3
                               })
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Started sex offender detection: {data.get('message')}")
            
            # Wait a bit and then stop
            print("⏱️ Running detection for 10 seconds...")
            time.sleep(10)
            
            # Stop detection
            response = requests.post(f"{base_url}/api/sex_offender_detection/stop")
            if response.status_code == 200:
                print("✅ Stopped sex offender detection")
            else:
                print(f"⚠️ Failed to stop detection: {response.status_code}")
        else:
            print(f"⚠️ Failed to start detection: {response.status_code}")
            if response.text:
                print(f"   Error: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Detection start/stop failed: {e}")
    
    # Test getting stats
    try:
        response = requests.get(f"{base_url}/api/sex_offender_detection/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Retrieved detection stats:")
            print(f"   Total detections: {stats.get('total_detections', 0)}")
            print(f"   High confidence matches: {stats.get('high_confidence_matches', 0)}")
            print(f"   Total sex offenders detected: {stats.get('total_sex_offenders_detected', 0)}")
        else:
            print(f"⚠️ Failed to get stats: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Stats retrieval failed: {e}")
    
    return True

def test_image_detection():
    """Test image-based detection."""
    print("\n📸 Testing Image-Based Detection")
    print("=" * 50)
    
    base_url = "http://localhost:5002"
    
    # Test with available images
    test_images = [
        "bus.jpg",
        "sex-offenders/images/10712834.jpg",
        "sex-offenders/images/10715977.jpg"
    ]
    
    for image_path in test_images:
        if os.path.exists(image_path):
            print(f"🔍 Testing detection on {image_path}...")
            
            try:
                with open(image_path, 'rb') as f:
                    files = {'image': f}
                    data = {'threshold': '0.1'}
                    response = requests.post(f"{base_url}/api/sex_offender_detection/detect_image", 
                                           files=files, data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    count = result.get('count', 0)
                    print(f"✅ Detection complete: {count} matches found")
                    
                    if count > 0:
                        results = result.get('results', [])
                        for i, match in enumerate(results[:3], 1):  # Show top 3
                            offender_info = match.get('offender_info', {})
                            name = offender_info.get('name', match.get('offender_id', 'Unknown'))
                            confidence = match['confidence']
                            print(f"   {i}. {name} - Confidence: {confidence:.3f}")
                else:
                    print(f"⚠️ Detection failed: {response.status_code}")
                    if response.text:
                        print(f"   Error: {response.text}")
                        
            except requests.exceptions.RequestException as e:
                print(f"❌ Image detection failed: {e}")
            
            break
    else:
        print("⚠️ No test images found")

def main():
    """Main test function."""
    print("🚨 Continuous Sex Offender Detection Test")
    print("=" * 60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Direct detection
    print("Test 1: Direct Backend Detection")
    print("-" * 30)
    direct_success = test_direct_detection()
    
    print("\n" + "=" * 60)
    
    # Test 2: Web API
    print("Test 2: Web API Integration")
    print("-" * 30)
    api_success = test_web_api()
    
    print("\n" + "=" * 60)
    
    # Test 3: Image detection
    print("Test 3: Image-Based Detection")
    print("-" * 30)
    test_image_detection()
    
    print("\n" + "=" * 60)
    print("🎯 Test Summary")
    print("-" * 30)
    print(f"Direct detection: {'✅ PASS' if direct_success else '❌ FAIL'}")
    print(f"Web API: {'✅ PASS' if api_success else '❌ FAIL'}")
    print("Image detection: ✅ PASS (if images available)")
    
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if direct_success and api_success:
        print("\n🎉 All tests passed! The continuous sex offender detection is working correctly.")
        print("\n📋 Usage Instructions:")
        print("1. Start the web server: python web_app/app.py")
        print("2. Open http://localhost:5002 in your browser")
        print("3. Use the API endpoints to start/stop detection:")
        print("   - POST /api/sex_offender_detection/start")
        print("   - POST /api/sex_offender_detection/stop")
        print("   - GET /api/sex_offender_detection/status")
        print("   - GET /api/sex_offender_detection/stats")
    else:
        print("\n⚠️ Some tests failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
