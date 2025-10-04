"""
Main video processing class with YOLOv8 integration.
Handles video files, camera streams, and real-time object detection.
"""

import cv2
import torch
import numpy as np
from pathlib import Path
from typing import Union, Optional, Dict, List, Tuple, Callable
import time
import logging
from datetime import datetime
from ultralytics import YOLO

try:
    from .detection_utils import DetectionUtils
    from .object_tracker import ObjectTracker
    from .timeline_manager import TimelineManager
except ImportError:
    from detection_utils import DetectionUtils
    from object_tracker import ObjectTracker
    from timeline_manager import TimelineManager


class VideoProcessor:
    """
    Main class for processing videos and camera streams with YOLOv8.
    
    Features:
    - Real-time object detection
    - Object tracking
    - Video file processing
    - Camera stream handling
    - Customizable callbacks
    - Comprehensive logging
    """
    
    def __init__(
        self,
        model_path: str = None,
        confidence_threshold: float = 0.25,
        device: str = "auto",
        enable_tracking: bool = True,
        tracking_method: str = "bytetrack",
        enable_timeline: bool = True,
        target_classes: List[str] = None
    ):
        """
        Initialize the VideoProcessor.
        
        Args:
            model_path: Path to YOLOv8 model file
            confidence_threshold: Minimum confidence for detections
            device: Device to run inference on ('auto', 'cpu', 'cuda', etc.)
            enable_tracking: Whether to enable object tracking
            tracking_method: Tracking method to use ('bytetrack', 'botsort')
            enable_timeline: Whether to enable timeline event tracking
            target_classes: List of class names to detect (None for all classes)
        """
        # Set model path - use provided path or find it dynamically
        if model_path is None:
            try:
                from .config import Config
                config = Config()
                self.model_path = config.get_model_path()
            except ImportError:
                from config import Config
                config = Config()
                self.model_path = config.get_model_path()
        else:
            self.model_path = model_path
            
        self.confidence_threshold = confidence_threshold
        self.enable_tracking = enable_tracking
        self.tracking_method = tracking_method
        self.enable_timeline = enable_timeline
        
        # Setup logging first
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Set target classes for filtering
        self.target_classes = target_classes
        if target_classes:
            self.logger.info(f"🎯 CLASS FILTERING ENABLED: Only detecting {target_classes}")
            self.logger.info(f"   (Model loads all 80 classes, but filtering happens during detection)")
        else:
            self.logger.info("📋 CLASS FILTERING DISABLED: Detecting all 80 classes")
        
        # Initialize model
        self._setup_model(device)
        
        # Initialize tracking
        if self.enable_tracking:
            self.tracker = ObjectTracker(method=tracking_method)
        else:
            self.tracker = None
            
        # Initialize enter/exit tracking
        from .object_enter_exit_tracker import ObjectEnterExitTracker
        self.enter_exit_tracker = ObjectEnterExitTracker()
            
        # Initialize detection utils
        self.detection_utils = DetectionUtils()
        
        # Initialize timeline manager
        if self.enable_timeline:
            self.timeline_manager = TimelineManager()
        else:
            self.timeline_manager = None
        
        # Processing state
        self.is_processing = False
        self.frame_count = 0
        self.start_time = None
        self.current_video_source = None
        
        # Callbacks
        self.on_detection_callback: Optional[Callable] = None
        self.on_frame_callback: Optional[Callable] = None
        self.on_timeline_event_callback: Optional[Callable] = None
        
        self.logger.info(f"VideoProcessor initialized with model: {model_path}")
        self.logger.info(f"Confidence threshold: {confidence_threshold}")
        self.logger.info(f"Tracking enabled: {enable_tracking}")
        self.logger.info(f"Timeline enabled: {enable_timeline}")
        
    def _setup_model(self, device: str):
        """Setup YOLOv8 model with proper device configuration."""
        try:
            # Fix for PyTorch 2.6+ weights_only security feature
            original_torch_load = torch.load
            def patched_torch_load(*args, **kwargs):
                if 'weights_only' not in kwargs:
                    kwargs['weights_only'] = False
                return original_torch_load(*args, **kwargs)
            torch.load = patched_torch_load
            
            # Load model
            self.model = YOLO(self.model_path)
            
            # Set device
            if device == "auto":
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                self.device = device
                
            self.model.to(self.device)
            
            self.logger.info(f"Model loaded successfully on device: {self.device}")
            self.logger.info(f"Model classes: {list(self.model.names.values())}")
            
        except Exception as e:
            self.logger.error(f"Failed to setup model: {e}")
            raise
    
    def set_detection_callback(self, callback: Callable):
        """
        Set callback function to be called when objects are detected.
        
        Args:
            callback: Function that receives (detections, frame, frame_number)
        """
        self.on_detection_callback = callback
        self.logger.info("Detection callback set")
    
    def set_frame_callback(self, callback: Callable):
        """
        Set callback function to be called for each processed frame.
        
        Args:
            callback: Function that receives (processed_frame, frame_number)
        """
        self.on_frame_callback = callback
        self.logger.info("Frame callback set")
    
    def set_timeline_event_callback(self, callback: Callable):
        """
        Set callback function to be called when timeline events are created.
        
        Args:
            callback: Function that receives (timeline_event)
        """
        self.on_timeline_event_callback = callback
        self.logger.info("Timeline event callback set")
    
    def process_video_file(
        self,
        video_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        display: bool = True,
        save_video: bool = False
    ) -> Dict:
        """
        Process a video file for object detection and tracking.
        
        Args:
            video_path: Path to input video file
            output_path: Path to save processed video (if save_video=True)
            display: Whether to display video during processing
            save_video: Whether to save the processed video
            
        Returns:
            Dictionary with processing statistics
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        self.logger.info(f"Processing video file: {video_path}")
        
        # Set video source for timeline
        self.current_video_source = f"video:{video_path}"
        
        # Open video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        
        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        self.logger.info(f"Video properties: {width}x{height}, {fps} FPS, {total_frames} frames")
        
        # Setup video writer if saving
        writer = None
        if save_video and output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
            self.logger.info(f"Video writer initialized: {output_path}")
        
        # Processing statistics
        stats = {
            'total_frames': total_frames,
            'processed_frames': 0,
            'total_detections': 0,
            'detection_counts': {},
            'processing_time': 0,
            'fps_actual': 0
        }
        
        self.is_processing = True
        self.frame_count = 0
        self.start_time = time.time()
        
        try:
            while cap.isOpened() and self.is_processing:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process frame
                processed_frame, detections, raw_frame = self._process_frame(frame)
                
                # Process timeline events if enabled
                if self.enable_timeline and self.timeline_manager and self.current_video_source:
                    timeline_events = self.timeline_manager.process_frame_detections(
                        detections, frame, self.frame_count, self.current_video_source
                    )
                    
                    # Call timeline event callbacks
                    for event in timeline_events:
                        if self.on_timeline_event_callback:
                            self.on_timeline_event_callback(event)
                
                # Update statistics
                stats['processed_frames'] += 1
                stats['total_detections'] += len(detections)
                
                for detection in detections:
                    class_name = detection['class_name']
                    stats['detection_counts'][class_name] = stats['detection_counts'].get(class_name, 0) + 1
                
                # Print detection info every 30 frames
                if self.frame_count % 30 == 0 and detections:
                    self._print_detection_info(detections, self.frame_count)
                
                # Call callbacks
                if self.on_detection_callback and detections:
                    self.on_detection_callback(detections, frame, self.frame_count)
                
                if self.on_frame_callback:
                    self.on_frame_callback(processed_frame, self.frame_count, raw_frame)
                
                # Save frame if needed
                if writer:
                    writer.write(processed_frame)
                
                # Display frame
                if display:
                    cv2.imshow('Video Processing - Press Q to quit', processed_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.logger.info("Processing stopped by user")
                        break
                
                self.frame_count += 1
                
        except KeyboardInterrupt:
            self.logger.info("Processing interrupted by user")
        finally:
            cap.release()
            if writer:
                writer.release()
            if display:
                cv2.destroyAllWindows()
            
            # Calculate final statistics
            processing_time = time.time() - self.start_time
            stats['processing_time'] = processing_time
            stats['fps_actual'] = stats['processed_frames'] / processing_time if processing_time > 0 else 0
            
            self.is_processing = False
            self._print_processing_summary(stats)
            
        return stats
    
    def process_camera_stream(
        self,
        camera_index: int = 0,
        display: bool = True,
        max_frames: Optional[int] = None
    ) -> Dict:
        """
        Process live camera stream for object detection and tracking.
        
        Args:
            camera_index: Camera device index (usually 0 for default camera)
            display: Whether to display the stream
            max_frames: Maximum number of frames to process (None for unlimited)
            
        Returns:
            Dictionary with processing statistics
        """
        self.logger.info(f"Starting camera stream processing (camera {camera_index})")
        
        # Set video source for timeline
        self.current_video_source = f"camera:{camera_index}"
        
        # Try to open camera
        cap = self._open_camera(camera_index)
        if cap is None:
            raise RuntimeError(f"Could not access camera {camera_index}")
        
        # Get camera properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        
        self.logger.info(f"Camera properties: {width}x{height}, {fps} FPS")
        
        # Processing statistics
        stats = {
            'processed_frames': 0,
            'total_detections': 0,
            'detection_counts': {},
            'processing_time': 0,
            'fps_actual': 0
        }
        
        self.is_processing = True
        self.frame_count = 0
        self.start_time = time.time()
        
        try:
            while cap.isOpened() and self.is_processing:
                ret, frame = cap.read()
                if not ret:
                    self.logger.warning("Failed to read frame from camera")
                    break
                
                # Process frame
                processed_frame, detections, raw_frame = self._process_frame(frame)
                
                # Process timeline events if enabled
                if self.enable_timeline and self.timeline_manager and self.current_video_source:
                    timeline_events = self.timeline_manager.process_frame_detections(
                        detections, frame, self.frame_count, self.current_video_source
                    )
                    
                    # Call timeline event callbacks
                    for event in timeline_events:
                        if self.on_timeline_event_callback:
                            self.on_timeline_event_callback(event)
                
                # Update statistics
                stats['processed_frames'] += 1
                stats['total_detections'] += len(detections)
                
                for detection in detections:
                    class_name = detection['class_name']
                    stats['detection_counts'][class_name] = stats['detection_counts'].get(class_name, 0) + 1
                
                # Print detection info every 30 frames
                if self.frame_count % 30 == 0 and detections:
                    self._print_detection_info(detections, self.frame_count)
                
                # Call callbacks
                if self.on_detection_callback and detections:
                    self.on_detection_callback(detections, frame, self.frame_count)
                
                if self.on_frame_callback:
                    self.on_frame_callback(processed_frame, self.frame_count, raw_frame)
                
                # Display frame
                if display:
                    cv2.imshow('Camera Stream - Press Q to quit', processed_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.logger.info("Stream processing stopped by user")
                        break
                
                self.frame_count += 1
                
                # Check max frames limit
                if max_frames and self.frame_count >= max_frames:
                    self.logger.info(f"Reached maximum frame limit: {max_frames}")
                    break
                
        except KeyboardInterrupt:
            self.logger.info("Stream processing interrupted by user")
        finally:
            cap.release()
            if display:
                cv2.destroyAllWindows()
            
            # Calculate final statistics
            processing_time = time.time() - self.start_time
            stats['processing_time'] = processing_time
            stats['fps_actual'] = stats['processed_frames'] / processing_time if processing_time > 0 else 0
            
            self.is_processing = False
            self._print_processing_summary(stats)
            
        return stats
    
    def _open_camera(self, camera_index: int) -> Optional[cv2.VideoCapture]:
        """Open camera with error handling and fallback options."""
        # Try different camera indices
        for idx in [camera_index, 0, 1]:
            self.logger.info(f"Trying camera index {idx}...")
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                # Test if we can read a frame
                ret, _ = cap.read()
                if ret:
                    self.logger.info(f"✓ Camera {idx} working!")
                    return cap
                else:
                    cap.release()
            else:
                cap.release()
        
        self.logger.error("❌ Could not access any camera")
        return None
    
    def _process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Dict], np.ndarray]:
        """
        Process a single frame for object detection and tracking.
        
        Args:
            frame: Input frame
            
        Returns:
            Tuple of (processed_frame, detections_list, raw_frame)
        """
        # Store raw frame for comparison
        raw_frame = frame.copy()
        
        # Run YOLOv8 inference
        results = self.model(frame, conf=self.confidence_threshold, verbose=False)
        
        # Extract detections
        detections = self.detection_utils.extract_detections(results[0], self.model.names)
        
        # Filter detections by target classes if specified
        if self.target_classes and detections:
            original_count = len(detections)
            filtered_detections = []
            for detection in detections:
                if detection['class_name'] in self.target_classes:
                    filtered_detections.append(detection)
                else:
                    self.logger.info(f"Filtered out detection: {detection['class_name']} (not in target classes)")
            detections = filtered_detections
            if original_count != len(detections):
                self.logger.info(f"Class filtering: {original_count} -> {len(detections)} detections (target classes: {self.target_classes})")
        
        # Apply tracking if enabled
        if self.enable_tracking and self.tracker and detections:
            detections = self.tracker.update(detections, frame)
        
        # Check for enter/exit events
        enter_exit_events = []
        if self.enable_tracking and detections:
            enter_exit_events = self.enter_exit_tracker.update(detections)
            
            # Process enter/exit events
            for event in enter_exit_events:
                # Update event with current context
                event['video_source'] = self.current_video_source or 'camera:0'
                event['frame_number'] = self.frame_count
                
                # Capture snapshot for enter/exit events
                if event['event_type'] in ['entered', 'exited']:
                    snapshot_path = self._capture_snapshot_for_event(frame, event)
                    event['snapshot_path'] = snapshot_path
                
                # Send enter/exit events to timeline and notifications
                self._handle_enter_exit_event(event)
        
        # Draw annotations - use our own drawing to respect filtering
        annotated_frame = self._draw_filtered_detections(frame, detections)
        
        # Skip tracking visualization for minimal design
        # if self.enable_tracking and self.tracker:
        #     annotated_frame = self.tracker.draw_tracks(annotated_frame)
        
        # Add frame info
        annotated_frame = self._add_frame_info(annotated_frame)
        
        # Add filtering status overlay
        if self.target_classes:
            annotated_frame = self._add_filtering_status(annotated_frame)
        
        return annotated_frame, detections, raw_frame
    
    def _draw_filtered_detections(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """
        Draw ultra-minimal detections with clean styling.
        
        Args:
            frame: Input frame
            detections: List of filtered detections to draw
            
        Returns:
            Annotated frame with minimal detections
        """
        annotated_frame = frame.copy()
        
        if not detections:
            return annotated_frame
        
        for detection in detections:
            # Get detection info
            bbox = detection.get('bbox', [])
            class_name = detection.get('class_name', 'unknown')
            track_id = detection.get('track_id')
            
            if len(bbox) != 4:
                continue
                
            x1, y1, x2, y2 = map(int, bbox)
            
            # Get clean color
            color = self._get_clean_class_color(class_name)
            
            # Draw ultra-thin, clean bounding box
            thickness = 2
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, thickness)
            
            # Only show track ID if available, no class name clutter
            if track_id is not None:
                label = f"#{track_id}"
                
                # Use better font with anti-aliasing
                font = cv2.FONT_HERSHEY_DUPLEX
                font_scale = 0.6
                font_thickness = 1
                
                # Get text size
                (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
                
                # Position label inside the box, top-left corner
                label_x = x1 + 5
                label_y = y1 + text_height + 5
                
                # Draw text with outline for better visibility
                cv2.putText(annotated_frame, label, (label_x, label_y), 
                           font, font_scale, (0, 0, 0), font_thickness + 1)  # Black outline
                cv2.putText(annotated_frame, label, (label_x, label_y), 
                           font, font_scale, (255, 255, 255), font_thickness)  # White text
        
        return annotated_frame
    
    def _get_clean_class_color(self, class_name: str) -> tuple:
        """
        Get clean, vibrant colors for different object types.
        
        Args:
            class_name: Name of the class
            
        Returns:
            BGR color tuple
        """
        # Clean, vibrant color palette
        color_map = {
            'person': (0, 255, 0),          # Bright green
            'car': (255, 0, 0),             # Bright blue  
            'truck': (255, 165, 0),         # Orange
            'bus': (255, 0, 255),           # Magenta
            'motorcycle': (0, 255, 255),    # Cyan
            'bicycle': (255, 255, 0),       # Yellow
            'dog': (255, 192, 203),         # Pink
            'cat': (144, 238, 144),         # Light green
            'bird': (173, 216, 230),        # Light blue
        }
        
        # Get color from map or use clean white fallback
        color = color_map.get(class_name.lower(), (255, 255, 255))  # White fallback
        
        return color  # Already in BGR format
    
    def _get_modern_class_color(self, class_name: str) -> tuple:
        """
        Get a modern, clean color for a class name (legacy method).
        
        Args:
            class_name: Name of the class
            
        Returns:
            BGR color tuple
        """
        return self._get_clean_class_color(class_name)
    
    def _get_class_color(self, class_name: str) -> tuple:
        """
        Get a consistent color for a class name (legacy method).
        
        Args:
            class_name: Name of the class
            
        Returns:
            BGR color tuple
        """
        return self._get_modern_class_color(class_name)
    
    def _capture_snapshot_for_event(self, frame: np.ndarray, event: Dict) -> Optional[str]:
        """
        Capture a snapshot for enter/exit events.
        
        Args:
            frame: Current frame
            event: Enter/exit event data
            
        Returns:
            Path to saved snapshot or None if failed
        """
        try:
            if not self.timeline_manager:
                return None
                
            event_id = event.get('event_id', 'unknown')
            snapshot_path = self.timeline_manager._capture_snapshot(frame, event_id, event['objects'][0])
            return snapshot_path
        except Exception as e:
            self.logger.error(f"Failed to capture snapshot for event {event.get('event_id', 'unknown')}: {e}")
            return None
    
    def _handle_enter_exit_event(self, event: Dict):
        """
        Handle enter/exit events by sending them to timeline and notifications.
        
        Args:
            event: Enter/exit event data
        """
        try:
            # Send to timeline manager if enabled
            if self.timeline_manager:
                # Create a TimelineEvent for the enter/exit
                from .timeline_manager import TimelineEvent
                timeline_event = TimelineEvent(
                    event_id=event['event_id'],
                    timestamp=datetime.now(),
                    video_source=event['video_source'],
                    objects=event['objects'],
                    snapshot_path=event.get('snapshot_path'),
                    frame_number=event['frame_number'],
                    confidence_scores=event['confidence_scores']
                )
                
                # Add to timeline
                self.timeline_manager.events.append(timeline_event)
                self.timeline_manager.events_by_id[event['event_id']] = timeline_event
                
                # Update stats
                self.timeline_manager.stats['total_events'] += 1
                self.timeline_manager.stats['last_event_time'] = timeline_event.timestamp.isoformat()
                
                # Queue for Gemini reporting
                try:
                    from .auto_gemini_reporter import get_auto_reporter
                    auto_reporter = get_auto_reporter()
                    if auto_reporter.enabled and event.get('snapshot_path'):
                        event_data = timeline_event.to_dict()
                        auto_reporter.queue_report(event_data, event['snapshot_path'])
                except Exception as e:
                    self.logger.debug(f"Auto Gemini reporting not available: {e}")
                
                # Queue for notifications
                try:
                    from .notification_manager import get_notification_manager
                    notification_manager = get_notification_manager()
                    event_data = timeline_event.to_dict()
                    notification_manager.queue_event(event_data)
                except Exception as e:
                    self.logger.debug(f"Notification system not available: {e}")
                
                # Send to timeline callback
                if self.on_timeline_event_callback:
                    try:
                        self.on_timeline_event_callback(timeline_event.to_dict())
                    except Exception as e:
                        self.logger.error(f"Error in timeline event callback: {e}")
                
                self.logger.info(f"Created {event['event_type']} event: {event['event_id']}")
                
        except Exception as e:
            self.logger.error(f"Error handling enter/exit event: {e}")
    
    def _add_filtering_status(self, frame: np.ndarray) -> np.ndarray:
        """
        Add nothing - completely minimal.
        
        Args:
            frame: Input frame
            
        Returns:
            Frame with no overlays
        """
        # Completely minimal - no status text at all
        return frame
    
    def _add_frame_info(self, frame: np.ndarray) -> np.ndarray:
        """Add nothing - completely minimal."""
        # Completely minimal - no text overlays at all
        return frame
    
    def _print_detection_info(self, detections: List[Dict], frame_number: int):
        """Print detection information to console."""
        if not detections:
            return
        
        print(f"\n🔍 Frame {frame_number}: Detected {len(detections)} objects")
        
        # Count objects by class
        class_counts = {}
        for detection in detections:
            class_name = detection['class_name']
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
        
        # Print object counts
        for class_name, count in class_counts.items():
            confidence = detection.get('confidence', 0)
            track_id = detection.get('track_id', 'N/A')
            print(f"  - {class_name}: {count} (conf: {confidence:.2f}, track: {track_id})")
    
    def _print_processing_summary(self, stats: Dict):
        """Print processing summary statistics."""
        print(f"\n📊 Processing Summary:")
        print(f"  - Processed frames: {stats['processed_frames']}")
        print(f"  - Total detections: {stats['total_detections']}")
        print(f"  - Processing time: {stats['processing_time']:.2f}s")
        print(f"  - Average FPS: {stats['fps_actual']:.2f}")
        
        if stats['detection_counts']:
            print(f"  - Object counts:")
            for class_name, count in stats['detection_counts'].items():
                print(f"    * {class_name}: {count}")
    
    def stop_processing(self):
        """Stop the current processing operation."""
        self.is_processing = False
        self.logger.info("Processing stop requested")
    
    def get_model_info(self) -> Dict:
        """Get information about the loaded model."""
        return {
            'model_path': self.model_path,
            'device': self.device,
            'classes': list(self.model.names.values()),
            'confidence_threshold': self.confidence_threshold,
            'tracking_enabled': self.enable_tracking,
            'tracking_method': self.tracking_method if self.enable_tracking else None,
            'timeline_enabled': self.enable_timeline
        }
    
    def get_timeline_manager(self) -> Optional[TimelineManager]:
        """Get the timeline manager instance."""
        return self.timeline_manager
