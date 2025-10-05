# Snapshot Analysis & Family Member Management Features

This document describes the enhanced snapshot analysis system that integrates sex offender detection and family member management with automatic snapshot processing.

## 🚨 **New Features**

### **1. Automatic Snapshot Analysis**
- **Every snapshot taken is automatically analyzed** for sex offenders and family members
- **Real-time detection** when snapshots are captured during object detection
- **Integrated with existing timeline system** - no additional setup required
- **Console logging** with detailed offender information

### **2. Sex Offender Detection on Snapshots**
- **Automatic detection** whenever a snapshot is captured
- **High-confidence alerts** with detailed offender information
- **Console output** with offender details:
  ```
  🚨 SEX OFFENDER DETECTED in snapshot event_123: 2 matches
  ```
- **Web interface alerts** for critical detections

### **3. Family Member Management System**
- **Add family members** with photos in the Settings tab
- **Upload photos** of family members for recognition
- **Capture current frame** button for live family member enrollment
- **Family member database** with persistent storage
- **Automatic recognition** in snapshots

### **4. Enhanced Web Interface**

#### **Settings Tab Enhancements:**
- **Sex Offender Detection Controls:**
  - Enable/disable continuous detection
  - Confidence threshold slider (0.1 - 1.0)
  - Detection interval slider (1-10 seconds)
  - Start/Stop detection buttons

- **Family Member Management:**
  - Add family member name and photo
  - Upload photos for recognition
  - Capture current frame for enrollment
  - View and remove family members
  - Refresh family member list

#### **Notifications Tab Enhancements:**
- **Sex Offender Alerts Section:**
  - Real-time alerts for detected sex offenders
  - Confidence scores and offender details
  - Timestamp information
  - Clear alerts functionality

- **Family Member Detection Section:**
  - Real-time notifications when family members are detected
  - Detection history
  - Clear detections functionality

## 🔧 **How It Works**

### **Automatic Snapshot Analysis Flow:**
1. **Object Detection** triggers snapshot capture
2. **Timeline Manager** saves snapshot to disk
3. **Snapshot Analysis Service** automatically analyzes the snapshot:
   - Detects faces in the image
   - Runs sex offender detection on each face
   - Checks for family member matches
   - Logs results to console
4. **Web Interface** receives real-time updates via WebSocket
5. **Alerts** are displayed for high-confidence matches

### **Console Output Example:**
```
🔍 Analyzing snapshot: timeline_snapshots/20241215_143025_event_123_annotated.jpg
🚨 SEX OFFENDER DETECTED in snapshot event_123: 1 matches
👨‍👩‍👧‍👦 FAMILY MEMBER detected in snapshot event_123: 1 matches
✅ Snapshot analysis complete: 1 sex offenders, 1 family members
```

## 🚀 **Usage Instructions**

### **1. Start the System**
```bash
# Start the web server
python web_app/app.py
```

### **2. Enable Sex Offender Detection**
1. Go to the **Settings** tab
2. Scroll to **Sex Offender Detection** section
3. Adjust confidence threshold (default: 0.3)
4. Set detection interval (default: 2 seconds)
5. Click **Start Detection**

### **3. Add Family Members**
1. Go to the **Settings** tab
2. Scroll to **Family Member Management** section
3. Enter family member name
4. Either:
   - Upload a photo file, OR
   - Click **Capture Current Frame** (requires video processing)
5. Click **Add**

### **4. Monitor Alerts**
1. Go to the **Notifications** tab
2. View **Sex Offender Alerts** for critical detections
3. View **Family Member Detection** for recognized family members
4. Use **Refresh** buttons to update displays

## 📊 **API Endpoints**

### **Snapshot Analysis**
- `POST /api/snapshot/analyze` - Analyze uploaded image
- `POST /api/snapshot/capture_family_photo` - Capture current frame
- `GET /api/snapshot/analysis/stats` - Get analysis statistics
- `POST /api/snapshot/analysis/settings` - Update analysis settings

### **Family Member Management**
- `GET /api/family/analysis/members` - Get all family members
- `POST /api/family/analysis/members` - Add family member
- `DELETE /api/family/analysis/members/<name>` - Remove family member

### **Sex Offender Detection**
- `POST /api/sex_offender_detection/start` - Start continuous detection
- `POST /api/sex_offender_detection/stop` - Stop detection
- `GET /api/sex_offender_detection/status` - Get detection status
- `GET /api/sex_offender_detection/stats` - Get detection statistics

## 🔄 **Real-time Updates**

The system provides real-time updates via WebSocket events:

### **Sex Offender Events:**
- `sex_offender_detection_update` - General detection updates
- `sex_offender_alert` - High-confidence alerts
- `sex_offender_detection_status` - Status changes

### **Family Member Events:**
- `family_member_detection` - Family member recognition

## 📁 **File Structure**

```
backend/
├── snapshot_analysis_service.py      # Main analysis service
├── continuous_sex_offender_detector.py # Continuous detection
├── timeline_manager.py               # Enhanced with analysis
└── improved_image_matcher.py         # Face recognition engine

web_app/
├── app.py                           # Enhanced with new API endpoints
├── templates/index.html             # Enhanced UI
└── static/js/app.js                 # Enhanced JavaScript

family_members/                      # Family member storage
├── family_members.json             # Family member database
└── photos/                         # Family member photos
```

## 🎯 **Configuration Options**

### **Detection Thresholds:**
- **Sex Offender Threshold**: 0.1 - 1.0 (default: 0.3)
- **Family Member Threshold**: 0.1 - 1.0 (default: 0.4)
- **Detection Interval**: 1 - 10 seconds (default: 2)

### **Alert Levels:**
- **CRITICAL**: Confidence > 0.8 (Red alerts)
- **HIGH**: Confidence > 0.7 (Red alerts)
- **MEDIUM**: Confidence > 0.5 (Yellow alerts)
- **LOW**: Confidence > 0.3 (Blue alerts)

## 🧪 **Testing**

### **Test Snapshot Analysis:**
```bash
# Test with uploaded image
curl -X POST http://localhost:5002/api/snapshot/analyze \
  -F "image=@test_image.jpg"
```

### **Test Family Member Management:**
```bash
# Add family member
curl -X POST http://localhost:5002/api/family/analysis/members \
  -F "name=John Doe" \
  -F "photo=@family_photo.jpg"
```

### **Test Sex Offender Detection:**
```bash
# Start detection
curl -X POST http://localhost:5002/api/sex_offender_detection/start \
  -H "Content-Type: application/json" \
  -d '{"camera_index": 0, "confidence_threshold": 0.3, "detection_interval": 2.0}'
```

## 🔒 **Security Considerations**

- **Data Privacy**: All analysis is performed locally
- **Family Photos**: Stored securely in local directory
- **Access Control**: Web interface should be secured in production
- **Logging**: Sensitive information should be filtered from logs

## 🚀 **Future Enhancements**

- **Face Recognition**: Implement actual face recognition for family members
- **Database Integration**: Store detection history in database
- **Mobile App**: Mobile interface for family member management
- **Email Alerts**: Email notifications for critical detections
- **Video Recording**: Automatic video recording when sex offenders detected

## 📞 **Support**

For issues or questions:
1. Check console logs for error messages
2. Verify camera and database setup
3. Test with provided API endpoints
4. Review configuration settings

---

**⚠️ Important**: This system is designed for security and safety applications. Ensure proper authorization and legal compliance when deploying in production environments.
