# Distributed Multi-Camera System - WORKING!

## ✅ What's Working:
- **Central Server**: Running at http://localhost:5002
- **Multi-Camera Dashboard**: http://localhost:5002/distributed
- **Simple Camera Sender**: Just run `./run_camera_sender.sh`

## 🚀 How to Use:

### 1. Start the Central Server (already running)
```bash
# Server is already running at http://localhost:5002
# You can see it in your terminal logs
```

### 2. Send Camera Feeds
```bash
# On any machine with a camera:
./run_camera_sender.sh
```

### 3. View Everything
Open: http://localhost:5002/distributed

## 🎯 What You Get:
- **One central server** that does all the AI processing
- **Multiple camera scripts** that just send video feeds
- **Web dashboard** to see all cameras and control processing
- **All your existing features**: YOLO detection, face recognition, etc.

## 📝 To Customize:
Edit `simple_camera_sender.py`:
```python
SERVER_URL = "http://YOUR_SERVER_IP:5002"  # Your main server
CLIENT_NAME = "Office_Camera"  # Name this camera
```

## 🔧 That's It!
- Run `./run_camera_sender.sh` on any machine with a camera
- Each script sends video to your central server
- View and control everything from the web dashboard
- All AI processing happens on the central server

The system is working! The server is running and ready to receive camera feeds.
