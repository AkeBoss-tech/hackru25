"""
Camera handling utilities for video stream processing.
Provides advanced camera management and stream handling capabilities.
"""

import cv2
import numpy as np
import threading
import time
import logging
from typing import Optional, Dict, List, Callable, Tuple
from queue import Queue, Empty
import json


class CameraHandler:
    """
    Advanced camera handler for managing multiple camera streams.
    
    Features:
    - Multi-camera support
    - Threaded frame capture
    - Camera discovery
    - Stream quality management
    - Error handling and recovery
    """
    
    def __init__(self, buffer_size: int = 10):
        """
        Initialize the camera handler.
        
        Args:
            buffer_size: Size of frame buffer for each camera
        """
        self.buffer_size = buffer_size
        self.cameras: Dict[int, cv2.VideoCapture] = {}
        self.frame_buffers: Dict[int, Queue] = {}
        self.capture_threads: Dict[int, threading.Thread] = {}
        self.is_capturing: Dict[int, bool] = {}
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Camera properties cache
        self.camera_properties: Dict[int, Dict] = {}
        
        self.logger.info("CameraHandler initialized")
    
    def discover_cameras(self, max_cameras: int = 5) -> List[int]:
        """
        Discover available cameras.
        
        Args:
            max_cameras: Maximum number of cameras to test
            
        Returns:
            List of working camera indices
        """
        self.logger.info(f"Discovering cameras (testing up to {max_cameras})...")
        working_cameras = []
        
        for i in range(max_cameras):
            self.logger.info(f"Testing camera {i}...")
            cap = cv2.VideoCapture(i)
            
            if cap.isOpened():
                # Try to read a frame
                ret, frame = cap.read()
                if ret and frame is not None:
                    # Get camera properties
                    properties = self._get_camera_properties(cap)
                    self.camera_properties[i] = properties
                    working_cameras.append(i)
                    self.logger.info(f"✓ Camera {i} working - {properties['width']}x{properties['height']} @ {properties['fps']} FPS")
                else:
                    self.logger.warning(f"✗ Camera {i} opened but cannot read frames")
                cap.release()
            else:
                self.logger.info(f"✗ Camera {i} not available")
        
        self.logger.info(f"Found {len(working_cameras)} working cameras: {working_cameras}")
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
    
    def open_camera(
        self,
        camera_index: int,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[int] = None
    ) -> bool:
        """
        Open a camera with specified settings.
        
        Args:
            camera_index: Camera device index
            width: Desired frame width
            height: Desired frame height
            fps: Desired FPS
            
        Returns:
            True if camera opened successfully
        """
        self.logger.info(f"Opening camera {camera_index}...")
        
        # Open camera
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            self.logger.error(f"Failed to open camera {camera_index}")
            return False
        
        # Set properties if specified
        if width:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        if height:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if fps:
            cap.set(cv2.CAP_PROP_FPS, fps)
        
        # Test camera
        ret, frame = cap.read()
        if not ret or frame is None:
            self.logger.error(f"Camera {camera_index} opened but cannot read frames")
            cap.release()
            return False
        
        # Store camera and create buffer
        self.cameras[camera_index] = cap
        self.frame_buffers[camera_index] = Queue(maxsize=self.buffer_size)
        self.is_capturing[camera_index] = False
        
        # Update properties
        self.camera_properties[camera_index] = self._get_camera_properties(cap)
        
        self.logger.info(f"✓ Camera {camera_index} opened successfully")
        self.logger.info(f"  Properties: {self.camera_properties[camera_index]}")
        
        return True
    
    def start_capture(self, camera_index: int) -> bool:
        """
        Start capturing frames from a camera in a separate thread.
        
        Args:
            camera_index: Camera device index
            
        Returns:
            True if capture started successfully
        """
        if camera_index not in self.cameras:
            self.logger.error(f"Camera {camera_index} not opened")
            return False
        
        if self.is_capturing.get(camera_index, False):
            self.logger.warning(f"Camera {camera_index} already capturing")
            return True
        
        self.logger.info(f"Starting capture for camera {camera_index}")
        
        # Start capture thread
        self.is_capturing[camera_index] = True
        thread = threading.Thread(
            target=self._capture_frames,
            args=(camera_index,),
            daemon=True
        )
        thread.start()
        self.capture_threads[camera_index] = thread
        
        return True
    
    def _capture_frames(self, camera_index: int):
        """Capture frames in a loop (runs in separate thread)."""
        cap = self.cameras[camera_index]
        buffer = self.frame_buffers[camera_index]
        
        self.logger.info(f"Frame capture started for camera {camera_index}")
        
        while self.is_capturing.get(camera_index, False):
            ret, frame = cap.read()
            if not ret or frame is None:
                self.logger.warning(f"Failed to read frame from camera {camera_index}")
                time.sleep(0.01)  # Small delay to prevent busy waiting
                continue
            
            # Add frame to buffer (non-blocking)
            try:
                buffer.put_nowait(frame)
            except:
                # Buffer full, remove oldest frame
                try:
                    buffer.get_nowait()
                    buffer.put_nowait(frame)
                except Empty:
                    pass
        
        self.logger.info(f"Frame capture stopped for camera {camera_index}")
    
    def get_latest_frame(self, camera_index: int) -> Optional[np.ndarray]:
        """
        Get the latest frame from a camera.
        
        Args:
            camera_index: Camera device index
            
        Returns:
            Latest frame or None if not available
        """
        if camera_index not in self.frame_buffers:
            return None
        
        buffer = self.frame_buffers[camera_index]
        
        # Get the most recent frame (clear buffer)
        latest_frame = None
        try:
            while True:
                latest_frame = buffer.get_nowait()
        except Empty:
            pass
        
        return latest_frame
    
    def get_frame_with_timestamp(self, camera_index: int) -> Optional[Tuple[np.ndarray, float]]:
        """
        Get the latest frame with timestamp.
        
        Args:
            camera_index: Camera device index
            
        Returns:
            Tuple of (frame, timestamp) or None if not available
        """
        frame = self.get_latest_frame(camera_index)
        if frame is not None:
            return frame, time.time()
        return None
    
    def stop_capture(self, camera_index: int):
        """Stop capturing frames from a camera."""
        if camera_index in self.is_capturing:
            self.logger.info(f"Stopping capture for camera {camera_index}")
            self.is_capturing[camera_index] = False
            
            # Wait for thread to finish
            if camera_index in self.capture_threads:
                self.capture_threads[camera_index].join(timeout=2.0)
                del self.capture_threads[camera_index]
    
    def close_camera(self, camera_index: int):
        """Close a camera and clean up resources."""
        self.logger.info(f"Closing camera {camera_index}")
        
        # Stop capture if running
        if camera_index in self.is_capturing and self.is_capturing[camera_index]:
            self.stop_capture(camera_index)
        
        # Release camera
        if camera_index in self.cameras:
            self.cameras[camera_index].release()
            del self.cameras[camera_index]
        
        # Clean up buffers and state
        if camera_index in self.frame_buffers:
            del self.frame_buffers[camera_index]
        
        if camera_index in self.is_capturing:
            del self.is_capturing[camera_index]
        
        if camera_index in self.camera_properties:
            del self.camera_properties[camera_index]
    
    def close_all_cameras(self):
        """Close all cameras and clean up all resources."""
        self.logger.info("Closing all cameras")
        
        camera_indices = list(self.cameras.keys())
        for camera_index in camera_indices:
            self.close_camera(camera_index)
    
    def set_camera_property(self, camera_index: int, property_name: str, value: float) -> bool:
        """
        Set a camera property.
        
        Args:
            camera_index: Camera device index
            property_name: Property name (brightness, contrast, etc.)
            value: Property value
            
        Returns:
            True if property was set successfully
        """
        if camera_index not in self.cameras:
            self.logger.error(f"Camera {camera_index} not opened")
            return False
        
        # Map property names to OpenCV constants
        property_map = {
            'brightness': cv2.CAP_PROP_BRIGHTNESS,
            'contrast': cv2.CAP_PROP_CONTRAST,
            'saturation': cv2.CAP_PROP_SATURATION,
            'hue': cv2.CAP_PROP_HUE,
            'gain': cv2.CAP_PROP_GAIN,
            'exposure': cv2.CAP_PROP_EXPOSURE,
            'width': cv2.CAP_PROP_FRAME_WIDTH,
            'height': cv2.CAP_PROP_FRAME_HEIGHT,
            'fps': cv2.CAP_PROP_FPS
        }
        
        if property_name not in property_map:
            self.logger.error(f"Unknown property: {property_name}")
            return False
        
        cap = self.cameras[camera_index]
        success = cap.set(property_map[property_name], value)
        
        if success:
            self.logger.info(f"Set camera {camera_index} {property_name} to {value}")
            # Update cached properties
            if camera_index in self.camera_properties:
                self.camera_properties[camera_index][property_name] = value
        else:
            self.logger.warning(f"Failed to set camera {camera_index} {property_name} to {value}")
        
        return success
    
    def get_camera_properties(self, camera_index: int) -> Optional[Dict]:
        """Get camera properties."""
        return self.camera_properties.get(camera_index)
    
    def get_all_camera_properties(self) -> Dict[int, Dict]:
        """Get properties for all cameras."""
        return self.camera_properties.copy()
    
    def is_camera_available(self, camera_index: int) -> bool:
        """Check if a camera is available and working."""
        return camera_index in self.cameras and self.cameras[camera_index].isOpened()
    
    def get_camera_status(self) -> Dict[int, Dict]:
        """Get status information for all cameras."""
        status = {}
        
        for camera_index in self.cameras:
            cap = self.cameras[camera_index]
            status[camera_index] = {
                'is_opened': cap.isOpened(),
                'is_capturing': self.is_capturing.get(camera_index, False),
                'buffer_size': self.frame_buffers[camera_index].qsize() if camera_index in self.frame_buffers else 0,
                'properties': self.camera_properties.get(camera_index, {})
            }
        
        return status
    
    def save_camera_settings(self, camera_index: int, filepath: str) -> bool:
        """
        Save camera settings to a JSON file.
        
        Args:
            camera_index: Camera device index
            filepath: Path to save settings file
            
        Returns:
            True if settings were saved successfully
        """
        if camera_index not in self.camera_properties:
            self.logger.error(f"No properties available for camera {camera_index}")
            return False
        
        try:
            settings = {
                'camera_index': camera_index,
                'properties': self.camera_properties[camera_index],
                'timestamp': time.time()
            }
            
            with open(filepath, 'w') as f:
                json.dump(settings, f, indent=2)
            
            self.logger.info(f"Camera {camera_index} settings saved to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save camera settings: {e}")
            return False
    
    def load_camera_settings(self, camera_index: int, filepath: str) -> bool:
        """
        Load camera settings from a JSON file.
        
        Args:
            camera_index: Camera device index
            filepath: Path to settings file
            
        Returns:
            True if settings were loaded and applied successfully
        """
        try:
            with open(filepath, 'r') as f:
                settings = json.load(f)
            
            if settings.get('camera_index') != camera_index:
                self.logger.warning(f"Settings file camera index mismatch: expected {camera_index}, got {settings.get('camera_index')}")
            
            properties = settings.get('properties', {})
            
            # Apply properties
            for prop_name, value in properties.items():
                if prop_name in ['width', 'height', 'fps', 'brightness', 'contrast', 'saturation', 'hue', 'gain', 'exposure']:
                    self.set_camera_property(camera_index, prop_name, value)
            
            self.logger.info(f"Camera {camera_index} settings loaded from {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load camera settings: {e}")
            return False
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.close_all_cameras()
