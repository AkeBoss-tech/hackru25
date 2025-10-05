# Simple Multi-Camera Setup

## How it works:
- **One central server** - Does all the AI processing
- **Multiple camera scripts** - Just send video feeds to the server

## Setup:

### 1. Start the Central Server (on your main machine)
```bash
python3 start_server.py
```
This starts the main processing server at http://localhost:5002

### 2. Send Camera Feeds (Multiple Options)

#### Option A: Simple Camera Sender (Easiest)
```bash
python3 simple_camera_sender.py
```

**To change settings, edit these lines in `simple_camera_sender.py`:**
```python
SERVER_URL = "http://192.168.1.100:5002"  # Your main server IP
CLIENT_NAME = "Office_Camera"  # Name this camera
```

#### Option B: Network Camera Sender (Auto-Discovery)
```bash
# Auto-discover servers on your network
python3 network_camera_sender.py --discover

# Or connect directly to a specific server
python3 network_camera_sender.py --server http://192.168.1.100:5002 --name "Office_Camera"

# List available cameras first
python3 network_camera_sender.py --list-cameras
```

#### Option C: Camera Client (Professional)
```bash
# Using the provided shell script (recommended)
chmod +x start_camera_client.sh
./start_camera_client.sh

# Or run directly with options
python3 camera_client.py --server http://192.168.1.100:5002 --max-cameras 3 --quality 90
```

#### Option D: Network Camera Shell Script
```bash
# Pre-configured script with auto-discovery
chmod +x start_network_camera.sh
./start_network_camera.sh
```

### 3. View Everything
Open: http://localhost:5002/distributed

## Command Line Options

### Network Camera Sender Options:
```bash
python3 network_camera_sender.py [options]

Options:
  --server, -s URL        Server URL (e.g., http://192.168.1.100:5002)
  --name, -n NAME         Client name (e.g., Office_Camera)
  --camera, -c INDEX      Camera index (default: 0)
  --discover, -d          Discover servers on network
  --list-cameras, -l      List available cameras
```

### Camera Client Options:
```bash
python3 camera_client.py [options]

Options:
  --server URL            Main backend server URL (default: http://localhost:5002)
  --client-id ID          Unique client identifier
  --max-cameras NUM       Maximum cameras to discover (default: 5)
  --quality NUM           Streaming quality 1-100 (default: 80)
  --fps NUM               Target streaming FPS (default: 15)
  --discover-only         Only discover cameras and exit
```

## That's it!

- Each camera script just sends video to the central server
- The central server does all the AI processing (YOLO, face detection, etc.)
- View all cameras from one web interface
- Start/stop processing from the web interface

## For multiple cameras on the same machine:
- **Simple**: Run `simple_camera_sender.py` multiple times with different CLIENT_NAME values
- **Advanced**: Use `camera_client.py` with `--max-cameras` to handle multiple cameras in one process

## Troubleshooting:

### Camera Issues:
```bash
# Test what cameras are available
python3 network_camera_sender.py --list-cameras

# Test camera client discovery
python3 camera_client.py --discover-only
```

### Network Issues:
```bash
# Auto-discover servers
python3 network_camera_sender.py --discover

# Test server connection
curl http://192.168.1.100:5002/api/distributed/stats
```

### Performance Tuning:
```bash
# Lower quality for better performance
python3 camera_client.py --quality 60 --fps 10

# Higher quality for better detection
python3 camera_client.py --quality 90 --fps 20
```
