"""
Distributed Camera Manager for Backend
Handles multiple camera clients and their video streams for centralized processing.
"""

import cv2
import numpy as np
import time
import threading
import logging
import base64
import os
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import json
import io
from queue import Queue, Empty

from .video_processor import VideoProcessor
from .config import Config
from .improved_image_matcher import get_improved_matcher

logger = logging.getLogger(__name__)

class CameraClient:
    """Represents a connected camera client."""
    
    def __init__(self, client_id: str, client_type: str = "camera"):
        self.client_id = client_id
        self.client_type = client_type
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self.cameras: Dict[int, Dict] = {}  # camera_index -> camera_info
        self.streaming_cameras: Dict[int, bool] = {}  # camera_index -> is_streaming
        self.frame_buffers: Dict[int, Queue] = {}  # camera_index -> frame_buffer
        self.is_active = True
    
    def add_camera(self, camera_index: int, camera_info: Dict):
        """Add camera information."""
        self.cameras[camera_index] = camera_info
        self.streaming_cameras[camera_index] = False
        self.frame_buffers[camera_index] = Queue(maxsize=10)
    
    def remove_camera(self, camera_index: int):
        """Remove camera."""
        self.cameras.pop(camera_index, None)
        self.streaming_cameras.pop(camera_index, None)
        self.frame_buffers.pop(camera_index, None)
    
    def start_streaming(self, camera_index: int):
        """Start streaming a camera."""
        self.streaming_cameras[camera_index] = True
    
    def stop_streaming(self, camera_index: int):
        """Stop streaming a camera."""
        self.streaming_cameras[camera_index] = False
    
    def add_frame(self, camera_index: int, frame: np.ndarray):
        """Add frame to buffer."""
        if camera_index in self.frame_buffers:
            buffer = self.frame_buffers[camera_index]
            try:
                buffer.put_nowait(frame)
            except:
                # Buffer full, remove oldest frame
                try:
                    buffer.get_nowait()
                    buffer.put_nowait(frame)
                except Empty:
                    pass
    
    def get_latest_frame(self, camera_index: int) -> Optional[np.ndarray]:
        """Get latest frame from buffer."""
        if camera_index not in self.frame_buffers:
            return None
        
        buffer = self.frame_buffers[camera_index]
        latest_frame = None
        
        try:
            while True:
                latest_frame = buffer.get_nowait()
        except Empty:
            pass
        
        return latest_frame
    
    def get_status(self) -> Dict[str, Any]:
        """Get client status."""
        return {
            'client_id': self.client_id,
            'client_type': self.client_type,
            'connected_at': self.connected_at.isoformat(),
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'is_active': self.is_active,
            'cameras': {
                str(k): {
                    'info': v,
                    'is_streaming': self.streaming_cameras.get(k, False)
                }
                for k, v in self.cameras.items()
            }
        }


class DistributedCameraManager:
    """
    Manages multiple camera clients and their video streams.
    
    Features:
    - Client registration and management
    - Frame buffer management
    - Multi-camera processing coordination
    - Real-time video stream handling
    - Client health monitoring
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the distributed camera manager.
        
        Args:
            config: Configuration object (uses default if None)
        """
        self.config = config or Config()
        
        # Client management
        self.clients: Dict[str, CameraClient] = {}
        self.client_lock = threading.Lock()
        
        # Face detection and sex offender matching
        self.image_matcher = get_improved_matcher()
        self.family_members = self._load_family_members()
        
        # Processing management
        self.processors: Dict[str, VideoProcessor] = {}  # stream_id -> processor
        self.processing_threads: Dict[str, threading.Thread] = {}
        self.processing_active: Dict[str, bool] = {}
        
        # Callbacks
        self.frame_callbacks: List[Callable] = []
        self.detection_callbacks: List[Callable] = []
        self.client_callbacks: List[Callable] = []
        
        # Statistics
        self.stats = {
            'total_clients': 0,
            'active_clients': 0,
            'total_cameras': 0,
            'active_streams': 0,
            'frames_processed': 0,
            'detections_total': 0,
            'start_time': datetime.now()
        }
        
        logger.info("🌐 Distributed Camera Manager initialized")
    
    def _load_family_members(self) -> Dict[str, Dict]:
        """Load family members from storage."""
        try:
            family_file = "family_members.json"
            if os.path.exists(family_file):
                with open(family_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading family members: {e}")
            return {}
    
    def _save_family_members(self):
        """Save family members to storage."""
        try:
            family_file = "family_members.json"
            with open(family_file, 'w') as f:
                json.dump(self.family_members, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving family members: {e}")
    
    def add_family_member(self, name: str, image_path: str) -> bool:
        """Add a family member."""
        try:
            # Process the image and store it
            if os.path.exists(image_path):
                self.family_members[name] = {
                    'name': name,
                    'image_path': image_path,
                    'added_at': datetime.now().isoformat()
                }
                self._save_family_members()
                logger.info(f"Added family member: {name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding family member {name}: {e}")
            return False
    
    def remove_family_member(self, name: str) -> bool:
        """Remove a family member."""
        try:
            if name in self.family_members:
                del self.family_members[name]
                self._save_family_members()
                logger.info(f"Removed family member: {name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing family member {name}: {e}")
            return False
    
    def get_family_members(self) -> Dict[str, Dict]:
        """Get all family members."""
        return self.family_members.copy()
    
    def check_family_member(self, frame: np.ndarray) -> Optional[Dict]:
        """Check if face in frame matches a family member."""
        try:
            # Detect faces in the frame
            faces = self.image_matcher.detect_faces(frame)
            
            for face in faces:
                # Crop face from frame
                x, y, w, h = face
                face_crop = frame[y:y+h, x:x+w]
                
                # For now, we'll do a simple comparison
                # In a real system, you'd use face recognition
                # For demo purposes, we'll return a placeholder
                return {
                    'face_region': face,
                    'confidence': 0.8,  # Placeholder
                    'is_family': True,
                    'family_member': 'Unknown Family Member'
                }
            
            return None
        except Exception as e:
            logger.error(f"Error checking family member: {e}")
            return None
    
    def register_client(self, client_id: str, client_type: str = "camera") -> CameraClient:
        """
        Register a new camera client.
        
        Args:
            client_id: Unique client identifier
            client_type: Type of client (camera, etc.)
            
        Returns:
            CameraClient object
        """
        with self.client_lock:
            if client_id in self.clients:
                logger.warning(f"Client {client_id} already registered, updating...")
                client = self.clients[client_id]
                client.last_heartbeat = datetime.now()
                client.is_active = True
            else:
                client = CameraClient(client_id, client_type)
                self.clients[client_id] = client
                logger.info(f"✅ Registered new client: {client_id}")
            
            self._update_stats()
            self._notify_client_change('registered', client)
            
            return client
    
    def unregister_client(self, client_id: str):
        """Unregister a camera client."""
        with self.client_lock:
            if client_id in self.clients:
                client = self.clients[client_id]
                
                # Stop all processing for this client
                self._stop_all_client_processing(client_id)
                
                # Remove client
                del self.clients[client_id]
                logger.info(f"❌ Unregistered client: {client_id}")
                
                self._update_stats()
                self._notify_client_change('unregistered', client)
    
    def update_client_heartbeat(self, client_id: str):
        """Update client heartbeat."""
        with self.client_lock:
            if client_id in self.clients:
                self.clients[client_id].last_heartbeat = datetime.now()
                self.clients[client_id].is_active = True
    
    def add_camera_info(self, client_id: str, camera_info: Dict):
        """Add camera information for a client."""
        with self.client_lock:
            if client_id in self.clients:
                client = self.clients[client_id]
                
                for camera_index, info in camera_info.get('cameras', {}).items():
                    camera_index = int(camera_index)
                    client.add_camera(camera_index, info)
                    logger.info(f"📹 Added camera {camera_index} to client {client_id}")
                
                self._update_stats()
    
    def handle_camera_frame(self, client_id: str, camera_index: int, frame_data: str) -> bool:
        """
        Handle incoming camera frame from a client.
        
        Args:
            client_id: Client identifier
            camera_index: Camera index
            frame_data: Base64 encoded frame data
            
        Returns:
            True if frame was processed successfully
        """
        try:
            # Decode frame
            frame_bytes = base64.b64decode(frame_data)
            frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
            
            if frame is None:
                logger.warning(f"Failed to decode frame from client {client_id}, camera {camera_index}")
                return False
            
            with self.client_lock:
                if client_id in self.clients:
                    client = self.clients[client_id]
                    client.add_frame(camera_index, frame)
                    client.last_heartbeat = datetime.now()
                    
                    # Update stats
                    self.stats['frames_processed'] += 1
                    
                    # Perform face detection and analysis
                    self._analyze_frame_for_faces(client_id, camera_index, frame)
                    
                    # Notify frame callbacks
                    self._notify_frame_received(client_id, camera_index, frame)
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling frame from client {client_id}, camera {camera_index}: {e}")
            return False
    
    def _analyze_frame_for_faces(self, client_id: str, camera_index: int, frame: np.ndarray):
        """Analyze frame for faces and run sex offender detection."""
        try:
            # Check for family members first
            family_result = self.check_family_member(frame)
            if family_result:
                self._notify_family_detection(client_id, camera_index, family_result, frame)
                return
            
            # Detect faces
            faces = self.image_matcher.detect_faces(frame)
            
            if faces:
                # Save temporary frame for sex offender detection
                temp_path = f"temp_frame_{client_id}_{camera_index}.jpg"
                cv2.imwrite(temp_path, frame)
                
                try:
                    # Run sex offender detection
                    sex_offender_results = self.image_matcher.identify_person_in_image(
                        temp_path, 
                        threshold=0.3
                    )
                    
                    if sex_offender_results:
                        # Found potential sex offender
                        for result in sex_offender_results:
                            self._notify_sex_offender_detection(
                                client_id, camera_index, result, frame
                            )
                    else:
                        # Face detected but not a sex offender
                        self._notify_face_detection(
                            client_id, camera_index, faces, "Not Sex Offender"
                        )
                        
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            else:
                # No faces detected
                self._notify_face_detection(
                    client_id, camera_index, [], "No Faces Detected"
                )
                
        except Exception as e:
            logger.error(f"Error analyzing frame for faces: {e}")
    
    def _notify_family_detection(self, client_id: str, camera_index: int, result: Dict, frame: np.ndarray):
        """Notify about family member detection."""
        try:
            # Create labeled frame with family member name
            labeled_frame = self.image_matcher.draw_face_labels(frame, [result])
            
            detection_data = {
                'client_id': client_id,
                'camera_index': camera_index,
                'detection_type': 'family_member',
                'result': result,
                'labeled_frame': labeled_frame,  # Include labeled frame
                'timestamp': datetime.now().isoformat(),
                'severity': 'info'
            }
            
            for callback in self.detection_callbacks:
                try:
                    callback(detection_data)
                except Exception as e:
                    logger.error(f"Error in family detection callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error notifying family detection: {e}")
    
    def _notify_sex_offender_detection(self, client_id: str, camera_index: int, result: Dict, frame: np.ndarray):
        """Notify about sex offender detection."""
        try:
            # Create labeled frame with name
            labeled_frame = self.image_matcher.draw_face_labels(frame, [result])
            
            detection_data = {
                'client_id': client_id,
                'camera_index': camera_index,
                'detection_type': 'sex_offender',
                'result': result,
                'labeled_frame': labeled_frame,  # Include labeled frame
                'timestamp': datetime.now().isoformat(),
                'severity': 'critical' if result.get('confidence', 0) > 0.7 else 'warning'
            }
            
            for callback in self.detection_callbacks:
                try:
                    callback(detection_data)
                except Exception as e:
                    logger.error(f"Error in sex offender detection callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error notifying sex offender detection: {e}")
    
    def _notify_face_detection(self, client_id: str, camera_index: int, faces: List, status: str):
        """Notify about general face detection."""
        try:
            detection_data = {
                'client_id': client_id,
                'camera_index': camera_index,
                'detection_type': 'face_detection',
                'faces': faces,
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'severity': 'info'
            }
            
            for callback in self.detection_callbacks:
                try:
                    callback(detection_data)
                except Exception as e:
                    logger.error(f"Error in face detection callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error notifying face detection: {e}")
    
    def start_processing_stream(self, stream_id: str, client_id: str, camera_index: int, 
                              confidence: float = 0.25, enable_tracking: bool = True,
                              target_classes: Optional[List[str]] = None) -> bool:
        """
        Start processing a camera stream.
        
        Args:
            stream_id: Unique identifier for this processing stream
            client_id: Client identifier
            camera_index: Camera index
            confidence: Detection confidence threshold
            enable_tracking: Enable object tracking
            target_classes: Target classes for detection
            
        Returns:
            True if processing started successfully
        """
        try:
            with self.client_lock:
                if client_id not in self.clients:
                    logger.error(f"Client {client_id} not found")
                    return False
                
                client = self.clients[client_id]
                if camera_index not in client.cameras:
                    logger.error(f"Camera {camera_index} not found for client {client_id}")
                    return False
                
                # Stop existing processing if any
                if stream_id in self.processing_active:
                    self.stop_processing_stream(stream_id)
                
                # Create video processor
                processor = VideoProcessor(
                    model_path=self.config.get_model_path(),
                    confidence_threshold=confidence,
                    enable_tracking=enable_tracking,
                    target_classes=target_classes
                )
                
                # Set up callbacks
                processor.set_detection_callback(
                    lambda detections, frame, frame_number: self._on_detection(
                        stream_id, detections, frame, frame_number
                    )
                )
                processor.set_frame_callback(
                    lambda processed_frame, frame_number, raw_frame: self._on_frame(
                        stream_id, processed_frame, frame_number, raw_frame
                    )
                )
                
                self.processors[stream_id] = processor
                self.processing_active[stream_id] = True
                
                # Start processing thread
                thread = threading.Thread(
                    target=self._process_stream_loop,
                    args=(stream_id, client_id, camera_index),
                    daemon=True
                )
                thread.start()
                self.processing_threads[stream_id] = thread
                
                logger.info(f"🚀 Started processing stream {stream_id} (client: {client_id}, camera: {camera_index})")
                self._update_stats()
                
                return True
                
        except Exception as e:
            logger.error(f"Error starting processing stream {stream_id}: {e}")
            return False
    
    def stop_processing_stream(self, stream_id: str):
        """Stop processing a camera stream."""
        try:
            if stream_id in self.processing_active:
                self.processing_active[stream_id] = False
                
                # Wait for thread to finish
                if stream_id in self.processing_threads:
                    self.processing_threads[stream_id].join(timeout=5.0)
                    del self.processing_threads[stream_id]
                
                # Clean up processor
                if stream_id in self.processors:
                    del self.processors[stream_id]
                
                logger.info(f"⏹️ Stopped processing stream {stream_id}")
                self._update_stats()
                
        except Exception as e:
            logger.error(f"Error stopping processing stream {stream_id}: {e}")
    
    def _process_stream_loop(self, stream_id: str, client_id: str, camera_index: int):
        """Process frames from a camera stream (runs in separate thread)."""
        logger.info(f"🔄 Processing loop started for stream {stream_id}")
        
        while self.processing_active.get(stream_id, False):
            try:
                with self.client_lock:
                    if client_id not in self.clients:
                        break
                    
                    client = self.clients[client_id]
                    frame = client.get_latest_frame(camera_index)
                
                if frame is not None and stream_id in self.processors:
                    # Process frame
                    processor = self.processors[stream_id]
                    processor.process_frame(frame)
                
                time.sleep(0.033)  # ~30 FPS max
                
            except Exception as e:
                logger.error(f"Error in processing loop for stream {stream_id}: {e}")
                time.sleep(0.1)
        
        logger.info(f"🔄 Processing loop ended for stream {stream_id}")
    
    def _stop_all_client_processing(self, client_id: str):
        """Stop all processing for a specific client."""
        streams_to_stop = []
        
        for stream_id in self.processing_active.keys():
            if stream_id.startswith(f"{client_id}_"):
                streams_to_stop.append(stream_id)
        
        for stream_id in streams_to_stop:
            self.stop_processing_stream(stream_id)
    
    def _on_detection(self, stream_id: str, detections: List[Dict], frame: np.ndarray, frame_number: int):
        """Handle detection results."""
        try:
            detection_data = {
                'stream_id': stream_id,
                'detections': detections,
                'frame_number': frame_number,
                'timestamp': datetime.now().isoformat()
            }
            
            self.stats['detections_total'] += len(detections)
            
            for callback in self.detection_callbacks:
                try:
                    callback(detection_data)
                except Exception as e:
                    logger.error(f"Error in detection callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling detection: {e}")
    
    def _on_frame(self, stream_id: str, processed_frame: np.ndarray, frame_number: int, raw_frame: Optional[np.ndarray]):
        """Handle processed frame."""
        try:
            frame_data = {
                'stream_id': stream_id,
                'processed_frame': processed_frame,
                'raw_frame': raw_frame,
                'frame_number': frame_number,
                'timestamp': datetime.now().isoformat()
            }
            
            for callback in self.frame_callbacks:
                try:
                    callback(frame_data)
                except Exception as e:
                    logger.error(f"Error in frame callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling frame: {e}")
    
    def _notify_frame_received(self, client_id: str, camera_index: int, frame: np.ndarray):
        """Notify that a frame was received."""
        # This can be used for additional frame processing or monitoring
        pass
    
    def _notify_client_change(self, change_type: str, client: CameraClient):
        """Notify about client changes."""
        for callback in self.client_callbacks:
            try:
                callback(change_type, client)
            except Exception as e:
                logger.error(f"Error in client callback: {e}")
    
    def _update_stats(self):
        """Update statistics."""
        with self.client_lock:
            self.stats['total_clients'] = len(self.clients)
            self.stats['active_clients'] = sum(1 for c in self.clients.values() if c.is_active)
            self.stats['total_cameras'] = sum(len(c.cameras) for c in self.clients.values())
            self.stats['active_streams'] = len(self.processing_active)
    
    def add_frame_callback(self, callback: Callable):
        """Add frame callback."""
        self.frame_callbacks.append(callback)
    
    def add_detection_callback(self, callback: Callable):
        """Add detection callback."""
        self.detection_callbacks.append(callback)
    
    def add_client_callback(self, callback: Callable):
        """Add client callback."""
        self.client_callbacks.append(callback)
    
    def get_client_status(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific client."""
        with self.client_lock:
            if client_id in self.clients:
                return self.clients[client_id].get_status()
            return None
    
    def get_all_clients_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all clients."""
        with self.client_lock:
            return {client_id: client.get_status() for client_id, client in self.clients.items()}
    
    def get_processing_status(self) -> Dict[str, Dict[str, Any]]:
        """Get processing status."""
        processing_status = {}
        
        for stream_id in self.processing_active.keys():
            if stream_id in self.processors:
                processor = self.processors[stream_id]
                processing_status[stream_id] = {
                    'is_active': self.processing_active.get(stream_id, False),
                    'stats': processor.get_processing_stats() if hasattr(processor, 'get_processing_stats') else {}
                }
        
        return processing_status
    
    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        
        return {
            **self.stats,
            'uptime_seconds': uptime,
            'processing_streams': list(self.processing_active.keys()),
            'active_processors': len(self.processors)
        }
    
    def cleanup_inactive_clients(self, timeout_seconds: int = 30):
        """Clean up inactive clients."""
        current_time = datetime.now()
        inactive_clients = []
        
        with self.client_lock:
            for client_id, client in self.clients.items():
                time_since_heartbeat = (current_time - client.last_heartbeat).total_seconds()
                if time_since_heartbeat > timeout_seconds:
                    inactive_clients.append(client_id)
        
        for client_id in inactive_clients:
            logger.warning(f"🧹 Cleaning up inactive client: {client_id}")
            self.unregister_client(client_id)
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        # Stop all processing
        for stream_id in list(self.processing_active.keys()):
            self.stop_processing_stream(stream_id)


# Global manager instance
_distributed_manager = None

def get_distributed_camera_manager() -> DistributedCameraManager:
    """Get or create the global distributed camera manager."""
    global _distributed_manager
    if _distributed_manager is None:
        _distributed_manager = DistributedCameraManager()
    return _distributed_manager

def initialize_distributed_camera_manager(config: Optional[Config] = None) -> DistributedCameraManager:
    """Initialize the global distributed camera manager."""
    global _distributed_manager
    _distributed_manager = DistributedCameraManager(config)
    return _distributed_manager
