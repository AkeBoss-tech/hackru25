# Face Detection & Sex Offender Detection Features

## ✅ **What's Added:**

### 🎯 **Automatic Face Detection**
- Every camera frame is automatically analyzed for faces
- Uses your existing face detection system
- Runs in real-time on all distributed camera streams

### 🚨 **Sex Offender Detection**
- When a face is detected, automatically runs sex offender detection
- Uses your existing sex offender database
- Labels faces as: **Sex Offender**, **Not Sex Offender**, or **Family Member**

### 👨‍👩‍👧‍👦 **Family Member Management**
- **Settings Tab** in the web interface
- Upload photos of family members
- Add/remove family members
- Family members are automatically recognized and labeled

### 📊 **Detection Dashboard**
- **Detections Tab** shows all recent detections
- Color-coded alerts (Critical = Red, Warning = Yellow, Info = Blue)
- Real-time notifications for critical detections
- Shows which camera detected what

## 🎮 **How to Use:**

### 1. **Add Family Members**
1. Go to the **Settings** tab in the web interface
2. Enter a name and upload a photo
3. Click "Add Family Member"
4. Family members are automatically recognized

### 2. **View Detections**
1. Go to the **Detections** tab
2. See all recent face detections
3. Critical detections (sex offenders) show alerts

### 3. **Detection Types**
- 🔴 **SEX OFFENDER** - Critical alert, immediate notification
- 🟡 **NOT SEX OFFENDER** - Face detected but not in database
- 💙 **FAMILY MEMBER** - Recognized family member
- ⚪ **NO FACES** - No faces detected in frame

## 🔧 **Settings Available:**
- **Face Detection Confidence** - How sure the system needs to be to detect a face
- **Sex Offender Threshold** - Confidence level for sex offender matches
- **Enable/Disable** face detection and sex offender detection

## 🚀 **How It Works:**
1. Camera sends video frame to central server
2. Server detects faces in the frame
3. For each face found:
   - Check if it's a family member
   - If not family, check against sex offender database
   - Label the face appropriately
   - Send detection result to web interface
4. Web interface shows real-time alerts and detection history

## 📱 **Access the Features:**
- **Main Interface**: http://localhost:5002/distributed
- **Settings Tab**: Add/manage family members
- **Detections Tab**: View all face detection results

The system is now running with automatic face detection and sex offender checking on all your distributed camera streams!
