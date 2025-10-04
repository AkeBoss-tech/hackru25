"""
Smart Notification Manager for Doorbell Security System
Provides intelligent notifications with importance hierarchy and LLM-powered descriptions.
"""

import os
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import queue

from .auto_gemini_reporter import get_auto_reporter


class NotificationImportance(Enum):
    """Notification importance levels for security events."""
    LOW = "low"           # Minor movements, small objects
    MEDIUM = "medium"     # Vehicles, animals
    HIGH = "high"         # People detected
    CRITICAL = "critical" # Multiple people, suspicious activity


@dataclass
class NotificationEvent:
    """Represents a notification event."""
    id: str
    timestamp: datetime
    importance: NotificationImportance
    title: str
    message: str
    event_data: Dict[str, Any]
    gemini_report: Optional[Dict] = None
    dismissed: bool = False
    sound_played: bool = False


class NotificationManager:
    """
    Manages smart notifications for security events.
    
    Features:
    - Importance-based filtering
    - LLM-powered event descriptions
    - Popup notifications
    - Sound alerts
    - Notification history
    - Rate limiting
    """
    
    def __init__(self, max_history: int = 100):
        self.logger = logging.getLogger(__name__)
        self.max_history = max_history
        
        # Notification storage
        self.notifications: Dict[str, NotificationEvent] = {}
        self.notification_history: List[NotificationEvent] = []
        
        # Rate limiting
        self.rate_limits = {
            NotificationImportance.LOW: 30,      # 30 seconds between low priority
            NotificationImportance.MEDIUM: 15,   # 15 seconds between medium priority
            NotificationImportance.HIGH: 5,      # 5 seconds between high priority
            NotificationImportance.CRITICAL: 1   # 1 second between critical (no limit)
        }
        self.last_notification_times: Dict[NotificationImportance, datetime] = {}
        
        # Callbacks
        self.on_notification_callbacks: List[Callable] = []
        
        # Threading
        self.notification_queue = queue.Queue()
        self.processing_thread = threading.Thread(target=self._process_notifications, daemon=True)
        self.processing_thread.start()
        
        self.logger.info("NotificationManager initialized")
    
    def add_notification_callback(self, callback: Callable[[NotificationEvent], None]):
        """Add callback for when notifications are created."""
        self.on_notification_callbacks.append(callback)
        self.logger.info(f"Added notification callback: {callback.__name__}")
    
    def _determine_importance(self, event_data: Dict[str, Any]) -> NotificationImportance:
        """Determine notification importance based on event data."""
        objects = event_data.get('objects', [])
        event_type = event_data.get('event_type', 'detected')
        
        if not objects:
            return NotificationImportance.LOW
        
        # Count objects by type
        person_count = 0
        vehicle_count = 0
        animal_count = 0
        other_count = 0
        
        for obj in objects:
            class_name = obj.get('class_name', '').lower()
            if class_name == 'person':
                person_count += 1
            elif class_name in ['car', 'truck', 'bus', 'motorcycle', 'bicycle']:
                vehicle_count += 1
            elif class_name in ['dog', 'cat', 'bird']:
                animal_count += 1
            else:
                other_count += 1
        
        # Determine importance based on event type and object counts
        if event_type in ['entered', 'exited']:
            # Enter/exit events are important - they represent actual movement
            if person_count >= 2:
                return NotificationImportance.CRITICAL  # Multiple people entering/exiting
            elif person_count == 1:
                return NotificationImportance.HIGH      # Single person entering/exiting
            elif vehicle_count > 0:
                return NotificationImportance.MEDIUM    # Vehicle entering/exiting
            elif animal_count > 0:
                return NotificationImportance.MEDIUM    # Animal entering/exiting
            else:
                return NotificationImportance.LOW       # Other objects entering/exiting
        else:
            # Regular detection events are always low priority - just passive monitoring
            return NotificationImportance.LOW
    
    def _should_notify(self, importance: NotificationImportance) -> bool:
        """Check if notification should be sent based on rate limiting."""
        now = datetime.now()
        last_time = self.last_notification_times.get(importance)
        
        if not last_time:
            return True
        
        rate_limit = self.rate_limits[importance]
        time_since_last = (now - last_time).total_seconds()
        
        return time_since_last >= rate_limit
    
    def _create_notification_message(self, event_data: Dict[str, Any], gemini_report: Optional[Dict], event_type: str = "detected") -> tuple[str, str]:
        """Create notification title and message."""
        objects = event_data.get('objects', [])
        importance = self._determine_importance(event_data)
        
        # Count objects
        person_count = sum(1 for obj in objects if obj.get('class_name', '').lower() == 'person')
        vehicle_count = sum(1 for obj in objects if obj.get('class_name', '').lower() in ['car', 'truck', 'bus', 'motorcycle', 'bicycle'])
        animal_count = sum(1 for obj in objects if obj.get('class_name', '').lower() in ['dog', 'cat', 'bird'])
        
        # Create title based on importance, objects, and event type
        if event_type == "entered":
            if importance == NotificationImportance.CRITICAL:
                title = "🚨 Multiple People Entered"
            elif importance == NotificationImportance.HIGH:
                title = "👤 Person Entered"
            elif importance == NotificationImportance.MEDIUM:
                if vehicle_count > 0:
                    title = "🚗 Vehicle Entered"
                else:
                    title = "🐕 Animal Entered"
            else:
                title = "📱 Object Entered"
        elif event_type == "exited":
            if importance == NotificationImportance.CRITICAL:
                title = "🚨 Multiple People Left"
            elif importance == NotificationImportance.HIGH:
                title = "👤 Person Left"
            elif importance == NotificationImportance.MEDIUM:
                if vehicle_count > 0:
                    title = "🚗 Vehicle Left"
                else:
                    title = "🐕 Animal Left"
            else:
                title = "📱 Object Left"
        else:  # detected (default)
            if importance == NotificationImportance.CRITICAL:
                title = "🚨 Multiple People Detected"
            elif importance == NotificationImportance.HIGH:
                title = "👤 Person Detected"
            elif importance == NotificationImportance.MEDIUM:
                if vehicle_count > 0:
                    title = "🚗 Vehicle Detected"
                else:
                    title = "🐕 Animal Detected"
            else:
                title = "📱 Object Detected"
        
        # Create message
        if gemini_report and gemini_report.get('summary'):
            # Use LLM-generated summary
            message = gemini_report['summary']
        else:
            # Fallback to basic description
            object_descriptions = []
            if person_count > 0:
                object_descriptions.append(f"{person_count} person{'s' if person_count > 1 else ''}")
            if vehicle_count > 0:
                object_descriptions.append(f"{vehicle_count} vehicle{'s' if vehicle_count > 1 else ''}")
            if animal_count > 0:
                object_descriptions.append(f"{animal_count} animal{'s' if animal_count > 1 else ''}")
            
            if object_descriptions:
                action = event_type.replace('detected', 'detected').replace('entered', 'entered frame').replace('exited', 'left frame')
                message = f"{action.title()}: {', '.join(object_descriptions)}"
            else:
                action = event_type.replace('detected', 'detected').replace('entered', 'entered frame').replace('exited', 'left frame')
                message = f"{action.title()} with {len(objects)} object{'s' if len(objects) != 1 else ''}"
        
        return title, message
    
    def _process_notifications(self):
        """Background thread to process notifications."""
        while True:
            try:
                event_data = self.notification_queue.get(timeout=1)
                if event_data is None:  # Shutdown signal
                    break
                
                self._handle_event(event_data)
                self.notification_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing notification: {e}")
    
    def _handle_event(self, event_data: Dict[str, Any]):
        """Handle a new detection event and create notification if needed."""
        try:
            # Determine importance
            importance = self._determine_importance(event_data)
            
            # Check rate limiting
            if not self._should_notify(importance):
                self.logger.debug(f"Notification suppressed due to rate limiting: {importance.value}")
                return
            
            # Get Gemini report if available
            event_id = event_data.get('event_id', '')
            gemini_report = None
            try:
                auto_reporter = get_auto_reporter()
                if auto_reporter.enabled:
                    gemini_report = auto_reporter.get_report(event_id)
            except Exception as e:
                self.logger.debug(f"Could not get Gemini report: {e}")
            
            # Get event type from event data
            event_type = event_data.get('event_type', 'detected')
            
            # Create notification message
            title, message = self._create_notification_message(event_data, gemini_report, event_type)
            
            # Create notification event
            notification = NotificationEvent(
                id=f"notif_{int(time.time() * 1000)}",
                timestamp=datetime.now(),
                importance=importance,
                title=title,
                message=message,
                event_data=event_data,
                gemini_report=gemini_report
            )
            
            # Store notification
            self.notifications[notification.id] = notification
            self.notification_history.append(notification)
            
            # Trim history if needed
            if len(self.notification_history) > self.max_history:
                removed = self.notification_history.pop(0)
                self.notifications.pop(removed.id, None)
            
            # Update rate limiting
            self.last_notification_times[importance] = datetime.now()
            
            # Notify callbacks
            for callback in self.on_notification_callbacks:
                try:
                    callback(notification)
                except Exception as e:
                    self.logger.error(f"Error in notification callback: {e}")
            
            self.logger.info(f"Created {importance.value} priority notification: {title}")
            
        except Exception as e:
            self.logger.error(f"Error handling notification event: {e}")
    
    def queue_event(self, event_data: Dict[str, Any]):
        """Queue a detection event for notification processing."""
        self.notification_queue.put(event_data)
    
    def dismiss_notification(self, notification_id: str):
        """Mark a notification as dismissed."""
        if notification_id in self.notifications:
            self.notifications[notification_id].dismissed = True
            self.logger.info(f"Dismissed notification: {notification_id}")
    
    def get_recent_notifications(self, limit: int = 10, importance_filter: Optional[NotificationImportance] = None) -> List[NotificationEvent]:
        """Get recent notifications, optionally filtered by importance."""
        notifications = [n for n in self.notification_history if not n.dismissed]
        
        if importance_filter:
            notifications = [n for n in notifications if n.importance == importance_filter]
        
        # Sort by timestamp (newest first)
        notifications.sort(key=lambda x: x.timestamp, reverse=True)
        
        return notifications[:limit]
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics."""
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        last_24h = now - timedelta(hours=24)
        
        recent_notifications = [n for n in self.notification_history if n.timestamp >= last_24h]
        hourly_notifications = [n for n in recent_notifications if n.timestamp >= last_hour]
        
        # Count by importance
        importance_counts = {}
        for importance in NotificationImportance:
            importance_counts[importance.value] = sum(
                1 for n in recent_notifications if n.importance == importance
            )
        
        return {
            'total_notifications': len(self.notification_history),
            'active_notifications': len([n for n in self.notifications.values() if not n.dismissed]),
            'last_hour': len(hourly_notifications),
            'last_24h': len(recent_notifications),
            'by_importance': importance_counts,
            'queue_size': self.notification_queue.qsize()
        }
    
    def clear_history(self):
        """Clear notification history."""
        self.notifications.clear()
        self.notification_history.clear()
        self.logger.info("Notification history cleared")
    
    def shutdown(self):
        """Shutdown the notification manager."""
        self.notification_queue.put(None)  # Signal shutdown
        if self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5)
        self.logger.info("NotificationManager shutdown complete")


# Singleton instance
_notification_manager: Optional[NotificationManager] = None
_notification_lock = threading.Lock()


def get_notification_manager() -> NotificationManager:
    """Get the singleton instance of NotificationManager."""
    global _notification_manager
    with _notification_lock:
        if _notification_manager is None:
            _notification_manager = NotificationManager()
    return _notification_manager
