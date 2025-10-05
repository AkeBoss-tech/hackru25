#!/usr/bin/env python3
"""
Continuous Sex Offender Detection Service
Automatically detects and identifies sex offenders in real-time camera streams
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

from .improved_image_matcher import get_improved_matcher
from .config import Config

logger = logging.getLogger(__name__)

class ContinuousSexOffenderDetector:
    """
    Service for continuous sex offender detection from camera streams.
    
    Features:
    - Continuous camera monitoring
    - Automatic sex offender identification
    - Configurable detection intervals
    - Real-time alerts and notifications
    - Detection history and logging
    - Integration with existing web app
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the continuous sex offender detector.
        
        Args:
            config: Configuration object (uses default if None)
        """
        self.config = config or Config()
        self.image_matcher = get_improved_matcher()
        
        # Service state
        self.is_running = False
        self.is_paused = False
        self.detection_thread = None
        self.camera = None
        self.current_camera_index = 0
        
        # Detection settings
        self.detection_interval = 2.0  # seconds between detections
        self.confidence_threshold = 0.3
        self.max_detections_per_frame = 5
        self.enable_face_detection = True
        
        # Statistics
        self.stats = {
            'total_frames_processed': 0,
            'total_detections': 0,
            'high_confidence_matches': 0,
            'medium_confidence_matches': 0,
            'low_confidence_matches': 0,
            'detection_history': [],
            'session_start_time': None,
            'last_detection_time': None,
            'total_sex_offenders_detected': 0
        }
        
        # Callbacks
        self.detection_callbacks: List[Callable] = []
        self.alert_callbacks: List[Callable] = []
        self.status_callbacks: List[Callable] = []
        
        logger.info("🚨 Continuous Sex Offender Detector initialized")
    
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
        Start continuous sex offender detection.
        
        Args:
            camera_index: Camera device index to use
            
        Returns:
            True if detection started successfully
        """
        if self.is_running:
            logger.warning("Sex offender detection service is already running")
            return False
        
        logger.info(f"🚨 Starting continuous sex offender detection on camera {camera_index}")
        
        # Open camera
        self.camera = cv2.VideoCapture(camera_index)
        if not self.camera.isOpened():
            logger.error(f"Failed to open camera {camera_index}")
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
        
        logger.info("✅ Continuous sex offender detection started successfully")
        self._notify_status_change('started')
        
        return True
    
    def stop_detection(self):
        """Stop sex offender detection."""
        if not self.is_running:
            logger.warning("Sex offender detection service is not running")
            return
        
        logger.info("🛑 Stopping sex offender detection")
        
        self.is_running = False
        
        # Wait for detection thread to finish
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=5.0)
        
        # Close camera
        if self.camera:
            self.camera.release()
            self.camera = None
        
        logger.info("✅ Sex offender detection stopped")
        self._notify_status_change('stopped')
    
    def pause_detection(self):
        """Pause sex offender detection."""
        if self.is_running and not self.is_paused:
            self.is_paused = True
            logger.info("⏸️ Sex offender detection paused")
            self._notify_status_change('paused')
    
    def resume_detection(self):
        """Resume sex offender detection."""
        if self.is_running and self.is_paused:
            self.is_paused = False
            logger.info("▶️ Sex offender detection resumed")
            self._notify_status_change('resumed')
    
    def _detection_loop(self):
        """Main detection loop (runs in separate thread)."""
        last_detection_time = 0
        
        logger.info("🔍 Sex offender detection loop started")
        
        while self.is_running:
            try:
                if self.is_paused:
                    time.sleep(0.1)
                    continue
                
                current_time = time.time()
                
                # Check if it's time for detection
                if current_time - last_detection_time >= self.detection_interval:
                    # Get latest frame
                    ret, frame = self.camera.read()
                    if ret and frame is not None:
                        # Process frame for sex offender detection
                        self._process_frame_for_detection(frame)
                        last_detection_time = current_time
                        self.stats['total_frames_processed'] += 1
                
                # Small sleep to prevent busy waiting
                time.sleep(0.05)
                
            except Exception as e:
                logger.error(f"Error in sex offender detection loop: {e}")
                time.sleep(1.0)  # Wait before retrying
        
        logger.info("🔍 Sex offender detection loop ended")
    
    def _process_frame_for_detection(self, frame: np.ndarray):
        """Process a frame for sex offender detection."""
        try:
            # Save temporary frame for analysis
            temp_path = "temp_sex_offender_detection.jpg"
            cv2.imwrite(temp_path, frame)
            
            # Run sex offender detection
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
                self.stats['total_sex_offenders_detected'] += len(results)
                self.stats['last_detection_time'] = datetime.now()
                
                # Categorize by confidence and log results
                for result in results:
                    confidence = result['confidence']
                    offender_info = result.get('offender_info', {})
                    name = offender_info.get('name', result.get('offender_id', 'Unknown'))
                    
                    # Log the detection with appropriate alert level
                    if confidence > 0.7:
                        self.stats['high_confidence_matches'] += 1
                        logger.warning(f"🚨 HIGH ALERT: Sex offender detected - {name} (confidence: {confidence:.3f})")
                        print(f"🚨 HIGH ALERT: Sex offender detected - {name} (confidence: {confidence:.3f})")
                    elif confidence > 0.4:
                        self.stats['medium_confidence_matches'] += 1
                        logger.warning(f"⚠️ MEDIUM ALERT: Potential sex offender - {name} (confidence: {confidence:.3f})")
                        print(f"⚠️ MEDIUM ALERT: Potential sex offender - {name} (confidence: {confidence:.3f})")
                    else:
                        self.stats['low_confidence_matches'] += 1
                        logger.info(f"💡 LOW CONFIDENCE: Possible match - {name} (confidence: {confidence:.3f})")
                        print(f"💡 LOW CONFIDENCE: Possible match - {name} (confidence: {confidence:.3f})")
                    
                    # Print detailed offender information
                    self._print_offender_details(result)
                
                # Add to detection history
                detection_record = {
                    'timestamp': datetime.now().isoformat(),
                    'results': results,
                    'frame_count': self.stats['total_frames_processed'],
                    'detection_type': 'sex_offender'
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
                
                logger.info(f"🎯 Sex offender detection: {len(results)} matches found")
                
            else:
                # No sex offenders detected
                logger.debug("No sex offenders detected in frame")
                
        except Exception as e:
            logger.error(f"Error processing frame for sex offender detection: {e}")
    
    def _print_offender_details(self, result: Dict):
        """Print detailed information about detected sex offender."""
        offender_info = result.get('offender_info', {})
        offender_id = result.get('offender_id', 'Unknown')
        confidence = result['confidence']
        method = result.get('method', 'unknown')
        
        print("\n" + "="*60)
        print("🚨 SEX OFFENDER DETECTED")
        print("="*60)
        print(f"Name: {offender_info.get('name', offender_id)}")
        print(f"Offender ID: {offender_id}")
        print(f"Confidence: {confidence:.3f}")
        print(f"Detection Method: {method}")
        
        # Print additional offender details if available
        if 'address' in offender_info:
            print(f"Address: {offender_info['address']}")
        if 'offenses' in offender_info:
            print(f"Offenses: {offender_info['offenses']}")
        if 'risk_level' in offender_info:
            print(f"Risk Level: {offender_info['risk_level']}")
        
        # Print detection methods used
        methods_used = result.get('methods_used', [method])
        print(f"Methods Used: {', '.join(methods_used)}")
        
        # Print face region if available
        if 'face_region' in result and result['face_region']:
            x, y, w, h = result['face_region']
            print(f"Face Region: x={x}, y={y}, width={w}, height={h}")
        
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
    
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
                'severity': self._calculate_alert_severity(result['confidence']),
                'detection_type': 'sex_offender'
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
            'camera_index': self.current_camera_index,
            'service_type': 'sex_offender_detection'
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
            'camera_status': self.camera.isOpened() if self.camera else False
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
            'total_sex_offenders_detected': self.stats['total_sex_offenders_detected'],
            'high_confidence_matches': self.stats['high_confidence_matches'],
            'medium_confidence_matches': self.stats['medium_confidence_matches'],
            'low_confidence_matches': self.stats['low_confidence_matches'],
            'last_detection': self.stats['last_detection_time'].isoformat() if self.stats['last_detection_time'] else None,
            'detection_rate': self.stats['total_detections'] / max(uptime or 1, 1),
            'database_stats': self.image_matcher.get_database_stats()
        }
    
    def test_camera(self, camera_index: int = 0) -> Dict[str, Any]:
        """Test camera functionality."""
        logger.info(f"🧪 Testing camera {camera_index} for sex offender detection")
        
        try:
            # Try to open camera
            test_camera = cv2.VideoCapture(camera_index)
            if not test_camera.isOpened():
                return {'success': False, 'error': 'Failed to open camera'}
            
            # Try to read a frame
            ret, frame = test_camera.read()
            if not ret or frame is None:
                test_camera.release()
                return {'success': False, 'error': 'Failed to read frame'}
            
            # Test face detection
            faces = self.image_matcher.detect_faces(frame)
            
            # Test sex offender detection on the frame
            temp_path = f"test_frame_{camera_index}.jpg"
            cv2.imwrite(temp_path, frame)
            
            try:
                test_results = self.image_matcher.identify_person_in_image(temp_path, threshold=0.1)
                sex_offender_detection_working = True
            except Exception as e:
                sex_offender_detection_working = False
                logger.warning(f"Sex offender detection test failed: {e}")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            
            # Close camera
            test_camera.release()
            
            return {
                'success': True,
                'camera_index': camera_index,
                'frame_shape': frame.shape,
                'faces_detected': len(faces),
                'sex_offender_detection_working': sex_offender_detection_working,
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
        logger.info(f"🔍 Discovering cameras for sex offender detection (testing up to {max_cameras})")
        
        cameras = []
        
        for camera_id in range(max_cameras):
            test_result = self.test_camera(camera_id)
            if test_result['success']:
                cameras.append({
                    'id': camera_id,
                    'frame_shape': test_result['frame_shape'],
                    'faces_detected': test_result['faces_detected'],
                    'sex_offender_detection_working': test_result['sex_offender_detection_working'],
                    'database_available': test_result['database_available']
                })
        
        return cameras
    
    def detect_in_image(self, image_path: str, threshold: float = None) -> List[Dict]:
        """
        Detect sex offenders in a single image.
        
        Args:
            image_path: Path to the image file
            threshold: Confidence threshold (uses default if None)
            
        Returns:
            List of detection results
        """
        if threshold is None:
            threshold = self.confidence_threshold
        
        logger.info(f"🔍 Analyzing image for sex offenders: {image_path}")
        
        results = self.image_matcher.identify_person_in_image(image_path, threshold=threshold)
        
        if results:
            logger.info(f"Found {len(results)} potential sex offender matches")
            for result in results:
                offender_info = result.get('offender_info', {})
                name = offender_info.get('name', result.get('offender_id', 'Unknown'))
                confidence = result['confidence']
                
                logger.warning(f"Sex offender detected: {name} (confidence: {confidence:.3f})")
                print(f"🚨 Sex offender detected: {name} (confidence: {confidence:.3f})")
                self._print_offender_details(result)
        else:
            logger.info("No sex offenders detected in image")
            print("✅ No sex offenders detected in image")
        
        return results
    
    def __del__(self):
        """Cleanup when service is destroyed."""
        if self.is_running:
            self.stop_detection()


# Global service instance
_continuous_sex_offender_detector = None

def get_continuous_sex_offender_detector() -> ContinuousSexOffenderDetector:
    """Get or create the global continuous sex offender detector."""
    global _continuous_sex_offender_detector
    if _continuous_sex_offender_detector is None:
        _continuous_sex_offender_detector = ContinuousSexOffenderDetector()
    return _continuous_sex_offender_detector

def initialize_continuous_sex_offender_detector(config: Optional[Config] = None) -> ContinuousSexOffenderDetector:
    """Initialize the global continuous sex offender detector."""
    global _continuous_sex_offender_detector
    _continuous_sex_offender_detector = ContinuousSexOffenderDetector(config)
    return _continuous_sex_offender_detector

