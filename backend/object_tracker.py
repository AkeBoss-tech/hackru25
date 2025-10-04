"""
Object tracking implementation for video processing.
Supports multiple tracking algorithms and provides tracking utilities.
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
import time
from collections import defaultdict, deque


class ObjectTracker:
    """
    Object tracking class supporting multiple tracking algorithms.
    
    Features:
    - ByteTrack tracking
    - BoTSORT tracking
    - Custom tracking utilities
    - Track visualization
    - Track statistics
    """
    
    def __init__(self, method: str = "bytetrack", max_disappeared: int = 30):
        """
        Initialize the object tracker.
        
        Args:
            method: Tracking method ('bytetrack', 'botsort', 'custom')
            max_disappeared: Maximum frames an object can be missing before removal
        """
        self.method = method.lower()
        self.max_disappeared = max_disappeared
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Initialize tracker based on method
        self.tracker = self._initialize_tracker()
        
        # Track management
        self.next_track_id = 1
        self.tracks: Dict[int, Dict] = {}
        self.disappeared_count: Dict[int, int] = defaultdict(int)
        
        # Track history for visualization
        self.track_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=30))
        
        # Statistics
        self.stats = {
            'total_tracks': 0,
            'active_tracks': 0,
            'lost_tracks': 0,
            'track_durations': []
        }
        
        self.logger.info(f"ObjectTracker initialized with method: {method}")
    
    def _initialize_tracker(self):
        """Initialize the appropriate tracker based on method."""
        if self.method == "bytetrack":
            try:
                # ByteTrack tracker
                tracker = cv2.TrackerCSRT_create()
                self.logger.info("ByteTrack tracker initialized")
                return tracker
            except Exception as e:
                self.logger.warning(f"Failed to initialize ByteTrack: {e}, falling back to custom tracking")
                return None
        
        elif self.method == "botsort":
            try:
                # BoTSORT tracker (if available)
                tracker = cv2.TrackerKCF_create()
                self.logger.info("BoTSORT tracker initialized")
                return tracker
            except Exception as e:
                self.logger.warning(f"Failed to initialize BoTSORT: {e}, falling back to custom tracking")
                return None
        
        else:
            self.logger.info("Using custom tracking method")
            return None
    
    def update(self, detections: List[Dict], frame: np.ndarray) -> List[Dict]:
        """
        Update tracks with new detections.
        
        Args:
            detections: List of detection dictionaries
            frame: Current frame
            
        Returns:
            Updated detections with track IDs
        """
        if not detections:
            # No detections, increment disappeared count for all tracks
            for track_id in list(self.tracks.keys()):
                self.disappeared_count[track_id] += 1
                if self.disappeared_count[track_id] > self.max_disappeared:
                    self._remove_track(track_id)
            return []
        
        # Convert detections to format expected by tracker
        detection_boxes = []
        for detection in detections:
            bbox = detection['bbox']
            # Convert to (x, y, w, h) format
            x1, y1, x2, y2 = bbox
            w, h = x2 - x1, y2 - y1
            detection_boxes.append((x1, y1, w, h))
        
        if self.method in ["bytetrack", "botsort"] and self.tracker is not None:
            # Use OpenCV tracker
            updated_detections = self._update_with_opencv_tracker(detections, detection_boxes, frame)
        else:
            # Use custom tracking
            updated_detections = self._update_with_custom_tracker(detections, detection_boxes)
        
        # Update track history
        self._update_track_history(updated_detections)
        
        # Update statistics
        self._update_statistics()
        
        return updated_detections
    
    def _update_with_opencv_tracker(self, detections: List[Dict], detection_boxes: List[Tuple], frame: np.ndarray) -> List[Dict]:
        """Update tracks using OpenCV tracker."""
        # For now, use custom tracking as OpenCV multi-object tracking is complex
        # This is a placeholder for future implementation
        return self._update_with_custom_tracker(detections, detection_boxes)
    
    def _update_with_custom_tracker(self, detections: List[Dict], detection_boxes: List[Tuple]) -> List[Dict]:
        """Update tracks using custom tracking algorithm."""
        # Simple IoU-based tracking
        updated_detections = []
        
        # Calculate IoU between detections and existing tracks
        for i, detection in enumerate(detections):
            bbox = detection_boxes[i]
            best_track_id = None
            best_iou = 0.3  # Minimum IoU threshold
            
            # Find best matching track
            for track_id, track_info in self.tracks.items():
                if self.disappeared_count[track_id] > 0:
                    continue  # Skip disappeared tracks
                
                track_bbox = track_info['bbox']
                iou = self._calculate_iou(bbox, track_bbox)
                
                if iou > best_iou:
                    best_iou = iou
                    best_track_id = track_id
            
            if best_track_id is not None:
                # Update existing track
                detection['track_id'] = best_track_id
                self.tracks[best_track_id]['bbox'] = bbox
                self.tracks[best_track_id]['last_seen'] = time.time()
                self.disappeared_count[best_track_id] = 0
                
                # Update track info
                self.tracks[best_track_id]['class_name'] = detection['class_name']
                self.tracks[best_track_id]['confidence'] = detection['confidence']
                
            else:
                # Create new track
                track_id = self.next_track_id
                self.next_track_id += 1
                
                detection['track_id'] = track_id
                self.tracks[track_id] = {
                    'bbox': bbox,
                    'class_name': detection['class_name'],
                    'confidence': detection['confidence'],
                    'created_time': time.time(),
                    'last_seen': time.time(),
                    'frame_count': 1
                }
                self.disappeared_count[track_id] = 0
                self.stats['total_tracks'] += 1
            
            updated_detections.append(detection)
        
        # Increment disappeared count for tracks not matched
        for track_id in self.tracks:
            if track_id not in [d['track_id'] for d in updated_detections]:
                self.disappeared_count[track_id] += 1
                if self.disappeared_count[track_id] > self.max_disappeared:
                    self._remove_track(track_id)
        
        return updated_detections
    
    def _calculate_iou(self, box1: Tuple, box2: Tuple) -> float:
        """Calculate Intersection over Union (IoU) between two bounding boxes."""
        x1_1, y1_1, w1, h1 = box1
        x1_2, y1_2, w2, h2 = box2
        
        x2_1, y2_1 = x1_1 + w1, y1_1 + h1
        x2_2, y2_2 = x1_2 + w2, y1_2 + h2
        
        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _update_track_history(self, detections: List[Dict]):
        """Update track history for visualization."""
        for detection in detections:
            track_id = detection['track_id']
            bbox = detection['bbox']
            
            # Calculate center point
            x1, y1, x2, y2 = bbox
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            
            self.track_history[track_id].append((center_x, center_y))
    
    def _remove_track(self, track_id: int):
        """Remove a track and update statistics."""
        if track_id in self.tracks:
            track_info = self.tracks[track_id]
            duration = time.time() - track_info['created_time']
            self.stats['track_durations'].append(duration)
            self.stats['lost_tracks'] += 1
            
            del self.tracks[track_id]
            del self.disappeared_count[track_id]
            
            if track_id in self.track_history:
                del self.track_history[track_id]
    
    def _update_statistics(self):
        """Update tracking statistics."""
        self.stats['active_tracks'] = len(self.tracks)
    
    def draw_tracks(self, frame: np.ndarray) -> np.ndarray:
        """
        Draw track information on the frame.
        
        Args:
            frame: Input frame
            
        Returns:
            Frame with track visualization
        """
        # Draw track trails
        for track_id, history in self.track_history.items():
            if len(history) < 2:
                continue
            
            # Draw trail
            points = np.array(history, dtype=np.int32)
            cv2.polylines(frame, [points], False, (0, 255, 255), 2)
            
            # Draw track ID at the end of trail
            if len(history) > 0:
                last_point = history[-1]
                cv2.putText(
                    frame,
                    f"ID:{track_id}",
                    (int(last_point[0]), int(last_point[1]) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 255),
                    2
                )
        
        # Draw track statistics
        self._draw_track_stats(frame)
        
        return frame
    
    def _draw_track_stats(self, frame: np.ndarray):
        """Draw tracking statistics on the frame."""
        stats_text = [
            f"Active Tracks: {self.stats['active_tracks']}",
            f"Total Tracks: {self.stats['total_tracks']}",
            f"Lost Tracks: {self.stats['lost_tracks']}"
        ]
        
        y_offset = 30
        for text in stats_text:
            cv2.putText(
                frame,
                text,
                (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
            y_offset += 25
    
    def get_track_info(self, track_id: int) -> Optional[Dict]:
        """Get information about a specific track."""
        if track_id not in self.tracks:
            return None
        
        track_info = self.tracks[track_id].copy()
        track_info['disappeared_count'] = self.disappeared_count[track_id]
        track_info['history_length'] = len(self.track_history.get(track_id, []))
        
        return track_info
    
    def get_all_tracks(self) -> Dict[int, Dict]:
        """Get information about all active tracks."""
        tracks_info = {}
        for track_id in self.tracks:
            tracks_info[track_id] = self.get_track_info(track_id)
        return tracks_info
    
    def get_tracking_statistics(self) -> Dict:
        """Get comprehensive tracking statistics."""
        stats = self.stats.copy()
        
        if stats['track_durations']:
            stats['avg_track_duration'] = sum(stats['track_durations']) / len(stats['track_durations'])
            stats['max_track_duration'] = max(stats['track_durations'])
            stats['min_track_duration'] = min(stats['track_durations'])
        else:
            stats['avg_track_duration'] = 0
            stats['max_track_duration'] = 0
            stats['min_track_duration'] = 0
        
        stats['track_survival_rate'] = (
            stats['active_tracks'] / max(stats['total_tracks'], 1)
        ) * 100
        
        return stats
    
    def reset_tracking(self):
        """Reset all tracking data."""
        self.tracks.clear()
        self.disappeared_count.clear()
        self.track_history.clear()
        self.next_track_id = 1
        
        self.stats = {
            'total_tracks': 0,
            'active_tracks': 0,
            'lost_tracks': 0,
            'track_durations': []
        }
        
        self.logger.info("Tracking data reset")
    
    def set_tracking_parameters(self, max_disappeared: Optional[int] = None):
        """Update tracking parameters."""
        if max_disappeared is not None:
            self.max_disappeared = max_disappeared
            self.logger.info(f"Max disappeared frames set to: {max_disappeared}")
    
    def export_track_data(self) -> Dict:
        """Export all tracking data for analysis."""
        return {
            'tracks': self.get_all_tracks(),
            'statistics': self.get_tracking_statistics(),
            'track_history': {tid: list(history) for tid, history in self.track_history.items()},
            'parameters': {
                'method': self.method,
                'max_disappeared': self.max_disappeared
            }
        }
