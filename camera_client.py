#!/usr/bin/env python3
"""
Camera Client for Distributed Surveillance System
Runs on remote machines to stream camera feeds to the main backend server.
"""

import cv2
import numpy as np
import socketio
import time
import threading
import logging
import argparse
import json
import base64
from datetime import datetime
from typing import Optional, Dict, Any
import os
import signal
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CameraClient:
    """
    Camera client that streams video feeds to the main backend server.
    
    Features:
    - Connects to main backend server via SocketIO
    - Streams camera feeds in real-time
    - Handles connection management and reconnection
    - Provides camera discovery and configuration
    - Supports multiple camera streams per client
    """
    
    def __init__(self, server_url: str = "http://localhost:5002", client_id: str = None):
        """
        Initialize the camera client.
        
        Args:
            server_url: URL of the main backend server
            client_id: Unique identifier for this client
        """
        self.server_url = server_url
        self.client_id = client_id or f"camera_client_{int(time.time())}"
        self.is_connected = False
        self.is_streaming = False
        
        # Camera management
        self.cameras: Dict[int, cv2.VideoCapture] = {}
        self.camera_threads: Dict[int, threading.Thread] = {}
        self.camera_streaming: Dict[int, bool] = {}
        self.camera_properties: Dict[int, Dict] = {}
        
        # SocketIO client
        self.sio = socketio.Client()
        self._setup_socket_events()
        
        # Streaming settings
        self.streaming_quality = 80  # JPEG quality (1-100)
        self.streaming_fps = 15  # Target FPS
        self.frame_interval = 1.0 / self.streaming_fps
        
        logger.info(f"🎥 Camera Client initialized: {self.client_id}")
    
    def _setup_socket_events(self):
        """Setup SocketIO event handlers."""
        
        @self.sio.event
        def connect():
            logger.info(f"✅ Connected to main server: {self.server_url}")
            self.is_connected = True
            
            # Register this client
            self.sio.emit('client_register', {
                'client_id': self.client_id,
                'client_type': 'camera',
                'timestamp': datetime.now().isoformat()
            })
        
        @self.sio.event
        def disconnect():
            logger.warning("❌ Disconnected from main server")
            self.is_connected = False
            self.is_streaming = False
        
        @self.sio.event
        def client_registered(data):
            logger.info(f"✅ Client registered successfully: {data}")
        
        @self.sio.event
        def start_streaming(data):
            """Start streaming a specific camera."""
            camera_index = data.get('camera_index', 0)
            logger.info(f"📡 Starting stream for camera {camera_index}")
            self.start_camera_stream(camera_index)
        
        @self.sio.event
        def stop_streaming(data):
            """Stop streaming a specific camera."""
            camera_index = data.get('camera_index', 0)
            logger.info(f"⏹️ Stopping stream for camera {camera_index}")
            self.stop_camera_stream(camera_index)
        
        @self.sio.event
        def stop_all_streaming(data):
            """Stop all camera streams."""
            logger.info("⏹️ Stopping all camera streams")
            self.stop_all_streams()
        
        @self.sio.event
        def get_camera_info(data):
            """Send camera information to server."""
            self.send_camera_info()
        
        @self.sio.event
        def update_streaming_settings(data):
            """Update streaming settings."""
            if 'quality' in data:
                self.streaming_quality = max(1, min(100, data['quality']))
            if 'fps' in data:
                self.streaming_fps = max(1, min(30, data['fps']))
                self.frame_interval = 1.0 / self.streaming_fps
            
            logger.info(f"⚙️ Updated streaming settings: quality={self.streaming_quality}, fps={self.streaming_fps}")
    
    def connect_to_server(self) -> bool:
        """
        Connect to the main backend server.
        
        Returns:
            True if connection successful
        """
        try:
            logger.info(f"🔌 Connecting to server: {self.server_url}")
            self.sio.connect(self.server_url)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to server: {e}")
            return False
    
    def disconnect_from_server(self):
        """Disconnect from the main backend server."""
        try:
            self.stop_all_streams()
            self.sio.disconnect()
            logger.info("🔌 Disconnected from server")
        except Exception as e:
            logger.error(f"Error disconnecting from server: {e}")
    
    def discover_cameras(self, max_cameras: int = 5) -> list:
        """
        Discover available cameras on this machine.
        
        Args:
            max_cameras: Maximum number of cameras to test
            
        Returns:
            List of working camera indices
        """
        logger.info(f"🔍 Discovering cameras (testing up to {max_cameras})...")
        working_cameras = []
        
        for i in range(max_cameras):
            logger.info(f"Testing camera {i}...")
            cap = cv2.VideoCapture(i)
            
            if cap.isOpened():
                # Try to read a frame
                ret, frame = cap.read()
                if ret and frame is not None:
                    # Get camera properties
                    properties = self._get_camera_properties(cap)
                    self.camera_properties[i] = properties
                    working_cameras.append(i)
                    logger.info(f"✓ Camera {i} working - {properties['width']}x{properties['height']} @ {properties['fps']} FPS")
                else:
                    logger.warning(f"✗ Camera {i} opened but cannot read frames")
                cap.release()
            else:
                logger.info(f"✗ Camera {i} not available")
        
        logger.info(f"Found {len(working_cameras)} working cameras: {working_cameras}")
        return working_cameras
    
    def _get_camera_properties(self, cap: cv2.VideoCapture) -> Dict:
        """Get camera properties."""
        return {
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': int(cap.get(cv2.CAP_PROP_FPS)),
            'brightness': cap.get(cv2.CAP_PROP_BRIGHTNESS),
            'contrast': cap.get(cv2.CAP_PROP_CONTRAST),
            'saturation': cap.get(cv2.CAP_PROP_SATURATION),
            'hue': cap.get(cv2.CAP_PROP_HUE),
            'gain': cap.get(cv2.CAP_PROP_GAIN),
            'exposure': cap.get(cv2.CAP_PROP_EXPOSURE)
        }
    
    def open_camera(self, camera_index: int) -> bool:
        """
        Open a camera for streaming.
        
        Args:
            camera_index: Camera device index
            
        Returns:
            True if camera opened successfully
        """
        try:
            logger.info(f"📹 Opening camera {camera_index}")
            
            cap = cv2.VideoCapture(camera_index)
            if not cap.isOpened():
                logger.error(f"Failed to open camera {camera_index}")
                return False
            
            # Test camera
            ret, frame = cap.read()
            if not ret or frame is None:
                logger.error(f"Camera {camera_index} opened but cannot read frames")
                cap.release()
                return False
            
            self.cameras[camera_index] = cap
            self.camera_streaming[camera_index] = False
            
            # Update properties
            self.camera_properties[camera_index] = self._get_camera_properties(cap)
            
            logger.info(f"✓ Camera {camera_index} opened successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error opening camera {camera_index}: {e}")
            return False
    
    def start_camera_stream(self, camera_index: int) -> bool:
        """
        Start streaming from a camera.
        
        Args:
            camera_index: Camera device index
            
        Returns:
            True if streaming started successfully
        """
        if camera_index not in self.cameras:
            if not self.open_camera(camera_index):
                return False
        
        if self.camera_streaming.get(camera_index, False):
            logger.warning(f"Camera {camera_index} is already streaming")
            return True
        
        if not self.is_connected:
            logger.error("Not connected to server")
            return False
        
        logger.info(f"📡 Starting stream for camera {camera_index}")
        
        self.camera_streaming[camera_index] = True
        self.is_streaming = True
        
        # Start streaming thread
        thread = threading.Thread(
            target=self._stream_camera_frames,
            args=(camera_index,),
            daemon=True
        )
        thread.start()
        self.camera_threads[camera_index] = thread
        
        return True
    
    def stop_camera_stream(self, camera_index: int):
        """Stop streaming from a camera."""
        if camera_index in self.camera_streaming:
            logger.info(f"⏹️ Stopping stream for camera {camera_index}")
            self.camera_streaming[camera_index] = False
            
            # Wait for thread to finish
            if camera_index in self.camera_threads:
                self.camera_threads[camera_index].join(timeout=2.0)
                del self.camera_threads[camera_index]
        
        # Check if any cameras are still streaming
        self.is_streaming = any(self.camera_streaming.values())
    
    def stop_all_streams(self):
        """Stop all camera streams."""
        logger.info("⏹️ Stopping all camera streams")
        
        camera_indices = list(self.camera_streaming.keys())
        for camera_index in camera_indices:
            self.stop_camera_stream(camera_index)
    
    def _stream_camera_frames(self, camera_index: int):
        """Stream frames from a camera (runs in separate thread)."""
        cap = self.cameras[camera_index]
        last_frame_time = 0
        
        logger.info(f"📡 Streaming started for camera {camera_index}")
        
        while self.camera_streaming.get(camera_index, False) and self.is_connected:
            try:
                current_time = time.time()
                
                # Control frame rate
                if current_time - last_frame_time < self.frame_interval:
                    time.sleep(0.01)
                    continue
                
                # Read frame
                ret, frame = cap.read()
                if not ret or frame is None:
                    logger.warning(f"Failed to read frame from camera {camera_index}")
                    time.sleep(0.1)
                    continue
                
                # Encode frame as JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.streaming_quality]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                # Send frame to server
                frame_data = {
                    'client_id': self.client_id,
                    'camera_index': camera_index,
                    'frame_data': frame_base64,
                    'timestamp': datetime.now().isoformat(),
                    'frame_shape': frame.shape,
                    'quality': self.streaming_quality
                }
                
                self.sio.emit('camera_frame', frame_data)
                last_frame_time = current_time
                
            except Exception as e:
                logger.error(f"Error streaming camera {camera_index}: {e}")
                time.sleep(0.1)
        
        logger.info(f"📡 Streaming stopped for camera {camera_index}")
    
    def send_camera_info(self):
        """Send camera information to the server."""
        if not self.is_connected:
            return
        
        camera_info = {
            'client_id': self.client_id,
            'cameras': {},
            'timestamp': datetime.now().isoformat()
        }
        
        for camera_index, properties in self.camera_properties.items():
            camera_info['cameras'][camera_index] = {
                'properties': properties,
                'is_streaming': self.camera_streaming.get(camera_index, False)
            }
        
        self.sio.emit('camera_info', camera_info)
        logger.info(f"📋 Sent camera info: {len(camera_info['cameras'])} cameras")
    
    def close_camera(self, camera_index: int):
        """Close a camera and clean up resources."""
        logger.info(f"📹 Closing camera {camera_index}")
        
        # Stop streaming if running
        if camera_index in self.camera_streaming and self.camera_streaming[camera_index]:
            self.stop_camera_stream(camera_index)
        
        # Release camera
        if camera_index in self.cameras:
            self.cameras[camera_index].release()
            del self.cameras[camera_index]
        
        # Clean up state
        if camera_index in self.camera_streaming:
            del self.camera_streaming[camera_index]
        
        if camera_index in self.camera_properties:
            del self.camera_properties[camera_index]
    
    def close_all_cameras(self):
        """Close all cameras and clean up all resources."""
        logger.info("📹 Closing all cameras")
        
        camera_indices = list(self.cameras.keys())
        for camera_index in camera_indices:
            self.close_camera(camera_index)
    
    def get_status(self) -> Dict[str, Any]:
        """Get client status information."""
        return {
            'client_id': self.client_id,
            'is_connected': self.is_connected,
            'is_streaming': self.is_streaming,
            'cameras': {
                str(k): {
                    'is_open': k in self.cameras,
                    'is_streaming': self.camera_streaming.get(k, False),
                    'properties': self.camera_properties.get(k, {})
                }
                for k in set(list(self.cameras.keys()) + list(self.camera_streaming.keys()))
            },
            'streaming_settings': {
                'quality': self.streaming_quality,
                'fps': self.streaming_fps
            }
        }
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.close_all_cameras()
        if self.is_connected:
            self.disconnect_from_server()


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("🛑 Received shutdown signal")
    sys.exit(0)


def main():
    """Main function for camera client."""
    parser = argparse.ArgumentParser(description='Camera Client for Distributed Surveillance System')
    parser.add_argument('--server', default='http://localhost:5002', help='Main backend server URL')
    parser.add_argument('--client-id', help='Unique client identifier')
    parser.add_argument('--max-cameras', type=int, default=5, help='Maximum cameras to discover')
    parser.add_argument('--quality', type=int, default=80, help='Streaming quality (1-100)')
    parser.add_argument('--fps', type=int, default=15, help='Target streaming FPS')
    parser.add_argument('--discover-only', action='store_true', help='Only discover cameras and exit')
    
    args = parser.parse_args()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create camera client
    client = CameraClient(server_url=args.server, client_id=args.client_id)
    
    # Set streaming settings
    client.streaming_quality = args.quality
    client.streaming_fps = args.fps
    client.frame_interval = 1.0 / args.fps
    
    # Discover cameras
    logger.info("🔍 Discovering cameras...")
    cameras = client.discover_cameras(args.max_cameras)
    
    if args.discover_only:
        logger.info(f"📋 Found cameras: {cameras}")
        for camera_index in cameras:
            props = client.camera_properties.get(camera_index, {})
            logger.info(f"  Camera {camera_index}: {props.get('width', 0)}x{props.get('height', 0)} @ {props.get('fps', 0)} FPS")
        return
    
    if not cameras:
        logger.error("❌ No cameras found!")
        return
    
    # Connect to server
    if not client.connect_to_server():
        logger.error("❌ Failed to connect to server")
        return
    
    try:
        logger.info("🎥 Camera client running... Press Ctrl+C to stop")
        
        # Keep the client running
        while True:
            if not client.is_connected:
                logger.warning("⚠️ Lost connection to server, attempting to reconnect...")
                if client.connect_to_server():
                    logger.info("✅ Reconnected to server")
                    # Send camera info after reconnection
                    client.send_camera_info()
                else:
                    logger.error("❌ Failed to reconnect, retrying in 5 seconds...")
                    time.sleep(5)
            else:
                time.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down camera client...")
    finally:
        client.close_all_cameras()
        client.disconnect_from_server()
        logger.info("👋 Camera client stopped")


if __name__ == '__main__':
    main()
