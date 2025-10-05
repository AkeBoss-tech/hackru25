# Backend API Endpoints Documentation

This document lists all available API endpoints in the HackRU25 security surveillance system backend.

## 🏠 Main Application

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Main page (serves index.html) |

## 🎥 Camera Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/cameras` | Get available cameras |
| `POST` | `/api/start_camera` | Start camera processing |
| `POST` | `/api/stop_processing` | Stop current processing |

## 📁 Video Upload & Processing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload_video` | Handle video file upload |
| `GET` | `/api/status` | Get current processing status |
| `GET` | `/api/config` | Get current configuration |

## 🔍 Detection Classes

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/classes` | Get available detection class sets |

## 📊 Timeline Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/timeline/events` | Get timeline events |
| `GET` | `/api/timeline/events/<event_id>` | Get specific timeline event |
| `GET` | `/api/timeline/snapshots/<path:snapshot_path>` | Get timeline snapshot image |
| `GET` | `/api/timeline/snapshots/<path:snapshot_path>/raw` | Get raw timeline snapshot |
| `GET` | `/api/timeline/statistics` | Get timeline statistics |
| `POST` | `/api/timeline/clear` | Clear all timeline events |

## 🤖 Gemini AI Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/gemini/reports/<event_id>` | Get Gemini AI report for specific event |
| `GET` | `/api/gemini/reports` | Get recent Gemini AI reports |
| `GET` | `/api/gemini/stats` | Get Gemini reporter statistics |
| `GET` | `/api/gemini/check-env` | Check if Gemini API key is available |
| `POST` | `/api/gemini/enable` | Enable Gemini auto-reporting |
| `POST` | `/api/gemini/disable` | Disable Gemini auto-reporting |

## 🔍 Vector Database & Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/vector/search` | Search events using semantic similarity |
| `GET` | `/api/vector/search/similar/<event_id>` | Find events similar to specific event |
| `GET` | `/api/vector/events` | Get recent events from vector database |
| `GET` | `/api/vector/stats` | Get vector database statistics |
| `POST` | `/api/vector/clear` | Clear all events from vector database |

## 🔔 Notification System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/notifications` | Get recent notifications |
| `POST` | `/api/notifications/<notification_id>/dismiss` | Dismiss a notification |
| `GET` | `/api/notifications/stats` | Get notification statistics |
| `POST` | `/api/notifications/clear` | Clear notification history |

## 📈 Tracking Statistics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/tracking/stats` | Get enter/exit tracking statistics |

## 🎯 Camera Detection (NEW - Offender Identification)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/camera_detection/start` | Start camera-based offender detection |
| `POST` | `/api/camera_detection/stop` | Stop camera-based offender detection |
| `POST` | `/api/camera_detection/pause` | Pause camera-based offender detection |
| `POST` | `/api/camera_detection/resume` | Resume camera-based offender detection |
| `GET` | `/api/camera_detection/status` | Get camera detection service status |
| `GET` | `/api/camera_detection/stats` | Get camera detection statistics |
| `GET` | `/api/camera_detection/recent_detections` | Get recent detection results |
| `GET` | `/api/camera_detection/test_camera/<int:camera_index>` | Test camera for detection capabilities |
| `GET` | `/api/camera_detection/discover_cameras` | Discover cameras available for detection |
| `POST` | `/api/camera_detection/detect_image` | Detect offenders in uploaded image |
| `GET` | `/api/camera_detection/database_stats` | Get database statistics for detection |

## 📡 Real-time Communication (SocketIO)

The backend also provides real-time communication via SocketIO for live updates:

### Events Emitted by Server:
- `detection_update` - Real-time object detection updates
- `frame_update` - Processed frame updates
- `timeline_event` - Timeline event notifications
- `new_notification` - New notification alerts
- `processing_error` - Processing error notifications
- `camera_detection_update` - Camera detection results
- `camera_detection_alert` - High-confidence offender alerts
- `camera_detection_status` - Camera detection status changes

### Events Received by Server:
- `connect` - Client connection
- `disconnect` - Client disconnection
- `request_stats` - Stats update request

## 🔧 Configuration Parameters

### Camera Detection Parameters:
- `camera_index` - Camera device index (default: 0)
- `detection_interval` - Seconds between detections (default: 2.0)
- `confidence_threshold` - Minimum confidence for matches (default: 0.3)
- `max_cameras` - Maximum cameras to discover (default: 5)

### Video Processing Parameters:
- `confidence` - Detection confidence threshold (default: 0.25)
- `enable_tracking` - Enable object tracking (default: true)
- `target_classes` - Specific object classes to detect

### Timeline Parameters:
- `limit` - Number of events to return (default: 50)
- `video_source` - Filter by video source

### Vector Search Parameters:
- `q` - Search query string
- `limit` - Number of results (default: 10)
- `min_similarity` - Minimum similarity score (default: 0.7)

## 📝 Response Formats

All endpoints return JSON responses with the following structure:

### Success Response:
```json
{
  "status": "success",
  "data": { ... },
  "message": "Optional message"
}
```

### Error Response:
```json
{
  "error": "Error message",
  "status_code": 500
}
```

### Camera Detection Response:
```json
{
  "results": [
    {
      "offender_id": "12345",
      "name": "John Doe",
      "confidence": 0.85,
      "method": "opencv",
      "methods_used": ["opencv", "vector"],
      "face_region": [x, y, w, h],
      "offender_info": { ... }
    }
  ],
  "count": 1,
  "timestamp": "2025-10-04T21:17:44.123456"
}
```

## 🚀 Getting Started

1. Start the backend server: `python web_app/app.py`
2. Access the web interface at: `http://localhost:5002`
3. Use the API endpoints for programmatic access
4. Connect via SocketIO for real-time updates

## 📚 Additional Resources

- Face detection databases: `sex-offenders/` directory
- OpenCV embeddings: `opencv_embeddings/` directory
- Upload directory: `uploads/` directory
- Timeline snapshots: `web_app/timeline_snapshots/` directory
