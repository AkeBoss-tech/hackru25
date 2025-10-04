# YOLOv8 Video Processing System

A comprehensive video processing system with YOLOv8 object detection, tracking, and a modern web interface.

## 🚀 Features

### Core Backend
- **Real-time Object Detection**: YOLOv8 integration with customizable confidence thresholds
- **Object Tracking**: Track objects across frames with unique IDs and trails
- **Multi-source Processing**: Camera streams, video files, and image processing
- **Advanced Analytics**: Comprehensive detection statistics and performance metrics
- **Modular Design**: Reusable components for different use cases

### Web Application
- **Modern Web Interface**: Responsive design with real-time updates
- **Live Camera Processing**: Process camera feeds with real-time object detection
- **Video Upload**: Upload and process video files (MP4, AVI, MOV)
- **Real-time Statistics**: Live detection counts, FPS, and processing metrics
- **WebSocket Communication**: Real-time video feed and detection updates
- **Mobile Friendly**: Works on desktop, tablet, and mobile devices

## 📁 Project Structure

```
hackru25/
├── backend/                 # Core video processing backend
│   ├── video_processor.py   # Main video processing class
│   ├── camera_handler.py    # Camera management utilities
│   ├── object_tracker.py    # Object tracking implementation
│   ├── detection_utils.py   # Detection utilities and visualization
│   ├── config.py           # Configuration management
│   └── __init__.py         # Backend module exports
├── web_app/                # Flask web application
│   ├── app.py              # Main Flask application
│   ├── run.py              # Startup script
│   ├── static/             # Static web assets
│   │   ├── css/style.css   # Custom styles
│   │   └── js/app.js       # Frontend JavaScript
│   ├── templates/          # HTML templates
│   │   └── index.html      # Main web interface
│   └── README.md           # Web app documentation
├── examples/               # Example scripts and demos
│   ├── web_app_demo.py     # Web app demo script
│   └── [other examples]    # Additional example scripts
├── tests/                  # Test suites
│   └── test_backend.py     # Backend tests
├── scripts/                # Utility scripts
├── sex-offenders/          # Data and images
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🛠 Installation

### 1. Clone and Setup

```bash
git clone <repository-url>
cd hackru25
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Download YOLOv8 Model

The YOLOv8 model will be automatically downloaded on first use, or you can manually download `yolov8n.pt` to the project root.

## 🚀 Quick Start

### Backend Usage

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

### Web Application

1. **Start the web server**:
   ```bash
   cd web_app
   python run.py
   ```

2. **Open your browser** and go to: `http://localhost:5000`

3. **Use the interface**:
   - Select camera or upload video
   - Adjust confidence threshold
   - Enable/disable tracking
   - Click "Start Processing"

## 📊 Features Overview

### Object Detection
- **80 COCO Classes**: Person, car, bicycle, laptop, etc.
- **Confidence Filtering**: Adjustable detection threshold
- **Real-time Processing**: Live camera and video processing
- **Batch Processing**: Process multiple files efficiently

### Object Tracking
- **Multiple Algorithms**: ByteTrack, BoTSORT, Custom tracking
- **Track Visualization**: Draw tracking trails and IDs
- **Track Statistics**: Duration, survival rates, class distribution
- **Configurable Parameters**: Max disappeared frames, tracking method

### Web Interface
- **Real-time Video Feed**: See processed video with bounding boxes
- **Live Statistics**: FPS, frame count, detection counts
- **Detection History**: Recent detections with confidence scores
- **Object Counts**: Real-time count of detected objects by class
- **Responsive Design**: Works on all device sizes

### API Endpoints
- `GET /api/cameras` - Get available cameras
- `POST /api/start_camera` - Start camera processing
- `POST /api/upload_video` - Upload and process video
- `POST /api/stop_processing` - Stop current processing
- `GET /api/status` - Get processing status
- `GET /api/config` - Get configuration

## 🧪 Testing

### Backend Tests
```bash
cd tests
python test_backend.py
```

### Web App Demo
```bash
cd examples
python web_app_demo.py
```

### Manual Testing
1. Start the web app: `cd web_app && python run.py`
2. Open browser: `http://localhost:5000`
3. Test camera processing and video uploads

## ⚙️ Configuration

### Backend Configuration
Modify `backend/config.py` or create custom configuration:

```python
# Model settings
DEFAULT_MODEL_PATH = "yolov8n.pt"
CONFIDENCE_THRESHOLD = 0.25
DEVICE = "auto"  # "auto", "cpu", "cuda", "mps"

# Tracking settings
ENABLE_TRACKING = True
TRACKING_METHOD = "bytetrack"
MAX_DISAPPEARED = 30

# Camera settings
DEFAULT_CAMERA_INDEX = 0
CAMERA_BUFFER_SIZE = 10
```

### Web App Configuration
The web app uses the same configuration system as the backend. Settings can be modified through the web interface or configuration files.

## 📈 Performance

### Optimization Tips
- **GPU Acceleration**: Use CUDA for faster processing
- **Lower Resolution**: Reduce camera resolution for better performance
- **Confidence Threshold**: Higher values = fewer detections = better performance
- **Disable Tracking**: Turn off tracking if not needed
- **Close Other Apps**: Free up system resources

### System Requirements
- **Python**: 3.8+
- **RAM**: 4GB+ recommended
- **GPU**: Optional, CUDA-compatible for acceleration
- **Camera**: USB camera or built-in webcam
- **Browser**: Chrome 80+, Firefox 75+, Safari 13+, Edge 80+

## 🔧 Troubleshooting

### Common Issues

1. **Camera Not Found**
   - Check camera permissions
   - Ensure camera is not used by other apps
   - Try different camera indices

2. **Model Loading Issues**
   - Verify model file exists
   - Check PyTorch installation
   - Ensure sufficient disk space

3. **Web App Connection Issues**
   - Check firewall settings
   - Ensure port 5000 is available
   - Try refreshing the browser

4. **Performance Issues**
   - Reduce confidence threshold
   - Disable tracking if not needed
   - Use smaller model (yolov8n.pt)
   - Enable GPU acceleration

### Debug Mode
Enable debug logging for detailed information:
```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

## 🚀 Production Deployment

### Web Application
1. Set `debug=False` in `app.py`
2. Use production WSGI server (Gunicorn, uWSGI)
3. Configure reverse proxy (Nginx)
4. Set up SSL certificates
5. Implement proper logging and monitoring

### Backend Integration
The backend can be integrated into other applications:
```python
from backend import VideoProcessor, CameraHandler, ObjectTracker
```

## 📝 Examples

### Basic Camera Processing
```python
from backend import VideoProcessor

processor = VideoProcessor()
stats = processor.process_camera_stream(camera_index=0, display=True)
```

### Video File Processing
```python
processor = VideoProcessor()
stats = processor.process_video_file(
    video_path="input.mp4",
    output_path="output.mp4",
    save_video=True
)
```

### Custom Callbacks
```python
def on_detection(detections, frame, frame_number):
    if detections:
        print(f"Frame {frame_number}: {len(detections)} objects detected")

processor.set_detection_callback(on_detection)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the examples
3. Check the logs for error messages
4. Create an issue with detailed information

## 🎯 Use Cases

- **Security Monitoring**: Real-time surveillance with object detection
- **Traffic Analysis**: Vehicle and pedestrian counting
- **Retail Analytics**: Customer behavior analysis
- **Sports Analysis**: Player and ball tracking
- **Educational**: Computer vision learning and experimentation
- **Research**: Object detection and tracking research

---

**Built with ❤️ using YOLOv8, Flask, and modern web technologies**