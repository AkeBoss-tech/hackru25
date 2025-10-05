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

### 2. Send Camera Feeds (on any machine with a camera)
```bash
python3 simple_camera_sender.py
```

**To change settings, edit these lines in `simple_camera_sender.py`:**
```python
SERVER_URL = "http://192.168.1.100:5002"  # Your main server IP
CLIENT_NAME = "Office_Camera"  # Name this camera
```

### 3. View Everything
Open: http://localhost:5002/distributed

## That's it!

- Each camera script just sends video to the central server
- The central server does all the AI processing (YOLO, face detection, etc.)
- View all cameras from one web interface
- Start/stop processing from the web interface

## For multiple cameras on the same machine:
Just run `simple_camera_sender.py` multiple times with different CLIENT_NAME values.
