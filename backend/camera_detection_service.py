#!/usr/bin/env python3
"""
Camera Detection Service for Backend
Integrates continuous camera detection with offender identification
"""

import cv2
import numpy as np
import time
import threading
import logging
from typing import Optional, Dict, List, Callable, Any
from datetime import datetime
import json
import os
from pathlib import Path

from .camera_handler import CameraHandler
from .improved_image_matcher import get_improved_matcher
from .config import Config

logger = logging.getLogger(__name__)

class CameraDetectionService:
    """
    Service for continuous camera-based offender detection.
    
    Features:
    - Continuous camera monitoring
    - Automatic face detection and matching
    - Configurable detection intervals
    - Real-time alerts and notifications
    - Detection history and logging
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the camera detection service.
        
        Args:
            config: Configuration object (uses default if None)
        """
        self.config = config or Config()
        self.camera_handler = CameraHandler()
        self.image_matcher = get_improved_matcher()
        
        # Service state
        self.is_running = False
        self.is_paused = False
        self.detection_thread = None
        self.current_camera_index = 0
        
        # Detection settings
        self.detection_interval = 2.0  # seconds between detections
        self.confidence_threshold = 0.3
        self.max_detections_per_frame = 5
        
        # Statistics
        self.stats = {
            'total_frames_processed': 0,
            'total_detections': 0,
            'high_confidence_matches': 0,
            'medium_confidence_matches': 0,
            'low_confidence_matches': 0,
            'detection_history': [],
            'session_start_time': None,
            'last_detection_time': None
        }
        
        # Callbacks
        self.detection_callbacks: List[Callable] = []
        self.alert_callbacks: List[Callable] = []
        self.status_callbacks: List[Callable] = []
        
        logger.info("🎥 Camera Detection Service initialized")
    
    def set_detection_interval(self, interval: float):
        """Set the detection interval in seconds."""
        if interval > 0:
            self.detection_interval = interval
            logger.info(f"Detection interval set to {interval} seconds")
        else:
            logger.warning("Detection interval must be positive")
    
    def set_confidence_threshold(self, threshold: float):
        """Set the confidence threshold for matches."""
        if 0.0 <= threshold <= 1.0:
            self.confidence_threshold = threshold
            logger.info(f"Confidence threshold set to {threshold}")
        else:
            logger.warning("Confidence threshold must be between 0.0 and 1.0")
    
    def add_detection_callback(self, callback: Callable[[List[Dict]], None]):
        """Add a callback for detection events."""
        self.detection_callbacks.append(callback)
    
    def add_alert_callback(self, callback: Callable[[Dict], None]):
        """Add a callback for high-confidence alerts."""
        self.alert_callbacks.append(callback)
    
    def add_status_callback(self, callback: Callable[[Dict], None]):
        """Add a callback for status updates."""
        self.status_callbacks.append(callback)
    
    def start_detection(self, camera_index: int = 0) -> bool:
        """
        Start continuous camera detection.
        
        Args:
            camera_index: Camera device index to use
            
        Returns:
            True if detection started successfully
        """
        if self.is_running:
            logger.warning("Detection service is already running")
            return False
        
        logger.info(f"🚀 Starting camera detection on camera {camera_index}")
        
        # Open camera
        if not self.camera_handler.open_camera(camera_index):
            logger.error(f"Failed to open camera {camera_index}")
            return False
        
        # Start camera capture
        if not self.camera_handler.start_capture(camera_index):
            logger.error(f"Failed to start capture on camera {camera_index}")
            self.camera_handler.close_camera(camera_index)
            return False
        
        # Start detection thread
        self.current_camera_index = camera_index
        self.is_running = True
        self.is_paused = False
        self.stats['session_start_time'] = datetime.now()
        
        self.detection_thread = threading.Thread(
            target=self._detection_loop,
            daemon=True
        )
        self.detection_thread.start()
        
        logger.info("✅ Camera detection started successfully")
        self._notify_status_change('started')
        
        return True
    
    def stop_detection(self):
        """Stop camera detection."""
        if not self.is_running:
            logger.warning("Detection service is not running")
            return
        
        logger.info("🛑 Stopping camera detection")
        
        self.is_running = False
        
        # Wait for detection thread to finish
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=5.0)
        
        # Close camera
        self.camera_handler.close_camera(self.current_camera_index)
        
        logger.info("✅ Camera detection stopped")
        self._notify_status_change('stopped')
    
    def pause_detection(self):
        """Pause camera detection."""
        if self.is_running and not self.is_paused:
            self.is_paused = True
            logger.info("⏸️ Camera detection paused")
            self._notify_status_change('paused')
    
    def resume_detection(self):
        """Resume camera detection."""
        if self.is_running and self.is_paused:
            self.is_paused = False
            logger.info("▶️ Camera detection resumed")
            self._notify_status_change('resumed')
    
    def _detection_loop(self):
        """Main detection loop (runs in separate thread)."""
        last_detection_time = 0
        
        logger.info("🔍 Detection loop started")
        
        while self.is_running:
            try:
                if self.is_paused:
                    time.sleep(0.1)
                    continue
                
                current_time = time.time()
                
                # Check if it's time for detection
                if current_time - last_detection_time >= self.detection_interval:
                    # Get latest frame
                    frame = self.camera_handler.get_latest_frame(self.current_camera_index)
                    
                    if frame is not None:
                        # Process frame for detection
                        self._process_frame_for_detection(frame)
                        last_detection_time = current_time
                        self.stats['total_frames_processed'] += 1
                
                # Small sleep to prevent busy waiting
                time.sleep(0.05)
                
            except Exception as e:
                logger.error(f"Error in detection loop: {e}")
                time.sleep(1.0)  # Wait before retrying
        
        logger.info("🔍 Detection loop ended")
    
    def _process_frame_for_detection(self, frame: np.ndarray):
        """Process a frame for offender detection."""
        try:
            # Save temporary frame for analysis
            temp_path = "temp_detection_frame.jpg"
            cv2.imwrite(temp_path, frame)
            
            # Run detection
            results = self.image_matcher.identify_person_in_image(
                temp_path, 
                threshold=self.confidence_threshold
            )
            
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            if results:
                # Limit results
                results = results[:self.max_detections_per_frame]
                
                # Update statistics
                self.stats['total_detections'] += len(results)
                self.stats['last_detection_time'] = datetime.now()
                
                # Categorize by confidence
                for result in results:
                    confidence = result['confidence']
                    if confidence > 0.7:
                        self.stats['high_confidence_matches'] += 1
                    elif confidence > 0.4:
                        self.stats['medium_confidence_matches'] += 1
                    else:
                        self.stats['low_confidence_matches'] += 1
                
                # Add to detection history
                detection_record = {
                    'timestamp': datetime.now().isoformat(),
                    'results': results,
                    'frame_count': self.stats['total_frames_processed']
                }
                self.stats['detection_history'].append(detection_record)
                
                # Keep only recent history (last 100 detections)
                if len(self.stats['detection_history']) > 100:
                    self.stats['detection_history'] = self.stats['detection_history'][-100:]
                
                # Notify callbacks
                self._notify_detection(results)
                
                # Check for high-confidence alerts
                high_conf_results = [r for r in results if r['confidence'] > 0.7]
                if high_conf_results:
                    self._notify_alerts(high_conf_results)
                
                logger.info(f"🎯 Detection: {len(results)} matches found")
                
        except Exception as e:
            logger.error(f"Error processing frame for detection: {e}")
    
    def _notify_detection(self, results: List[Dict]):
        """Notify detection callbacks."""
        for callback in self.detection_callbacks:
            try:
                callback(results)
            except Exception as e:
                logger.error(f"Error in detection callback: {e}")
    
    def _notify_alerts(self, results: List[Dict]):
        """Notify alert callbacks for high-confidence matches."""
        for result in results:
            alert_data = {
                'timestamp': datetime.now().isoformat(),
                'confidence': result['confidence'],
                'offender_info': result.get('offender_info', {}),
                'method': result.get('method', 'unknown'),
                'face_region': result.get('face_region'),
                'severity': self._calculate_alert_severity(result['confidence'])
            }
            
            for callback in self.alert_callbacks:
                try:
                    callback(alert_data)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
    
    def _notify_status_change(self, status: str):
        """Notify status callbacks."""
        status_data = {
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'camera_index': self.current_camera_index
        }
        
        for callback in self.status_callbacks:
            try:
                callback(status_data)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
    
    def _calculate_alert_severity(self, confidence: float) -> str:
        """Calculate alert severity based on confidence."""
        if confidence > 0.8:
            return 'CRITICAL'
        elif confidence > 0.7:
            return 'HIGH'
        elif confidence > 0.5:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status."""
        uptime = None
        if self.stats['session_start_time']:
            uptime = (datetime.now() - self.stats['session_start_time']).total_seconds()
        
        return {
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'camera_index': self.current_camera_index,
            'detection_interval': self.detection_interval,
            'confidence_threshold': self.confidence_threshold,
            'uptime_seconds': uptime,
            'stats': self.stats.copy(),
            'camera_status': self.camera_handler.get_camera_status().get(self.current_camera_index, {})
        }
    
    def get_recent_detections(self, limit: int = 10) -> List[Dict]:
        """Get recent detection results."""
        return self.stats['detection_history'][-limit:]
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get detection statistics."""
        uptime = None
        if self.stats['session_start_time']:
            uptime = (datetime.now() - self.stats['session_start_time']).total_seconds()
        
        return {
            'session_start': self.stats['session_start_time'].isoformat() if self.stats['session_start_time'] else None,
            'uptime_seconds': uptime,
            'total_frames_processed': self.stats['total_frames_processed'],
            'total_detections': self.stats['total_detections'],
            'high_confidence_matches': self.stats['high_confidence_matches'],
            'medium_confidence_matches': self.stats['medium_confidence_matches'],
            'low_confidence_matches': self.stats['low_confidence_matches'],
            'last_detection': self.stats['last_detection_time'].isoformat() if self.stats['last_detection_time'] else None,
            'detection_rate': self.stats['total_detections'] / max(uptime or 1, 1),
            'database_stats': self.image_matcher.get_database_stats()
        }
    
    def test_camera(self, camera_index: int = 0) -> Dict[str, Any]:
        """Test camera functionality."""
        logger.info(f"🧪 Testing camera {camera_index}")
        
        try:
            # Try to open camera
            if not self.camera_handler.open_camera(camera_index):
                return {'success': False, 'error': 'Failed to open camera'}
            
            # Try to read a frame
            frame = self.camera_handler.get_latest_frame(camera_index)
            if frame is None:
                self.camera_handler.close_camera(camera_index)
                return {'success': False, 'error': 'Failed to read frame'}
            
            # Get camera properties
            properties = self.camera_handler.get_camera_properties(camera_index)
            
            # Test face detection
            faces = self.image_matcher.detect_faces(frame)
            
            # Close camera
            self.camera_handler.close_camera(camera_index)
            
            return {
                'success': True,
                'camera_index': camera_index,
                'properties': properties,
                'faces_detected': len(faces),
                'frame_shape': frame.shape,
                'database_available': {
                    'opencv': self.image_matcher.opencv_db is not None,
                    'vector': self.image_matcher.face_db is not None
                }
            }
            
        except Exception as e:
            logger.error(f"Camera test error: {e}")
            return {'success': False, 'error': str(e)}
    
    def discover_cameras(self, max_cameras: int = 5) -> List[Dict]:
        """Discover available cameras."""
        logger.info(f"🔍 Discovering cameras (testing up to {max_cameras})")
        
        cameras = self.camera_handler.discover_cameras(max_cameras)
        camera_info = []
        
        for camera_id in cameras:
            test_result = self.test_camera(camera_id)
            if test_result['success']:
                camera_info.append({
                    'id': camera_id,
                    'properties': test_result['properties'],
                    'faces_detected': test_result['faces_detected'],
                    'frame_shape': test_result['frame_shape']
                })
        
        return camera_info
    
    def __del__(self):
        """Cleanup when service is destroyed."""
        if self.is_running:
            self.stop_detection()


# Global service instance
_camera_detection_service = None

def get_camera_detection_service() -> CameraDetectionService:
    """Get or create the global camera detection service."""
    global _camera_detection_service
    if _camera_detection_service is None:
        _camera_detection_service = CameraDetectionService()
    return _camera_detection_service

def initialize_camera_detection_service(config: Optional[Config] = None) -> CameraDetectionService:
    """Initialize the global camera detection service."""
    global _camera_detection_service
    _camera_detection_service = CameraDetectionService(config)
    return _camera_detection_service

