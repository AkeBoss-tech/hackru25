"""
Backend module for video and camera stream processing with YOLOv8.
"""

__version__ = "1.0.0"
__author__ = "HackRU25 Team"

from .video_processor import VideoProcessor
from .camera_handler import CameraHandler
from .object_tracker import ObjectTracker
from .detection_utils import DetectionUtils

__all__ = [
    "VideoProcessor",
    "CameraHandler", 
    "ObjectTracker",
    "DetectionUtils"
]
