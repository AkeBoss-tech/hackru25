# Interface Integration Guide

## ✅ **How the Two Interfaces Connect:**

### 🎯 **Navigation Between Interfaces**
Both interfaces now have a **"System Views"** dropdown in the top navigation:

**Main Interface (Single Camera):**
- Access at: http://localhost:5002/
- Dropdown option: "Multi-Camera Dashboard" → Takes you to distributed interface

**Distributed Interface (Multi-Camera):**
- Access at: http://localhost:5002/distributed  
- Dropdown option: "Single Camera View" → Takes you to main interface

### 📊 **Status Integration**
The **main interface** now shows distributed camera status:

**In the Settings Panel:**
- **"Distributed Cameras"** card shows:
  - Number of active camera clients
  - Total cameras connected
  - Frames processed
  - Detections found
  - Quick link to open multi-camera dashboard

### 🔄 **Shared Data & Processing**
Both interfaces share the same backend:
- **Same face detection system**
- **Same sex offender database** 
- **Same family member database**
- **Same AI processing** (Gemini reports)
- **Same detection results**

### 🎮 **How to Use Both Together:**

#### **Scenario 1: Monitor Everything**
1. **Main Interface**: Use for detailed single camera analysis
2. **Distributed Interface**: Use for overview of all cameras + face detection alerts
3. **Switch between them** using the dropdown navigation

#### **Scenario 2: Setup & Control**
1. **Distributed Interface**: Add family members in Settings tab
2. **Main Interface**: Process individual videos with those same family members recognized
3. **Both interfaces** will show the same detection results

#### **Scenario 3: Multi-Camera Operations**
1. **Distributed Interface**: Start processing on all connected cameras
2. **Main Interface**: Monitor detailed results for specific streams
3. **Both interfaces** show real-time updates

### 🚀 **Quick Start Workflow:**

1. **Start the server**: Your server is already running at http://localhost:5002
2. **Connect cameras**: Run `./run_camera_sender.sh` on camera machines
3. **Main interface**: http://localhost:5002/ (single camera focus)
4. **Distributed interface**: http://localhost:5002/distributed (multi-camera + face detection)
5. **Switch between them**: Use the "System Views" dropdown

### 📱 **What You See:**

**Main Interface Shows:**
- Single camera/video processing
- Detailed object detection results
- Timeline of events
- Gemini AI reports
- **NEW**: Distributed camera status widget

**Distributed Interface Shows:**
- Multi-camera grid view
- Face detection results
- Sex offender alerts
- Family member management
- **NEW**: Navigation back to main interface

### 🔧 **Technical Integration:**
- **Shared backend**: Both interfaces use the same Flask app
- **Shared data**: Same databases and processing systems
- **Real-time sync**: Both interfaces update in real-time
- **Unified navigation**: Easy switching between views

The interfaces are now fully connected and work together seamlessly!
