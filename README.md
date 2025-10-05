# Sentri

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

### AI Integration
- **Gemini AI Analysis**: Automatic brief reports for detected objects
- **Vector Database**: Semantic search through events and AI reports
- **Smart Search**: Find similar events using natural language queries
- **Cost-Effective**: Optimized prompts to minimize API usage

## 📁 Project Structure

```
sentri/
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
├── start_server.py         # Central processing server
├── simple_camera_sender.py # Simple camera sender script
├── camera_client.py        # Professional camera client
├── network_camera_sender.py # Network camera sender with discovery
├── start_camera_client.sh  # Camera client startup script
├── start_network_camera.sh # Network camera startup script
├── run_camera_sender.sh    # Legacy camera sender script
├── SIMPLE_SETUP.md         # Simple setup documentation
└── README.md              # This file
```

## 🛠 Installation

### 1. Clone and Setup

```bash
git clone <repository-url>
cd sentri
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

### 5. Gemini AI Setup (Optional)

```bash
# Copy the example environment file
cp gemini.env.example .env

# Edit .env and add your Gemini API key
# Get your API key from: https://makersuite.google.com/app/apikey
# The system will automatically use GEMINI_API_KEY from your .env file
```

### 6. Make Shell Scripts Executable

```bash
chmod +x start_camera_client.sh
chmod +x start_network_camera.sh
chmod +x run_camera_sender.sh
```

## 🚀 Quick Start

### Single Camera Systems

#### Option 1: Simple Camera Sender (Easiest)
For quick setup with minimal configuration:

```bash
# Start the central server (on your main machine)
python3 start_server.py

# Send camera feed (on any machine with camera)
python3 simple_camera_sender.py
```

**Configuration**: Edit these lines in `simple_camera_sender.py`:
```python
SERVER_URL = "http://192.168.1.100:5002"  # Your main server IP
CLIENT_NAME = "Office_Camera"  # Name this camera
```

#### Option 2: Network Camera Sender (Advanced)
For network discovery and multiple options:

```bash
# Auto-discover servers on network
python3 network_camera_sender.py --discover

# Connect to specific server
python3 network_camera_sender.py --server http://192.168.1.100:5002 --name "Office_Camera"

# List available cameras
python3 network_camera_sender.py --list-cameras

# Use specific camera index
python3 network_camera_sender.py --camera 1 --name "Security_Cam"
```

#### Option 3: Camera Client (Professional)
For advanced features and multiple camera support:

```bash
# Using shell script (recommended)
chmod +x start_camera_client.sh
./start_camera_client.sh

# Direct command with options
python3 camera_client.py --server http://192.168.1.100:5002 --max-cameras 3 --quality 90 --fps 20

# Discover cameras only
python3 camera_client.py --discover-only
```

#### Shell Scripts
Pre-configured startup scripts for easy deployment:

```bash
# Camera client with defaults
./start_camera_client.sh

# Network camera sender with auto-discovery
./start_network_camera.sh
```

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

### Distributed System

1. **Start central server**:
   ```bash
   python3 start_server.py
   ```

2. **Connect cameras** using any of the single camera options above

3. **View everything**: Open `http://localhost:5002/distributed`

## 📋 Shell Scripts Reference

### Available Shell Scripts

#### `start_camera_client.sh`
Professional camera client with comprehensive features:
```bash
./start_camera_client.sh
```
**Features:**
- Auto-discovers cameras (up to 5)
- Connects to main server via SocketIO
- Quality: 80, FPS: 15 (configurable)
- Handles multiple camera streams
- Automatic reconnection on network issues

#### `start_network_camera.sh`
Network camera sender with auto-discovery:
```bash
./start_network_camera.sh
```
**Features:**
- Auto-discovers servers on local network
- Installs dependencies if missing
- Simple HTTP-based streaming
- Works on any machine with Python 3

#### `run_camera_sender.sh`
Legacy camera sender script:
```bash
./run_camera_sender.sh
```

### Command Line Examples

#### Camera Discovery
```bash
# List all available cameras
python3 network_camera_sender.py --list-cameras

# Discover cameras with camera client
python3 camera_client.py --discover-only

# Test camera 0 specifically
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera 0:', cap.isOpened()); cap.release()"
```

#### Network Discovery
```bash
# Find all servers on network
python3 network_camera_sender.py --discover

# Test server connectivity
curl http://192.168.1.100:5002/api/distributed/stats

# Ping test
ping -c 3 192.168.1.100
```

#### Performance Tuning
```bash
# Low resource usage (good for older machines)
python3 camera_client.py --quality 60 --fps 10 --max-cameras 2

# High quality (good for detailed detection)
python3 camera_client.py --quality 95 --fps 25 --max-cameras 1

# Balanced settings (default)
python3 camera_client.py --quality 80 --fps 15 --max-cameras 3
```

#### Multiple Camera Setup
```bash
# Method 1: Multiple simple senders
python3 simple_camera_sender.py &  # Camera 1
# Edit CLIENT_NAME in script, then:
python3 simple_camera_sender.py &  # Camera 2

# Method 2: Single camera client (recommended)
python3 camera_client.py --max-cameras 4 --server http://192.168.1.100:5002
```

#### Troubleshooting Commands
```bash
# Check if server is running
curl -I http://localhost:5002

# Check camera permissions (Linux/Mac)
ls -la /dev/video*

# Test OpenCV camera access
python3 -c "import cv2; print('OpenCV version:', cv2.__version__)"

# Check network connectivity
python3 -c "import requests; print(requests.get('http://192.168.1.100:5002/api/distributed/stats').status_code)"
```

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