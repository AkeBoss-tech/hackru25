#!/usr/bin/env python3
"""
Test script for the distributed camera system.
This script helps test the system components and provides examples.
"""

import time
import requests
import json
import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_server_connection(server_url="http://localhost:5002"):
    """Test if the main server is running and accessible."""
    print("🔍 Testing server connection...")
    
    try:
        response = requests.get(f"{server_url}/api/distributed/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Server is running!")
            print(f"   - Total clients: {stats.get('total_clients', 0)}")
            print(f"   - Total cameras: {stats.get('total_cameras', 0)}")
            print(f"   - Active streams: {stats.get('active_streams', 0)}")
            return True
        else:
            print(f"❌ Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server at {server_url}")
        print("   Make sure the main backend server is running:")
        print("   cd web_app && python app.py")
        return False
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False

def test_clients(server_url="http://localhost:5002"):
    """Test connected clients."""
    print("\n🔍 Testing connected clients...")
    
    try:
        response = requests.get(f"{server_url}/api/distributed/clients", timeout=5)
        if response.status_code == 200:
            data = response.json()
            clients = data.get('clients', {})
            
            if clients:
                print(f"✅ Found {len(clients)} connected clients:")
                for client_id, client_info in clients.items():
                    cameras = client_info.get('cameras', {})
                    print(f"   - {client_id}: {len(cameras)} cameras")
                    for camera_id, camera_info in cameras.items():
                        is_streaming = camera_info.get('is_streaming', False)
                        status = "🟢 Streaming" if is_streaming else "🔴 Not streaming"
                        print(f"     Camera {camera_id}: {status}")
            else:
                print("⚠️  No clients connected")
                print("   Start a camera client to see it here:")
                print("   python camera_client.py")
            
            return True
        else:
            print(f"❌ Failed to get clients: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing clients: {e}")
        return False

def test_processing_status(server_url="http://localhost:5002"):
    """Test processing status."""
    print("\n🔍 Testing processing status...")
    
    try:
        response = requests.get(f"{server_url}/api/distributed/processing", timeout=5)
        if response.status_code == 200:
            processing = response.json()
            
            if processing:
                print(f"✅ Found {len(processing)} active processing streams:")
                for stream_id, stream_info in processing.items():
                    is_active = stream_info.get('is_active', False)
                    status = "🟢 Active" if is_active else "🔴 Inactive"
                    print(f"   - {stream_id}: {status}")
            else:
                print("⚠️  No active processing streams")
            
            return True
        else:
            print(f"❌ Failed to get processing status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing processing status: {e}")
        return False

def test_web_interface(server_url="http://localhost:5002"):
    """Test web interface accessibility."""
    print("\n🔍 Testing web interface...")
    
    try:
        # Test main interface
        response = requests.get(f"{server_url}/", timeout=5)
        if response.status_code == 200:
            print("✅ Main web interface accessible")
        else:
            print(f"❌ Main interface returned: {response.status_code}")
            return False
        
        # Test distributed interface
        response = requests.get(f"{server_url}/distributed", timeout=5)
        if response.status_code == 200:
            print("✅ Distributed web interface accessible")
            print(f"   Access it at: {server_url}/distributed")
        else:
            print(f"❌ Distributed interface returned: {response.status_code}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error testing web interface: {e}")
        return False

def demo_camera_client():
    """Demo how to start a camera client."""
    print("\n📹 Camera Client Demo")
    print("===================")
    print("To start a camera client, run one of these commands:")
    print()
    print("1. Using the startup script:")
    print("   ./start_camera_client.sh")
    print()
    print("2. Manual start:")
    print("   python camera_client.py")
    print()
    print("3. With custom settings:")
    print("   python camera_client.py --server http://192.168.1.100:5002 --client-id my_camera")
    print()
    print("4. Test camera discovery only:")
    print("   python camera_client.py --discover-only")

def demo_usage():
    """Demo usage instructions."""
    print("\n📖 Usage Instructions")
    print("====================")
    print("1. Start the main backend server:")
    print("   cd web_app && python app.py")
    print()
    print("2. Start camera clients on other machines:")
    print("   python camera_client.py --server http://MAIN_SERVER_IP:5002")
    print()
    print("3. Open web interface:")
    print("   http://localhost:5002/distributed")
    print()
    print("4. From the web interface:")
    print("   - View all connected clients and cameras")
    print("   - Start/stop video streaming")
    print("   - Start/stop AI processing")
    print("   - Monitor system statistics")

def main():
    """Main test function."""
    print("🧪 Distributed Camera System Test")
    print("=================================")
    
    server_url = "http://localhost:5002"
    
    # Test server connection
    if not test_server_connection(server_url):
        print("\n❌ Server test failed. Please start the main backend server first.")
        print("Run: cd web_app && python app.py")
        return False
    
    # Test other components
    test_clients(server_url)
    test_processing_status(server_url)
    test_web_interface(server_url)
    
    # Show demos
    demo_camera_client()
    demo_usage()
    
    print("\n✅ All tests completed!")
    print("\nNext steps:")
    print("1. Start camera clients on other machines")
    print("2. Open http://localhost:5002/distributed in your browser")
    print("3. Start streaming and processing from the web interface")
    
    return True

if __name__ == "__main__":
    main()
