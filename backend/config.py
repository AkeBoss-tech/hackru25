"""
Configuration settings for the video processing backend.
Centralized configuration management for all components.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging


class Config:
    """Configuration class for video processing backend."""
    
    # Model settings
    DEFAULT_MODEL_PATH = "yolov8n.pt"  # Will be resolved dynamically
    CONFIDENCE_THRESHOLD = 0.25
    DEVICE = "auto"  # "auto", "cpu", "cuda", "mps"
    
    # Tracking settings
    ENABLE_TRACKING = True
    TRACKING_METHOD = "bytetrack"  # "bytetrack", "botsort", "custom"
    MAX_DISAPPEARED = 30
    
    # Camera settings
    DEFAULT_CAMERA_INDEX = 0
    CAMERA_BUFFER_SIZE = 10
    CAMERA_WIDTH = None  # None for default
    CAMERA_HEIGHT = None  # None for default
    CAMERA_FPS = None  # None for default
    
    # Processing settings
    MAX_FRAMES = None  # None for unlimited
    FRAME_SKIP = 1  # Process every Nth frame
    SAVE_VIDEO = False
    DISPLAY_VIDEO = True
    
    # Output settings
    OUTPUT_DIR = "runs/detect"
    SAVE_DETECTIONS = False
    DETECTION_FORMAT = "json"  # "json", "csv", "txt"
    
    # Visualization settings
    SHOW_CONFIDENCE = True
    SHOW_CLASS_NAMES = True
    SHOW_BOUNDING_BOXES = True
    SHOW_TRACKS = True
    SHOW_STATISTICS = True
    
    # Logging settings
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = None  # None for console only
    
    # Performance settings
    ENABLE_GPU_OPTIMIZATION = True
    BATCH_SIZE = 1
    NUM_WORKERS = 0
    
    # Detection filtering
    MIN_DETECTION_AREA = 0
    TARGET_CLASSES = None  # None for all classes
    MAX_DETECTIONS_PER_FRAME = None
    
    # Callback settings
    DETECTION_CALLBACK_INTERVAL = 30  # Call detection callback every N frames
    FRAME_CALLBACK_INTERVAL = 1  # Call frame callback every N frames
    
    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        """
        Load configuration from a file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Config instance with loaded settings
        """
        config = cls()
        
        if not os.path.exists(config_path):
            logging.warning(f"Config file not found: {config_path}")
            return config
        
        try:
            import json
            with open(config_path, 'r') as f:
                settings = json.load(f)
            
            # Update configuration with loaded settings
            for key, value in settings.items():
                if hasattr(config, key.upper()):
                    setattr(config, key.upper(), value)
                else:
                    logging.warning(f"Unknown config key: {key}")
            
            logging.info(f"Configuration loaded from {config_path}")
            
        except Exception as e:
            logging.error(f"Failed to load configuration: {e}")
        
        return config
    
    def to_file(self, config_path: str) -> bool:
        """
        Save configuration to a file.
        
        Args:
            config_path: Path to save configuration file
            
        Returns:
            True if save was successful
        """
        try:
            import json
            
            # Get all configuration attributes
            settings = {}
            for attr in dir(self):
                if attr.isupper() and not attr.startswith('_'):
                    value = getattr(self, attr)
                    # Convert non-serializable objects
                    if isinstance(value, Path):
                        value = str(value)
                    settings[attr.lower()] = value
            
            with open(config_path, 'w') as f:
                json.dump(settings, f, indent=2)
            
            logging.info(f"Configuration saved to {config_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to save configuration: {e}")
            return False
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model-related configuration."""
        return {
            'model_path': self.DEFAULT_MODEL_PATH,
            'confidence_threshold': self.CONFIDENCE_THRESHOLD,
            'device': self.DEVICE,
            'enable_gpu_optimization': self.ENABLE_GPU_OPTIMIZATION,
            'batch_size': self.BATCH_SIZE,
            'num_workers': self.NUM_WORKERS
        }
    
    def get_tracking_config(self) -> Dict[str, Any]:
        """Get tracking-related configuration."""
        return {
            'enable_tracking': self.ENABLE_TRACKING,
            'tracking_method': self.TRACKING_METHOD,
            'max_disappeared': self.MAX_DISAPPEARED
        }
    
    def get_camera_config(self) -> Dict[str, Any]:
        """Get camera-related configuration."""
        return {
            'camera_index': self.DEFAULT_CAMERA_INDEX,
            'buffer_size': self.CAMERA_BUFFER_SIZE,
            'width': self.CAMERA_WIDTH,
            'height': self.CAMERA_HEIGHT,
            'fps': self.CAMERA_FPS
        }
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing-related configuration."""
        return {
            'max_frames': self.MAX_FRAMES,
            'frame_skip': self.FRAME_SKIP,
            'save_video': self.SAVE_VIDEO,
            'display_video': self.DISPLAY_VIDEO,
            'output_dir': self.OUTPUT_DIR,
            'save_detections': self.SAVE_DETECTIONS,
            'detection_format': self.DETECTION_FORMAT
        }
    
    def get_visualization_config(self) -> Dict[str, Any]:
        """Get visualization-related configuration."""
        return {
            'show_confidence': self.SHOW_CONFIDENCE,
            'show_class_names': self.SHOW_CLASS_NAMES,
            'show_bounding_boxes': self.SHOW_BOUNDING_BOXES,
            'show_tracks': self.SHOW_TRACKS,
            'show_statistics': self.SHOW_STATISTICS
        }
    
    def get_detection_filter_config(self) -> Dict[str, Any]:
        """Get detection filtering configuration."""
        return {
            'min_detection_area': self.MIN_DETECTION_AREA,
            'target_classes': self.TARGET_CLASSES,
            'max_detections_per_frame': self.MAX_DETECTIONS_PER_FRAME
        }
    
    def get_callback_config(self) -> Dict[str, Any]:
        """Get callback configuration."""
        return {
            'detection_callback_interval': self.DETECTION_CALLBACK_INTERVAL,
            'frame_callback_interval': self.FRAME_CALLBACK_INTERVAL
        }
    
    def _find_model_file(self) -> Optional[str]:
        """
        Find the YOLOv8 model file in common locations.
        
        Returns:
            Path to model file if found, None otherwise
        """
        possible_paths = [
            self.DEFAULT_MODEL_PATH,  # Current directory
            f"../{self.DEFAULT_MODEL_PATH}",  # Parent directory
            f"../../{self.DEFAULT_MODEL_PATH}",  # Grandparent directory
            os.path.join(os.path.dirname(__file__), self.DEFAULT_MODEL_PATH),  # Backend directory
            os.path.join(os.path.dirname(__file__), "..", self.DEFAULT_MODEL_PATH),  # Project root
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def get_model_path(self) -> str:
        """
        Get the actual path to the model file.
        
        Returns:
            Path to model file
        """
        model_path = self._find_model_file()
        return model_path if model_path else self.DEFAULT_MODEL_PATH
    
    def setup_logging(self):
        """Setup logging based on configuration."""
        # Create formatter
        formatter = logging.Formatter(self.LOG_FORMAT)
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.LOG_LEVEL)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.LOG_LEVEL)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # File handler (if specified)
        if self.LOG_FILE:
            file_handler = logging.FileHandler(self.LOG_FILE)
            file_handler.setLevel(self.LOG_LEVEL)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
    
    def validate(self, check_model_file: bool = True) -> bool:
        """
        Validate configuration settings.
        
        Args:
            check_model_file: Whether to check if model file exists
            
        Returns:
            True if configuration is valid
        """
        errors = []
        
        # Validate model path (optional for testing)
        if check_model_file:
            model_path = self._find_model_file()
            if not model_path:
                errors.append(f"Model file not found: {self.DEFAULT_MODEL_PATH}")
        
        # Validate confidence threshold
        if not 0.0 <= self.CONFIDENCE_THRESHOLD <= 1.0:
            errors.append(f"Confidence threshold must be between 0.0 and 1.0, got: {self.CONFIDENCE_THRESHOLD}")
        
        # Validate tracking method
        valid_tracking_methods = ["bytetrack", "botsort", "custom"]
        if self.TRACKING_METHOD not in valid_tracking_methods:
            errors.append(f"Invalid tracking method: {self.TRACKING_METHOD}. Must be one of: {valid_tracking_methods}")
        
        # Validate device
        valid_devices = ["auto", "cpu", "cuda", "mps"]
        if self.DEVICE not in valid_devices:
            errors.append(f"Invalid device: {self.DEVICE}. Must be one of: {valid_devices}")
        
        # Validate detection format
        valid_formats = ["json", "csv", "txt"]
        if self.DETECTION_FORMAT not in valid_formats:
            errors.append(f"Invalid detection format: {self.DETECTION_FORMAT}. Must be one of: {valid_formats}")
        
        # Validate numeric values
        if self.MAX_DISAPPEARED < 0:
            errors.append(f"Max disappeared must be non-negative, got: {self.MAX_DISAPPEARED}")
        
        if self.CAMERA_BUFFER_SIZE <= 0:
            errors.append(f"Camera buffer size must be positive, got: {self.CAMERA_BUFFER_SIZE}")
        
        if self.FRAME_SKIP <= 0:
            errors.append(f"Frame skip must be positive, got: {self.FRAME_SKIP}")
        
        # Report errors
        if errors:
            for error in errors:
                logging.error(f"Configuration error: {error}")
            return False
        
        logging.info("Configuration validation passed")
        return True
    
    def __str__(self) -> str:
        """String representation of configuration."""
        config_dict = {
            'model_path': self.DEFAULT_MODEL_PATH,
            'confidence_threshold': self.CONFIDENCE_THRESHOLD,
            'device': self.DEVICE,
            'enable_tracking': self.ENABLE_TRACKING,
            'tracking_method': self.TRACKING_METHOD,
            'camera_index': self.DEFAULT_CAMERA_INDEX,
            'display_video': self.DISPLAY_VIDEO,
            'save_video': self.SAVE_VIDEO,
            'output_dir': self.OUTPUT_DIR
        }
        
        return f"Config({', '.join(f'{k}={v}' for k, v in config_dict.items())})"


# Global configuration instance
config = Config()
