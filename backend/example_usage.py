#!/usr/bin/env python3
"""
Example usage script for the video processing backend.
Demonstrates various features and use cases.
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from video_processor import VideoProcessor
from camera_handler import CameraHandler
from object_tracker import ObjectTracker
from detection_utils import DetectionUtils
from config import Config


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('video_processing.log')
        ]
    )


def example_camera_stream():
    """Example: Process live camera stream."""
    print("\n🎥 Example: Live Camera Stream Processing")
    print("=" * 50)
    
    # Initialize video processor
    processor = VideoProcessor(
        model_path="yolov8n.pt",
        confidence_threshold=0.25,
        enable_tracking=True
    )
    
    # Set up detection callback
    def on_detection(detections, frame, frame_number):
        if detections:
            print(f"🔍 Frame {frame_number}: {len(detections)} objects detected")
            for detection in detections:
                print(f"  - {detection['class_name']} (conf: {detection['confidence']:.2f}, track: {detection.get('track_id', 'N/A')})")
    
    processor.set_detection_callback(on_detection)
    
    # Process camera stream
    try:
        stats = processor.process_camera_stream(
            camera_index=0,
            display=True,
            max_frames=300  # Process for 10 seconds at 30 FPS
        )
        
        print(f"\n📊 Processing completed:")
        print(f"  - Frames processed: {stats['processed_frames']}")
        print(f"  - Total detections: {stats['total_detections']}")
        print(f"  - Average FPS: {stats['fps_actual']:.2f}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Processing stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")


def example_video_file():
    """Example: Process video file."""
    print("\n🎬 Example: Video File Processing")
    print("=" * 50)
    
    # Check if video file exists
    video_path = "sample_video.mp4"
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        print("Please provide a video file or update the path in the script")
        return
    
    # Initialize video processor
    processor = VideoProcessor(
        model_path="yolov8n.pt",
        confidence_threshold=0.3,
        enable_tracking=True
    )
    
    # Process video file
    try:
        stats = processor.process_video_file(
            video_path=video_path,
            output_path="output_processed.mp4",
            display=True,
            save_video=True
        )
        
        print(f"\n📊 Video processing completed:")
        print(f"  - Total frames: {stats['total_frames']}")
        print(f"  - Processed frames: {stats['processed_frames']}")
        print(f"  - Total detections: {stats['total_detections']}")
        print(f"  - Processing time: {stats['processing_time']:.2f}s")
        print(f"  - Average FPS: {stats['fps_actual']:.2f}")
        
        if stats['detection_counts']:
            print(f"  - Object counts:")
            for class_name, count in stats['detection_counts'].items():
                print(f"    * {class_name}: {count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_camera_discovery():
    """Example: Discover and test cameras."""
    print("\n📷 Example: Camera Discovery")
    print("=" * 50)
    
    # Initialize camera handler
    camera_handler = CameraHandler()
    
    # Discover cameras
    working_cameras = camera_handler.discover_cameras(max_cameras=5)
    
    if working_cameras:
        print(f"✓ Found {len(working_cameras)} working cameras: {working_cameras}")
        
        # Test each camera
        for camera_index in working_cameras:
            print(f"\nTesting camera {camera_index}...")
            
            if camera_handler.open_camera(camera_index):
                # Get camera properties
                properties = camera_handler.get_camera_properties(camera_index)
                print(f"  Properties: {properties}")
                
                # Test frame capture
                if camera_handler.start_capture(camera_index):
                    import time
                    time.sleep(2)  # Capture for 2 seconds
                    
                    frame = camera_handler.get_latest_frame(camera_index)
                    if frame is not None:
                        print(f"  ✓ Successfully captured frame: {frame.shape}")
                    else:
                        print(f"  ✗ Failed to capture frame")
                    
                    camera_handler.stop_capture(camera_index)
                
                camera_handler.close_camera(camera_index)
    else:
        print("❌ No working cameras found")


def example_detection_analysis():
    """Example: Advanced detection analysis."""
    print("\n🔍 Example: Detection Analysis")
    print("=" * 50)
    
    # Initialize detection utils
    detection_utils = DetectionUtils()
    
    # Initialize video processor
    processor = VideoProcessor(
        model_path="yolov8n.pt",
        confidence_threshold=0.25,
        enable_tracking=False  # Disable tracking for this example
    )
    
    # Collect detections from camera stream
    all_detections = []
    
    def collect_detections(detections, frame, frame_number):
        if detections:
            all_detections.extend(detections)
            print(f"Frame {frame_number}: Collected {len(detections)} detections")
    
    processor.set_detection_callback(collect_detections)
    
    try:
        # Process for a short time to collect data
        stats = processor.process_camera_stream(
            camera_index=0,
            display=False,  # Don't display for analysis
            max_frames=60  # 2 seconds at 30 FPS
        )
        
        if all_detections:
            print(f"\n📊 Analysis Results:")
            print(f"  - Total detections collected: {len(all_detections)}")
            
            # Calculate metrics
            metrics = detection_utils.calculate_detection_metrics(all_detections)
            print(f"  - Average confidence: {metrics['avg_confidence']:.3f}")
            print(f"  - Class distribution: {metrics['class_distribution']}")
            print(f"  - Size distribution: {metrics['size_distribution']}")
            
            # Filter detections
            high_conf_detections = detection_utils.filter_detections(
                all_detections,
                min_confidence=0.5,
                min_area=1000
            )
            print(f"  - High confidence detections (>0.5): {len(high_conf_detections)}")
            
            # Export detections
            detection_utils.export_detections(
                all_detections,
                "detections_analysis.json",
                format="json"
            )
            print(f"  - Detections exported to: detections_analysis.json")
            
            # Get statistics
            stats = detection_utils.get_detection_statistics()
            print(f"  - Detection statistics: {stats}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_tracking_analysis():
    """Example: Object tracking analysis."""
    print("\n🎯 Example: Object Tracking Analysis")
    print("=" * 50)
    
    # Initialize video processor with tracking
    processor = VideoProcessor(
        model_path="yolov8n.pt",
        confidence_threshold=0.25,
        enable_tracking=True,
        tracking_method="custom"
    )
    
    # Track statistics
    track_stats = {
        'total_tracks': 0,
        'track_durations': [],
        'class_tracks': {}
    }
    
    def analyze_tracks(detections, frame, frame_number):
        if detections:
            for detection in detections:
                track_id = detection.get('track_id')
                if track_id:
                    track_stats['total_tracks'] = max(track_stats['total_tracks'], track_id)
                    
                    class_name = detection['class_name']
                    if class_name not in track_stats['class_tracks']:
                        track_stats['class_tracks'][class_name] = set()
                    track_stats['class_tracks'][class_name].add(track_id)
    
    processor.set_detection_callback(analyze_tracks)
    
    try:
        # Process camera stream with tracking
        stats = processor.process_camera_stream(
            camera_index=0,
            display=True,
            max_frames=300  # 10 seconds
        )
        
        print(f"\n📊 Tracking Analysis Results:")
        print(f"  - Total unique tracks: {track_stats['total_tracks']}")
        print(f"  - Tracks by class:")
        for class_name, tracks in track_stats['class_tracks'].items():
            print(f"    * {class_name}: {len(tracks)} tracks")
        
        # Get tracking statistics from processor
        if processor.tracker:
            tracking_stats = processor.tracker.get_tracking_statistics()
            print(f"  - Tracking statistics: {tracking_stats}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_configuration():
    """Example: Configuration management."""
    print("\n⚙️  Example: Configuration Management")
    print("=" * 50)
    
    # Load default configuration
    config = Config()
    
    print(f"Default configuration: {config}")
    
    # Validate configuration
    if config.validate():
        print("✓ Configuration is valid")
    else:
        print("❌ Configuration validation failed")
    
    # Save configuration to file
    config_path = "example_config.json"
    if config.to_file(config_path):
        print(f"✓ Configuration saved to {config_path}")
    
    # Load configuration from file
    loaded_config = Config.from_file(config_path)
    print(f"Loaded configuration: {loaded_config}")
    
    # Get specific configuration sections
    model_config = config.get_model_config()
    tracking_config = config.get_tracking_config()
    camera_config = config.get_camera_config()
    
    print(f"Model config: {model_config}")
    print(f"Tracking config: {tracking_config}")
    print(f"Camera config: {camera_config}")


def main():
    """Main function to run examples."""
    parser = argparse.ArgumentParser(description='Video Processing Backend Examples')
    parser.add_argument(
        '--example',
        choices=['camera', 'video', 'discovery', 'analysis', 'tracking', 'config', 'all'],
        default='all',
        help='Example to run (default: all)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='yolov8n.pt',
        help='Path to YOLOv8 model file'
    )
    parser.add_argument(
        '--confidence',
        type=float,
        default=0.25,
        help='Confidence threshold for detections'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    print("🚀 Video Processing Backend Examples")
    print("=" * 60)
    
    # Update model path if provided
    if args.model != 'yolov8n.pt':
        Config.DEFAULT_MODEL_PATH = args.model
    if args.confidence != 0.25:
        Config.CONFIDENCE_THRESHOLD = args.confidence
    
    try:
        if args.example == 'camera' or args.example == 'all':
            example_camera_stream()
        
        if args.example == 'video' or args.example == 'all':
            example_video_file()
        
        if args.example == 'discovery' or args.example == 'all':
            example_camera_discovery()
        
        if args.example == 'analysis' or args.example == 'all':
            example_detection_analysis()
        
        if args.example == 'tracking' or args.example == 'all':
            example_tracking_analysis()
        
        if args.example == 'config' or args.example == 'all':
            example_configuration()
        
        print("\n✅ All examples completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        logging.exception("Exception in main")


if __name__ == '__main__':
    main()
