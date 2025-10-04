"""
Timeline Event Manager for tracking object detection events.
Handles new object detection, snapshot capture, and timeline management.
"""

import os
import json
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
from collections import defaultdict, deque
import threading
import time
from typing import Set


class TimelineEvent:
    """Represents a timeline event with metadata and snapshot."""
    
    def __init__(
        self,
        event_id: str,
        timestamp: datetime,
        video_source: str,
        objects: List[Dict],
        snapshot_path: Optional[str] = None,
        frame_number: int = 0,
        confidence_scores: List[float] = None
    ):
        self.event_id = event_id
        self.timestamp = timestamp
        self.video_source = video_source
        self.objects = objects
        self.snapshot_path = snapshot_path
        self.frame_number = frame_number
        self.confidence_scores = confidence_scores or []
        
    def to_dict(self) -> Dict:
        """Convert event to dictionary for JSON serialization."""
        # Convert numpy types to Python native types for JSON serialization
        def convert_numpy_types(obj):
            if hasattr(obj, 'item'):  # numpy scalar
                return obj.item()
            elif isinstance(obj, dict):
                return {k: convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            else:
                return obj
        
        # Convert objects to ensure all numpy types are converted
        converted_objects = convert_numpy_types(self.objects)
        converted_confidence_scores = convert_numpy_types(self.confidence_scores)
        
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'video_source': self.video_source,
            'objects': converted_objects,
            'snapshot_path': self.snapshot_path,
            'frame_number': int(self.frame_number),
            'confidence_scores': converted_confidence_scores,
            'object_count': len(self.objects),
            'object_types': list(set(obj.get('class_name', 'unknown') for obj in self.objects))
        }


class TimelineManager:
    """
    Manages timeline events for object detection.
    
    Features:
    - New object detection tracking
    - Snapshot capture and storage
    - Timeline event management
    - Event persistence and retrieval
    - Real-time event broadcasting
    """
    
    def __init__(
        self,
        snapshots_dir: str = "timeline_snapshots",
        max_events: int = 1000,
        new_object_threshold_frames: int = 2,
        min_object_area: float = 0.01,
        event_grouping_threshold: float = 0.3
    ):
        """
        Initialize TimelineManager.
        
        Args:
            snapshots_dir: Directory to store snapshots
            max_events: Maximum number of events to keep in memory
            new_object_threshold_frames: Number of frames to track new objects
            min_object_area: Minimum object area ratio to consider significant (0.0-1.0)
            event_grouping_threshold: IoU threshold for grouping similar events (0.0-1.0)
        """
        self.snapshots_dir = Path(snapshots_dir)
        self.max_events = max_events
        self.new_object_threshold_frames = new_object_threshold_frames
        self.min_object_area = min_object_area
        self.event_grouping_threshold = event_grouping_threshold
        
        # Create snapshots directory
        self.snapshots_dir.mkdir(exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Event storage
        self.events: deque = deque(maxlen=max_events)
        self.events_by_id: Dict[str, TimelineEvent] = {}
        
        # Object tracking for new object detection
        self.tracked_objects: Dict[int, Dict] = {}  # track_id -> object_info
        self.new_object_frames: Dict[int, int] = {}  # track_id -> frames_since_first_seen
        self.previous_frame_objects: Set[int] = set()
        
        # Event grouping for reducing similar events
        self.recent_events: deque = deque(maxlen=50)  # Store recent events for grouping
        
        # Statistics
        self.stats = {
            'total_events': 0,
            'total_objects_detected': 0,
            'new_object_events': 0,
            'snapshots_captured': 0,
            'last_event_time': None,
            'people_count': 0,
            'cars_count': 0,
            'unique_objects_count': 0,  # Track count of unique objects
            'object_counts': {}  # Track counts by class
        }
        
        # Internal tracking (not serialized)
        self._unique_objects = set()  # Track unique object IDs to avoid double counting
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Event callbacks
        self.event_callbacks: List[callable] = []
        
        self.logger.info(f"TimelineManager initialized with snapshots dir: {snapshots_dir}")
    
    def add_event_callback(self, callback: callable):
        """Add callback function to be called when new events are created."""
        self.event_callbacks.append(callback)
        self.logger.info("Event callback added")
    
    def _calculate_object_area_ratio(self, detection: Dict, frame_shape: tuple) -> float:
        """
        Calculate the area ratio of an object relative to the frame.
        
        Args:
            detection: Detection dictionary with bbox
            frame_shape: Frame shape (height, width)
            
        Returns:
            Area ratio (0.0-1.0)
        """
        try:
            bbox = detection.get('bbox', [])
            if len(bbox) != 4:
                return 0.0
            
            x1, y1, x2, y2 = bbox
            object_area = (x2 - x1) * (y2 - y1)
            frame_area = frame_shape[0] * frame_shape[1]
            
            return object_area / frame_area
            
        except Exception as e:
            self.logger.error(f"Error calculating object area ratio: {e}")
            return 0.0
    
    def _is_significant_object(self, detection: Dict, frame_shape: tuple) -> bool:
        """
        Check if an object is significant based on area and confidence.
        
        Args:
            detection: Detection dictionary
            frame_shape: Frame shape (height, width)
            
        Returns:
            True if object is significant enough to record
        """
        area_ratio = self._calculate_object_area_ratio(detection, frame_shape)
        confidence = detection.get('confidence', 0.0)
        
        # Object must be large enough and confident enough
        return (area_ratio >= self.min_object_area and 
                confidence >= 0.3)
    
    def _should_group_with_recent_event(self, new_event: TimelineEvent) -> bool:
        """
        Check if the new event should be grouped with recent events.
        
        Args:
            new_event: New timeline event
            
        Returns:
            True if event should be grouped (and not added separately)
        """
        if not self.recent_events:
            return False
        
        try:
            # Check IoU with recent events
            for recent_event in list(self.recent_events):
                if self._calculate_event_iou(new_event, recent_event) > self.event_grouping_threshold:
                    # Update the recent event with new information
                    self._merge_events(recent_event, new_event)
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking event grouping: {e}")
            return False
    
    def _calculate_event_iou(self, event1: TimelineEvent, event2: TimelineEvent) -> float:
        """
        Calculate IoU between two events based on their object bounding boxes.
        
        Args:
            event1: First timeline event
            event2: Second timeline event
            
        Returns:
            IoU value (0.0-1.0)
        """
        try:
            if not event1.objects or not event2.objects:
                return 0.0
            
            # Get the largest object from each event
            obj1 = event1.objects[0]  # Assume first object is primary
            obj2 = event2.objects[0]
            
            bbox1 = obj1.get('bbox', [])
            bbox2 = obj2.get('bbox', [])
            
            if len(bbox1) != 4 or len(bbox2) != 4:
                return 0.0
            
            # Calculate IoU
            x1_1, y1_1, x2_1, y2_1 = bbox1
            x1_2, y1_2, x2_2, y2_2 = bbox2
            
            # Intersection
            x1_i = max(x1_1, x1_2)
            y1_i = max(y1_1, y1_2)
            x2_i = min(x2_1, x2_2)
            y2_i = min(y2_1, y2_2)
            
            if x2_i <= x1_i or y2_i <= y1_i:
                return 0.0
            
            intersection = (x2_i - x1_i) * (y2_i - y1_i)
            area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
            area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
            union = area1 + area2 - intersection
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating event IoU: {e}")
            return 0.0
    
    def _merge_events(self, existing_event: TimelineEvent, new_event: TimelineEvent):
        """
        Merge a new event into an existing recent event.
        
        Args:
            existing_event: Existing event to update
            new_event: New event to merge
        """
        try:
            # Update timestamp to most recent
            existing_event.timestamp = new_event.timestamp
            existing_event.frame_number = new_event.frame_number
            
            # Update objects list (keep unique objects)
            existing_objects = {obj.get('track_id', -1): obj for obj in existing_event.objects}
            for obj in new_event.objects:
                track_id = obj.get('track_id', -1)
                if track_id not in existing_objects:
                    existing_objects[track_id] = obj
            
            existing_event.objects = list(existing_objects.values())
            
            # Update confidence scores
            existing_event.confidence_scores = [obj.get('confidence', 0.0) for obj in existing_event.objects]
            
            self.logger.info(f"Merged event {new_event.event_id} into {existing_event.event_id}")
            
        except Exception as e:
            self.logger.error(f"Error merging events: {e}")
    
    def process_frame_detections(
        self,
        detections: List[Dict],
        frame: np.ndarray,
        frame_number: int,
        video_source: str
    ) -> List[TimelineEvent]:
        """
        Process frame detections and create timeline events for significant objects.
        Uses YOLO tracking and object area to determine significance.
        
        Args:
            detections: List of detection dictionaries with track_ids
            frame: Current frame
            frame_number: Frame number
            video_source: Source identifier (camera index, video path, etc.)
            
        Returns:
            List of new timeline events created
        """
        new_events = []
        frame_shape = frame.shape[:2]  # (height, width)
        
        with self.lock:
            # Get current track IDs
            current_track_ids = set()
            significant_detections = []
            
            # Filter detections for significant objects
            for detection in detections:
                if 'track_id' in detection and detection['track_id'] is not None:
                    current_track_ids.add(detection['track_id'])
                    
                    # Check if this object is significant
                    if self._is_significant_object(detection, frame_shape):
                        significant_detections.append(detection)
            
            # Find new objects (tracks not in previous frame)
            new_track_ids = current_track_ids - self.previous_frame_objects
            
            # Update tracking for new objects
            for track_id in new_track_ids:
                # Find the detection for this track
                detection = next((d for d in significant_detections if d.get('track_id') == track_id), None)
                if detection:
                    self.tracked_objects[track_id] = {
                        'first_seen_frame': frame_number,
                        'detection': detection,
                        'frames_tracked': 1
                    }
                    self.new_object_frames[track_id] = 1
            
            # Update frame counts for tracked objects
            for track_id in current_track_ids:
                if track_id in self.new_object_frames:
                    self.new_object_frames[track_id] += 1
            
            # Create events for objects that have been tracked for threshold frames
            for track_id in list(self.new_object_frames.keys()):
                if self.new_object_frames[track_id] >= self.new_object_threshold_frames:
                    # Create timeline event
                    event = self._create_new_object_event(
                        track_id, frame, frame_number, video_source
                    )
                    if event:
                        # Check if this event should be grouped with recent events
                        if not self._should_group_with_recent_event(event):
                            new_events.append(event)
                            # Add to recent events for grouping
                            self.recent_events.append(event)
                        else:
                            # Event was grouped, don't add as new event
                            continue
                    
                    # Remove from new object tracking
                    del self.new_object_frames[track_id]
                    if track_id in self.tracked_objects:
                        del self.tracked_objects[track_id]
            
            # Update previous frame objects
            self.previous_frame_objects = current_track_ids.copy()
            
            # Clean up lost tracks
            self._cleanup_lost_tracks(current_track_ids)
        
        # Call event callbacks for new events
        for event in new_events:
            for callback in self.event_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error(f"Error in event callback: {e}")
        
        return new_events
    
    def _create_new_object_event(
        self,
        track_id: int,
        frame: np.ndarray,
        frame_number: int,
        video_source: str
    ) -> Optional[TimelineEvent]:
        """Create a timeline event for a new object."""
        if track_id not in self.tracked_objects:
            return None
        
        tracked_info = self.tracked_objects[track_id]
        detection = tracked_info['detection']
        
        # Generate event ID
        event_id = f"event_{int(time.time() * 1000)}_{track_id}"
        
        # Capture snapshot
        snapshot_path = self._capture_snapshot(frame, event_id, detection)
        
        # Create event
        event = TimelineEvent(
            event_id=event_id,
            timestamp=datetime.now(),
            video_source=video_source,
            objects=[detection],
            snapshot_path=snapshot_path,
            frame_number=frame_number,
            confidence_scores=[detection.get('confidence', 0.0)]
        )
        
        # Store event
        self.events.append(event)
        self.events_by_id[event_id] = event
        
        # Update statistics
        self.stats['total_events'] += 1
        self.stats['total_objects_detected'] += 1
        self.stats['new_object_events'] += 1
        self.stats['last_event_time'] = event.timestamp.isoformat()
        
        if snapshot_path:
            self.stats['snapshots_captured'] += 1
        
        # Track unique objects to avoid double counting
        track_id = detection.get('track_id')
        if track_id is not None and track_id not in self._unique_objects:
            self._unique_objects.add(track_id)
            self.stats['unique_objects_count'] = len(self._unique_objects)
        
        # Queue for auto Gemini report generation
        try:
            from .auto_gemini_reporter import get_auto_reporter
            auto_reporter = get_auto_reporter()
            if auto_reporter.enabled and snapshot_path:
                event_data = event.to_dict()
                auto_reporter.queue_report(event_data, snapshot_path)
        except Exception as e:
            self.logger.debug(f"Auto Gemini reporting not available: {e}")
            
            # Count specific object types
            class_name = detection.get('class_name', 'unknown')
            if class_name == 'person':
                self.stats['people_count'] += 1
            elif class_name in ['car', 'truck', 'bus', 'motorcycle', 'bicycle']:
                self.stats['cars_count'] += 1
            
            # Update object counts
            if class_name not in self.stats['object_counts']:
                self.stats['object_counts'][class_name] = 0
            self.stats['object_counts'][class_name] += 1
        
        self.logger.info(f"Created timeline event: {event_id} for object {detection.get('class_name', 'unknown')}")
        
        return event
    
    def _capture_snapshot(
        self,
        frame: np.ndarray,
        event_id: str,
        detection: Dict
    ) -> Optional[str]:
        """Capture and save snapshots of the whole frame (both raw and annotated)."""
        try:
            # Extract bounding box for annotation
            bbox = detection.get('bbox', [])
            if len(bbox) != 4:
                return None
            
            x1, y1, x2, y2 = [int(coord) for coord in bbox]
            
            # Save snapshots of the whole frame
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            class_name = detection.get('class_name', 'unknown')
            confidence = detection.get('confidence', 0.0)
            
            # Create annotated snapshot (whole frame with bounding box)
            annotated_frame = frame.copy()
            
            # Draw bounding box and label on the whole frame
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
            
            label = f"{class_name}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
            
            # Draw label background
            cv2.rectangle(annotated_frame, 
                         (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), 
                         (0, 255, 0), -1)
            
            # Draw label text
            cv2.putText(annotated_frame, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            
            # Add timestamp and event info to the frame
            frame_info = f"Event: {event_id} | {timestamp}"
            cv2.putText(annotated_frame, frame_info, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Save both raw and annotated snapshots
            raw_filename = f"{timestamp}_{event_id}_raw.jpg"
            annotated_filename = f"{timestamp}_{event_id}_annotated.jpg"
            
            raw_path = self.snapshots_dir / raw_filename
            annotated_path = self.snapshots_dir / annotated_filename
            
            # Save raw snapshot (whole frame without annotations)
            cv2.imwrite(str(raw_path), frame)
            
            # Save annotated snapshot (whole frame with annotations)
            cv2.imwrite(str(annotated_path), annotated_frame)
            
            # Return the annotated path as the primary snapshot
            return str(annotated_path)
            
        except Exception as e:
            self.logger.error(f"Error capturing snapshot: {e}")
            return None
    
    def _cleanup_lost_tracks(self, current_track_ids: set):
        """Clean up tracking data for objects that are no longer visible."""
        lost_tracks = set(self.tracked_objects.keys()) - current_track_ids
        
        for track_id in lost_tracks:
            if track_id in self.tracked_objects:
                del self.tracked_objects[track_id]
            if track_id in self.new_object_frames:
                del self.new_object_frames[track_id]
    
    def get_events(
        self,
        limit: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        video_source: Optional[str] = None
    ) -> List[Dict]:
        """
        Get timeline events with optional filtering.
        
        Args:
            limit: Maximum number of events to return
            start_time: Filter events after this time
            end_time: Filter events before this time
            video_source: Filter events by video source
            
        Returns:
            List of event dictionaries
        """
        with self.lock:
            events = list(self.events)
        
        # Apply filters
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        if video_source:
            events = [e for e in events if e.video_source == video_source]
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply limit
        if limit:
            events = events[:limit]
        
        return [event.to_dict() for event in events]
    
    def get_event_by_id(self, event_id: str) -> Optional[Dict]:
        """Get a specific event by ID."""
        with self.lock:
            event = self.events_by_id.get(event_id)
        
        return event.to_dict() if event else None
    
    def get_snapshot(self, snapshot_path: str) -> Optional[bytes]:
        """Get snapshot image data."""
        try:
            if os.path.exists(snapshot_path):
                with open(snapshot_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            self.logger.error(f"Error reading snapshot {snapshot_path}: {e}")
        
        return None
    
    def get_raw_snapshot_path(self, annotated_path: str) -> Optional[str]:
        """Get the corresponding raw snapshot path for an annotated snapshot."""
        try:
            if '_annotated.jpg' in annotated_path:
                raw_path = annotated_path.replace('_annotated.jpg', '_raw.jpg')
                if os.path.exists(raw_path):
                    return raw_path
        except Exception as e:
            self.logger.error(f"Error getting raw snapshot path for {annotated_path}: {e}")
        
        return None
    
    def get_statistics(self) -> Dict:
        """Get timeline statistics."""
        with self.lock:
            stats = self.stats.copy()
        
        stats['events_in_memory'] = len(self.events)
        stats['tracked_objects'] = len(self.tracked_objects)
        stats['new_object_candidates'] = len(self.new_object_frames)
        
        return stats
    
    def clear_events(self):
        """Clear all events and reset statistics."""
        with self.lock:
            self.events.clear()
            self.events_by_id.clear()
            self.tracked_objects.clear()
            self.new_object_frames.clear()
            self.previous_frame_objects.clear()
            self._unique_objects.clear()
            
            self.stats = {
                'total_events': 0,
                'total_objects_detected': 0,
                'new_object_events': 0,
                'snapshots_captured': 0,
                'last_event_time': None,
                'people_count': 0,
                'cars_count': 0,
                'unique_objects_count': 0,
                'object_counts': {}
            }
        
        self.logger.info("All timeline events cleared")
    
    def set_timeline_parameters(self, min_object_area: Optional[float] = None, event_grouping_threshold: Optional[float] = None):
        """Update timeline detection parameters."""
        if min_object_area is not None:
            self.min_object_area = min_object_area
            self.logger.info(f"Min object area set to: {min_object_area}")
        
        if event_grouping_threshold is not None:
            self.event_grouping_threshold = event_grouping_threshold
            self.logger.info(f"Event grouping threshold set to: {event_grouping_threshold}")
    
    def export_events(self, filepath: str, format: str = "json") -> bool:
        """Export events to file."""
        try:
            events = self.get_events()
            
            if format.lower() == "json":
                with open(filepath, 'w') as f:
                    json.dump(events, f, indent=2)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            self.logger.info(f"Exported {len(events)} events to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting events: {e}")
            return False
