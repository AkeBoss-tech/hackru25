"""
Object Enter/Exit Tracking System
Tracks when objects enter and exit the frame to generate enter/exit notifications.
"""

import logging
from typing import Dict, List, Set, Optional
from collections import defaultdict
import time


class ObjectEnterExitTracker:
    """
    Tracks objects entering and exiting the frame.
    
    Features:
    - Detects when objects first appear (enter)
    - Detects when objects disappear (exit)
    - Maintains state of previously tracked objects
    - Generates enter/exit events for notifications
    """
    
    def __init__(self, exit_timeout: float = 3.0):
        """
        Initialize the tracker.
        
        Args:
            exit_timeout: Time in seconds before considering an object "exited"
        """
        self.logger = logging.getLogger(__name__)
        self.exit_timeout = exit_timeout
        
        # Track currently visible objects by track_id
        self.current_objects: Dict[int, Dict] = {}
        
        # Track objects that recently disappeared (for exit timeout)
        self.recently_exited: Dict[int, Dict] = {}
        
        # Track objects that have been seen before (to avoid duplicate enter events)
        self.seen_objects: Set[int] = set()
        
        # Statistics
        self.stats = {
            'total_enters': 0,
            'total_exits': 0,
            'active_objects': 0
        }
        
        self.logger.info("ObjectEnterExitTracker initialized")
    
    def update(self, detections: List[Dict]) -> List[Dict]:
        """
        Update tracker with new detections and return enter/exit events.
        
        Args:
            detections: List of current detections
            
        Returns:
            List of enter/exit events
        """
        current_time = time.time()
        events = []
        
        # Extract track IDs from current detections
        current_track_ids = set()
        current_objects_dict = {}
        
        for detection in detections:
            track_id = detection.get('track_id')
            if track_id is not None:
                current_track_ids.add(track_id)
                current_objects_dict[track_id] = detection
        
        # Check for new objects (enter events)
        new_objects = current_track_ids - self.seen_objects
        for track_id in new_objects:
            if track_id in current_objects_dict:
                event = self._create_enter_event(current_objects_dict[track_id])
                events.append(event)
                self.seen_objects.add(track_id)
                self.stats['total_enters'] += 1
                self.logger.info(f"Object entered: {detection.get('class_name', 'unknown')} (ID: {track_id})")
        
        # Check for objects that disappeared (exit events)
        disappeared_objects = set(self.current_objects.keys()) - current_track_ids
        for track_id in disappeared_objects:
            if track_id in self.current_objects:
                # Add to recently exited with timestamp
                self.recently_exited[track_id] = {
                    'object': self.current_objects[track_id],
                    'exit_time': current_time
                }
        
        # Check recently exited objects for timeout
        timed_out_objects = []
        for track_id, exit_info in self.recently_exited.items():
            if current_time - exit_info['exit_time'] >= self.exit_timeout:
                event = self._create_exit_event(exit_info['object'])
                events.append(event)
                timed_out_objects.append(track_id)
                self.stats['total_exits'] += 1
                self.logger.info(f"Object exited: {exit_info['object'].get('class_name', 'unknown')} (ID: {track_id})")
        
        # Remove timed out objects
        for track_id in timed_out_objects:
            del self.recently_exited[track_id]
            self.seen_objects.discard(track_id)  # Allow re-detection if object returns
        
        # Update current objects
        self.current_objects = current_objects_dict.copy()
        self.stats['active_objects'] = len(self.current_objects)
        
        return events
    
    def _create_enter_event(self, detection: Dict) -> Dict:
        """Create an enter event from a detection."""
        return {
            'event_type': 'entered',
            'event_id': f"enter_{int(time.time() * 1000)}_{detection.get('track_id', 'unknown')}",
            'timestamp': time.time(),
            'objects': [detection],
            'video_source': 'camera:0',  # Will be updated by caller
            'frame_number': 0,  # Will be updated by caller
            'confidence_scores': [detection.get('confidence', 0.0)],
            'snapshot_path': None  # Will be set if snapshot is captured
        }
    
    def _create_exit_event(self, detection: Dict) -> Dict:
        """Create an exit event from a detection."""
        return {
            'event_type': 'exited',
            'event_id': f"exit_{int(time.time() * 1000)}_{detection.get('track_id', 'unknown')}",
            'timestamp': time.time(),
            'objects': [detection],
            'video_source': 'camera:0',  # Will be updated by caller
            'frame_number': 0,  # Will be updated by caller
            'confidence_scores': [detection.get('confidence', 0.0)],
            'snapshot_path': None  # Will be set if snapshot is captured
        }
    
    def get_stats(self) -> Dict:
        """Get tracker statistics."""
        return {
            **self.stats,
            'currently_tracking': len(self.current_objects),
            'recently_exited': len(self.recently_exited),
            'total_seen': len(self.seen_objects)
        }
    
    def reset(self):
        """Reset the tracker state."""
        self.current_objects.clear()
        self.recently_exited.clear()
        self.seen_objects.clear()
        self.stats = {
            'total_enters': 0,
            'total_exits': 0,
            'active_objects': 0
        }
        self.logger.info("ObjectEnterExitTracker reset")
