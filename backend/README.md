# Video Processing Backend

A comprehensive Python backend for processing videos and camera streams using YOLOv8 for object detection and tracking.

## Features

- 🎥 **Real-time Camera Stream Processing**: Process live camera feeds with object detection
- 🎬 **Video File Processing**: Process video files with detection and tracking
- 🎯 **Object Tracking**: Track objects across frames using multiple algorithms
- 📊 **Advanced Analytics**: Comprehensive detection statistics and analysis
- 🔧 **Modular Design**: Reusable components for different use cases
- ⚙️ **Configurable**: Extensive configuration options for all components
- 📝 **Comprehensive Logging**: Detailed logging and print statements
- 🚀 **High Performance**: Optimized for real-time processing

## Components

### Core Classes

- **`VideoProcessor`**: Main class for video and camera stream processing
- **`CameraHandler`**: Advanced camera management and stream handling
- **`ObjectTracker`**: Object tracking with multiple algorithms
- **`DetectionUtils`**: Utility functions for detection processing and visualization
- **`Config`**: Configuration management system

### Key Features

#### VideoProcessor
- Real-time object detection with YOLOv8
- Camera stream and video file processing
- Object tracking integration
- Customizable callbacks for detections and frames
- Comprehensive statistics and logging

#### CameraHandler
- Multi-camera support
- Threaded frame capture
- Camera discovery and testing
- Stream quality management
- Error handling and recovery

#### ObjectTracker
- Multiple tracking algorithms (ByteTrack, BoTSORT, Custom)
- Track visualization with trails
- Track statistics and analysis
- Configurable tracking parameters

#### DetectionUtils
- Detection extraction and formatting
- Advanced filtering and analysis
- Visualization utilities
- Export/import functionality
- Performance metrics

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Download YOLOv8 Model** (if not already present):
   ```bash
   # The model will be automatically downloaded on first use
   # Or manually download yolov8n.pt to the project root
   ```

## Quick Start

### Basic Camera Stream Processing

```python
from backend import VideoProcessor

# Initialize processor
processor = VideoProcessor(
    model_path="yolov8n.pt",
    confidence_threshold=0.25,
    enable_tracking=True
)

# Process camera stream
stats = processor.process_camera_stream(
    camera_index=0,
    display=True
)

print(f"Processed {stats['processed_frames']} frames")
print(f"Total detections: {stats['total_detections']}")
```

### Video File Processing

```python
from backend import VideoProcessor

# Initialize processor
processor = VideoProcessor(
    model_path="yolov8n.pt",
    confidence_threshold=0.3,
    enable_tracking=True
)

# Process video file
stats = processor.process_video_file(
    video_path="input_video.mp4",
    output_path="output_video.mp4",
    display=True,
    save_video=True
)
```

### Advanced Usage with Callbacks

```python
from backend import VideoProcessor

def on_detection(detections, frame, frame_number):
    """Callback for when objects are detected."""
    if detections:
        print(f"Frame {frame_number}: {len(detections)} objects detected")
        for detection in detections:
            print(f"  - {detection['class_name']} (conf: {detection['confidence']:.2f})")

def on_frame(processed_frame, frame_number):
    """Callback for each processed frame."""
    # Custom processing of the frame
    pass

# Initialize processor with callbacks
processor = VideoProcessor(
    model_path="yolov8n.pt",
    confidence_threshold=0.25,
    enable_tracking=True
)

processor.set_detection_callback(on_detection)
processor.set_frame_callback(on_frame)

# Process stream
stats = processor.process_camera_stream(camera_index=0, display=True)
```

## Configuration

### Using Configuration File

```python
from backend import Config

# Load configuration from file
config = Config.from_file("config.json")

# Use configuration
processor = VideoProcessor(
    model_path=config.DEFAULT_MODEL_PATH,
    confidence_threshold=config.CONFIDENCE_THRESHOLD,
    enable_tracking=config.ENABLE_TRACKING
)
```

### Configuration Options

```python
# Model settings
DEFAULT_MODEL_PATH = "yolov8n.pt"
CONFIDENCE_THRESHOLD = 0.25
DEVICE = "auto"  # "auto", "cpu", "cuda", "mps"

# Tracking settings
ENABLE_TRACKING = True
TRACKING_METHOD = "bytetrack"  # "bytetrack", "botsort", "custom"
MAX_DISAPPEARED = 30

# Camera settings
DEFAULT_CAMERA_INDEX = 0
CAMERA_BUFFER_SIZE = 10

# Processing settings
MAX_FRAMES = None  # None for unlimited
DISPLAY_VIDEO = True
SAVE_VIDEO = False
```

## Examples

### Run All Examples

```bash
cd backend
python example_usage.py --example all
```

### Run Specific Examples

```bash
# Camera stream processing
python example_usage.py --example camera

# Video file processing
python example_usage.py --example video

# Camera discovery
python example_usage.py --example discovery

# Detection analysis
python example_usage.py --example analysis

# Tracking analysis
python example_usage.py --example tracking

# Configuration management
python example_usage.py --example config
```

### Custom Model and Confidence

```bash
python example_usage.py --model yolov8s.pt --confidence 0.3
```

## API Reference

### VideoProcessor

#### Constructor
```python
VideoProcessor(
    model_path: str = "yolov8n.pt",
    confidence_threshold: float = 0.25,
    device: str = "auto",
    enable_tracking: bool = True,
    tracking_method: str = "bytetrack"
)
```

#### Methods
- `process_camera_stream(camera_index, display, max_frames)` - Process live camera stream
- `process_video_file(video_path, output_path, display, save_video)` - Process video file
- `set_detection_callback(callback)` - Set detection callback function
- `set_frame_callback(callback)` - Set frame callback function
- `stop_processing()` - Stop current processing
- `get_model_info()` - Get model information

### CameraHandler

#### Constructor
```python
CameraHandler(buffer_size: int = 10)
```

#### Methods
- `discover_cameras(max_cameras)` - Discover available cameras
- `open_camera(camera_index, width, height, fps)` - Open camera with settings
- `start_capture(camera_index)` - Start capturing frames
- `get_latest_frame(camera_index)` - Get latest frame
- `stop_capture(camera_index)` - Stop capturing
- `close_camera(camera_index)` - Close camera

### ObjectTracker

#### Constructor
```python
ObjectTracker(method: str = "bytetrack", max_disappeared: int = 30)
```

#### Methods
- `update(detections, frame)` - Update tracks with new detections
- `draw_tracks(frame)` - Draw track visualization
- `get_track_info(track_id)` - Get track information
- `get_tracking_statistics()` - Get tracking statistics
- `reset_tracking()` - Reset all tracking data

### DetectionUtils

#### Methods
- `extract_detections(result, class_names)` - Extract detections from YOLOv8 result
- `filter_detections(detections, min_confidence, min_area, target_classes)` - Filter detections
- `draw_detections(frame, detections, show_confidence, show_class)` - Draw detections
- `calculate_detection_metrics(detections)` - Calculate detection metrics
- `export_detections(detections, filepath, format)` - Export detections
- `get_detection_statistics()` - Get detection statistics

## Output and Logging

### Console Output
The system provides comprehensive console output including:
- Object detection information with class names and confidence scores
- Tracking information with track IDs
- Processing statistics (FPS, frame count, detection counts)
- Error messages and warnings

### Log Files
- Detailed logging to `video_processing.log`
- Configurable log levels and formats
- Separate log files for different components

### Detection Data
- JSON, CSV, or TXT format export
- Comprehensive detection metadata
- Track information and statistics

## Performance Optimization

### GPU Acceleration
- Automatic GPU detection and usage
- CUDA and MPS (Apple Silicon) support
- Configurable device selection

### Memory Management
- Efficient frame buffering
- Configurable buffer sizes
- Automatic cleanup and resource management

### Processing Optimization
- Configurable frame skipping
- Batch processing support
- Multi-threaded camera handling

## Troubleshooting

### Common Issues

1. **Camera Not Found**:
   - Check camera permissions
   - Try different camera indices (0, 1, 2)
   - Ensure camera is not used by other applications

2. **Model Loading Issues**:
   - Verify model file exists
   - Check PyTorch installation
   - Ensure sufficient disk space

3. **Performance Issues**:
   - Reduce confidence threshold
   - Disable tracking if not needed
   - Use smaller model (yolov8n.pt)
   - Enable GPU acceleration

4. **Memory Issues**:
   - Reduce buffer sizes
   - Process fewer frames
   - Close other applications

### Debug Mode
Enable debug logging for detailed information:
```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the examples
3. Check the logs for error messages
4. Create an issue with detailed information

## Changelog

### Version 1.0.0
- Initial release
- YOLOv8 integration
- Camera stream processing
- Object tracking
- Comprehensive utilities
- Configuration management
- Example usage scripts
