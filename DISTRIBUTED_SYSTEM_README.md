# Distributed Multi-Camera Surveillance System

This system allows you to deploy multiple camera clients on different machines that stream video feeds to a central backend server for processing and analysis.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Camera Client │    │   Camera Client │    │   Camera Client │
│   (Machine A)   │    │   (Machine B)   │    │   (Machine C)   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │      Video Streams   │                      │
          └──────────┬───────────┼──────────────────────┘
                     │           │
                     ▼           ▼
        ┌─────────────────────────────────────────────┐
        │         Main Backend Server                 │
        │  ┌─────────────────────────────────────────┐│
        │  │    Distributed Camera Manager           ││
        │  │  - Client Management                    ││
        │  │  - Frame Buffer Management              ││
        │  │  - Multi-Camera Processing              ││
        │  └─────────────────────────────────────────┘│
        │  ┌─────────────────────────────────────────┐│
        │  │    Video Processing Engine              ││
        │  │  - YOLO Object Detection                ││
        │  │  - Face Recognition                     ││
        │  │  - AI Analysis (Gemini)                 ││
        │  └─────────────────────────────────────────┘│
        └─────────────────┬───────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────────┐
        │           Web Frontend                      │
        │  - Multi-Camera Dashboard                   │
        │  - Real-time Processing Results             │
        │  - System Management                        │
        └─────────────────────────────────────────────┘
```

## Components

### 1. Main Backend Server
- **File**: `web_app/app.py`
- **Purpose**: Central processing hub that handles all video analysis
- **Features**:
  - Manages multiple camera clients
  - Processes video streams with YOLO detection
  - Provides REST API and WebSocket server
  - Handles face recognition and AI analysis

### 2. Camera Client Application
- **File**: `camera_client.py`
- **Purpose**: Lightweight application that runs on camera machines
- **Features**:
  - Discovers and manages local cameras
  - Streams video feeds to main server
  - Handles connection management and reconnection
  - Minimal processing (just video streaming)

### 3. Distributed Camera Manager
- **File**: `backend/distributed_camera_manager.py`
- **Purpose**: Manages multiple camera clients and their streams
- **Features**:
  - Client registration and health monitoring
  - Frame buffer management
  - Multi-camera processing coordination
  - Real-time video stream handling

### 4. Multi-Camera Web Interface
- **File**: `web_app/templates/distributed.html`
- **Purpose**: Dashboard for managing multiple camera feeds
- **Features**:
  - Grid view of all camera feeds
  - Individual camera controls
  - Real-time processing results
  - System statistics and monitoring

## Setup Instructions

### Prerequisites

1. **Main Server Machine**:
   - Python 3.8+
   - OpenCV, YOLO models, and all existing dependencies
   - Sufficient processing power for video analysis

2. **Camera Client Machines**:
   - Python 3.8+
   - OpenCV
   - Camera access
   - Network connectivity to main server

### Installation

1. **Clone the repository** (on all machines):
   ```bash
   git clone <your-repo-url>
   cd sentri
   ```

2. **Install dependencies** (on all machines):
   ```bash
   pip install -r requirements.txt
   ```

3. **Additional dependencies for camera clients**:
   ```bash
   pip install python-socketio
   ```

### Running the System

#### 1. Start the Main Backend Server

On your main processing machine:

```bash
cd web_app
python app.py
```

The server will start on `http://localhost:5002`

#### 2. Start Camera Clients

On each machine with cameras:

**Option A: Using the startup script**
```bash
./start_camera_client.sh
```

**Option B: Manual start**
```bash
python camera_client.py --server http://MAIN_SERVER_IP:5002 --client-id camera_machine_1
```

**Option C: With custom settings**
```bash
python camera_client.py \
    --server http://192.168.1.100:5002 \
    --client-id camera_office_door \
    --max-cameras 3 \
    --quality 90 \
    --fps 20
```

#### 3. Access the Web Interface

Open your browser and navigate to:
- **Standard Interface**: `http://localhost:5002/`
- **Distributed Interface**: `http://localhost:5002/distributed`

## Configuration

### Camera Client Options

```bash
python camera_client.py --help
```

Available options:
- `--server`: Main backend server URL (default: http://localhost:5002)
- `--client-id`: Unique identifier for this client
- `--max-cameras`: Maximum cameras to discover (default: 5)
- `--quality`: Streaming quality 1-100 (default: 80)
- `--fps`: Target streaming FPS (default: 15)
- `--discover-only`: Only discover cameras and exit

### Server Configuration

Edit `backend/config.py` to adjust:
- Model paths
- Processing parameters
- Detection thresholds
- Tracking settings

## Usage

### 1. Camera Discovery

When you start a camera client, it will automatically:
- Discover available cameras on the machine
- Test each camera for functionality
- Report camera properties (resolution, FPS, etc.)
- Register with the main server

### 2. Starting Streams

From the web interface:
1. Go to the **Distributed** tab
2. See all connected clients and their cameras
3. Click **Stream** to start video streaming
4. Click **Process** to start AI analysis

### 3. Monitoring

The distributed interface shows:
- **System Overview**: Total clients, cameras, active streams
- **Camera Grid**: Live feeds from all cameras
- **Individual Controls**: Start/stop streaming and processing per camera
- **Real-time Statistics**: Frames processed, detections, etc.

## API Endpoints

### Client Management
- `GET /api/distributed/clients` - Get all connected clients
- `GET /api/distributed/clients/<client_id>` - Get specific client info
- `GET /api/distributed/stats` - Get system statistics

### Processing Control
- `POST /api/distributed/start_processing` - Start processing a stream
- `POST /api/distributed/stop_processing` - Stop processing a stream
- `GET /api/distributed/processing` - Get processing status

### Maintenance
- `POST /api/distributed/cleanup` - Clean up inactive clients

## WebSocket Events

### From Camera Clients
- `client_register` - Register new client
- `camera_info` - Send camera information
- `camera_frame` - Send video frame

### To Camera Clients
- `start_streaming` - Start streaming camera
- `stop_streaming` - Stop streaming camera
- `update_streaming_settings` - Update quality/FPS

### To Web Interface
- `distributed_client_change` - Client status changes
- `distributed_frame_update` - New processed frames
- `distributed_detection_update` - New detections

## Troubleshooting

### Common Issues

1. **Camera client can't connect to server**
   - Check network connectivity
   - Verify server URL and port
   - Check firewall settings

2. **No cameras detected**
   - Ensure cameras are connected and not in use by other applications
   - Check camera permissions
   - Try running with `--discover-only` to test

3. **Poor video quality**
   - Adjust `--quality` parameter (higher = better quality)
   - Check network bandwidth
   - Reduce `--fps` if needed

4. **High CPU usage on main server**
   - Reduce number of concurrent streams
   - Lower processing confidence thresholds
   - Use more powerful hardware

### Logs

- **Main server logs**: Check console output from `app.py`
- **Camera client logs**: Check console output from `camera_client.py`
- **Browser console**: Check for JavaScript errors in web interface

## Performance Considerations

### Network Bandwidth
- Each camera stream can use 1-5 Mbps depending on quality settings
- Plan network capacity accordingly
- Consider using wired connections for better stability

### Processing Power
- Main server needs significant CPU/GPU for video processing
- Consider using GPU acceleration for YOLO models
- Monitor system resources during operation

### Storage
- Video processing generates temporary files
- Ensure sufficient disk space
- Consider implementing automatic cleanup

## Security Considerations

- The system currently runs without authentication
- Consider adding authentication for production use
- Use HTTPS in production environments
- Restrict network access to authorized machines only

## Extending the System

### Adding New Features
- **Custom Detection**: Modify `VideoProcessor` class
- **New Camera Types**: Extend `CameraHandler` class
- **Additional Clients**: Create new client types in `DistributedCameraManager`

### Integration
- **Database Storage**: Add database integration for event storage
- **Alert Systems**: Integrate with notification services
- **Cloud Storage**: Add cloud backup for important events

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs for error messages
3. Test individual components separately
4. Verify network connectivity and permissions

---

**Note**: This is a development system. For production deployment, consider adding authentication, encryption, and additional security measures.
