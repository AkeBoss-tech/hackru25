# 🌐 Network Multi-Camera Setup Guide

## ✅ **How to Connect Multiple Computers to the Same Distributed Interface**

### 🎯 **Overview:**
- **One Central Server**: Your main computer runs the processing server
- **Multiple Camera Clients**: Other computers send their camera feeds to the server
- **Unified Dashboard**: View all cameras from any computer on the network

---

## 🚀 **Step 1: Setup the Central Server**

### **On Your Main Computer (Server):**

1. **Find your IP address:**
   ```bash
   # On Mac/Linux:
   ifconfig | grep "inet " | grep -v 127.0.0.1
   
   # On Windows:
   ipconfig | findstr "IPv4"
   ```

2. **Start the server:**
   ```bash
   ./start_server.py
   # or
   source venv/bin/activate && cd web_app && python3 app.py
   ```

3. **Access the dashboard:**
   - **Local**: http://localhost:5002/distributed
   - **Network**: http://YOUR_IP:5002/distributed (e.g., http://192.168.1.100:5002/distributed)

---

## 📱 **Step 2: Setup Camera Client Computers**

### **On Each Camera Computer:**

1. **Copy the camera sender script:**
   ```bash
   # Copy network_camera_sender.py to the other computer
   # You can download it from your main computer or copy via USB/network
   ```

2. **Install Python dependencies:**
   ```bash
   pip3 install opencv-python requests
   ```

3. **Discover and connect to your server:**
   ```bash
   # Auto-discover servers on your network:
   python3 network_camera_sender.py --discover
   
   # Or manually specify server:
   python3 network_camera_sender.py --server http://192.168.1.100:5002 --name "Office_Camera"
   ```

4. **List available cameras:**
   ```bash
   python3 network_camera_sender.py --list-cameras
   ```

---

## 🎮 **Step 3: Connect Multiple Cameras**

### **Example Commands for Different Computers:**

**Computer 1 (Office):**
```bash
python3 network_camera_sender.py --server http://192.168.1.100:5002 --name "Office_Camera" --camera 0
```

**Computer 2 (Entrance):**
```bash
python3 network_camera_sender.py --server http://192.168.1.100:5002 --name "Entrance_Camera" --camera 0
```

**Computer 3 (Backyard):**
```bash
python3 network_camera_sender.py --server http://192.168.1.100:5002 --name "Backyard_Camera" --camera 0
```

---

## 📊 **Step 4: View All Cameras**

### **From Any Computer on the Network:**
1. Open browser
2. Go to: `http://YOUR_SERVER_IP:5002/distributed`
3. See all connected cameras in the grid
4. Each camera shows live feed + face detection results

---

## 🔧 **Advanced Options**

### **Camera Sender Options:**
```bash
# Basic usage:
python3 network_camera_sender.py

# With options:
python3 network_camera_sender.py \
  --server http://192.168.1.100:5002 \
  --name "My_Camera" \
  --camera 0 \
  --discover

# Available options:
--server, -s    Server URL (e.g., http://192.168.1.100:5002)
--name, -n      Client name (e.g., Office_Camera)
--camera, -c    Camera index (default: 0)
--discover, -d  Auto-discover servers on network
--list-cameras, -l  List available cameras
```

### **Server Configuration:**
The server automatically accepts connections from any computer on the network.

---

## 🌍 **Network Requirements**

### **Firewall Settings:**
- **Port 5002** must be open on the server computer
- **HTTP traffic** must be allowed

### **Network Setup:**
- All computers must be on the **same network** (WiFi or Ethernet)
- Server computer needs a **static IP** or **known IP address**
- **No special network configuration** required

---

## 🎯 **Quick Start Commands**

### **1. Find Your Server IP:**
```bash
# Mac/Linux:
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows:
ipconfig | findstr "IPv4"
```

### **2. Start Server:**
```bash
./start_server.py
```

### **3. Connect Camera:**
```bash
# Auto-discover:
python3 network_camera_sender.py --discover

# Manual:
python3 network_camera_sender.py --server http://YOUR_IP:5002 --name "Camera_1"
```

### **4. View Dashboard:**
```
http://YOUR_IP:5002/distributed
```

---

## 🚨 **Troubleshooting**

### **Can't Find Server:**
- Check firewall settings
- Ensure server is running on port 5002
- Verify computers are on same network

### **Camera Not Working:**
- Run `--list-cameras` to see available cameras
- Try different camera index with `--camera 1`, `--camera 2`, etc.
- Check if camera is being used by another application

### **Connection Issues:**
- Ping the server IP: `ping 192.168.1.100`
- Test server access: `curl http://192.168.1.100:5002/api/distributed/stats`

---

## 📱 **Mobile Access**

### **View from Phone/Tablet:**
1. Connect phone to same WiFi network
2. Open browser
3. Go to: `http://YOUR_SERVER_IP:5002/distributed`
4. View all cameras with touch controls

---

## 🎉 **What You Get:**

- **Multiple cameras** from different computers
- **Real-time face detection** on all streams
- **Sex offender alerts** across all cameras
- **Family member recognition** system-wide
- **Unified dashboard** accessible from any device
- **Remote monitoring** from anywhere on the network

The system now supports unlimited camera computers connected to one central processing server!
