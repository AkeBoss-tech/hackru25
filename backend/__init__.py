"""
Backend module for video and camera stream processing with YOLOv8.
"""

__version__ = "1.0.0"
__author__ = "HackRU25 Team"

try:
    from .video_processor import VideoProcessor
    from .camera_handler import CameraHandler
    from .object_tracker import ObjectTracker
    from .detection_utils import DetectionUtils
    from .improved_image_matcher import ImprovedImageMatcher, get_improved_matcher
    from .camera_detection_service import CameraDetectionService, get_camera_detection_service
except ImportError:
    from video_processor import VideoProcessor
    from camera_handler import CameraHandler
    from object_tracker import ObjectTracker
    from detection_utils import DetectionUtils
    from improved_image_matcher import ImprovedImageMatcher, get_improved_matcher
    from camera_detection_service import CameraDetectionService, get_camera_detection_service

__all__ = [
    "VideoProcessor",
    "CameraHandler", 
    "ObjectTracker",
    "DetectionUtils",
    "ImprovedImageMatcher",
    "get_improved_matcher",
    "CameraDetectionService",
    "get_camera_detection_service"
]
