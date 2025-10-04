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
            self.logger.info(f"Target classes set to: {target_classes}")
        
        # Initialize model
        self._setup_model(device)
        
        # Initialize tracking
        if self.enable_tracking:
            self.tracker = ObjectTracker(method=tracking_method)
        else:
            self.tracker = None
            
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
            filtered_detections = []
            for detection in detections:
                if detection['class_name'] in self.target_classes:
                    filtered_detections.append(detection)
            detections = filtered_detections
        
        # Apply tracking if enabled
        if self.enable_tracking and self.tracker and detections:
            detections = self.tracker.update(detections, frame)
        
        # Draw annotations
        annotated_frame = results[0].plot()
        
        # Add tracking info if enabled
        if self.enable_tracking and self.tracker:
            annotated_frame = self.tracker.draw_tracks(annotated_frame)
        
        # Add frame info
        annotated_frame = self._add_frame_info(annotated_frame)
        
        return annotated_frame, detections, raw_frame
    
    def _add_frame_info(self, frame: np.ndarray) -> np.ndarray:
        """Add frame information overlay to the frame."""
        # Add frame counter
        cv2.putText(
            frame, 
            f"Frame: {self.frame_count}", 
            (10, 30), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.7, 
            (0, 255, 0), 
            2
        )
        
        # Add FPS if available
        if self.start_time and self.frame_count > 0:
            elapsed = time.time() - self.start_time
            fps = self.frame_count / elapsed
            cv2.putText(
                frame, 
                f"FPS: {fps:.1f}", 
                (10, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, 
                (0, 255, 0), 
                2
            )
        
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
