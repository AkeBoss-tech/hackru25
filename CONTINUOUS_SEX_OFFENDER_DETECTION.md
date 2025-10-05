# Continuous Sex Offender Detection

This implementation provides a comprehensive continuous sex offender detection system that automatically monitors camera feeds and identifies known sex offenders in real-time.

## 🚨 Features

- **Continuous Camera Monitoring**: Automatically detects and identifies sex offenders from live camera feeds
- **Real-time Alerts**: Immediate notifications for high-confidence matches
- **Multiple Detection Methods**: Combines OpenCV and vector-based face recognition
- **Web API Integration**: Full REST API for controlling detection
- **Real-time Web Updates**: Live updates via WebSocket connections
- **Comprehensive Logging**: Detailed logs with confidence scores and offender information
- **Configurable Thresholds**: Adjustable detection intervals and confidence levels

## 🏗️ Architecture

### Backend Components

1. **`continuous_sex_offender_detector.py`**: Main detection service
2. **`improved_image_matcher.py`**: Face recognition and matching engine
3. **Web API endpoints**: RESTful interface for control and monitoring
4. **Real-time callbacks**: WebSocket integration for live updates

### Key Classes

- `ContinuousSexOffenderDetector`: Main detection service
- `ImprovedImageMatcher`: Face recognition engine
- Web API endpoints for control and monitoring

## 🚀 Usage

### 1. Direct Backend Usage

```python
from backend.continuous_sex_offender_detector import get_continuous_sex_offender_detector

# Initialize detector
detector = get_continuous_sex_offender_detector()

# Configure settings
detector.set_detection_interval(2.0)  # Check every 2 seconds
detector.set_confidence_threshold(0.3)  # 30% confidence threshold

# Start detection
detector.start_detection(camera_index=0)

# Detection will run continuously and print alerts to console
```

### 2. Command Line Interface

```bash
# Interactive mode
python run_continuous_sex_offender_detection.py

# Daemon mode
python run_continuous_sex_offender_detection.py --daemon --camera 0 --interval 2.0 --threshold 0.3

# Test camera
python run_continuous_sex_offender_detection.py --test
```

### 3. Web API Usage

Start the web server:
```bash
python web_app/app.py
```

#### API Endpoints

**Start Detection:**
```bash
curl -X POST http://localhost:5002/api/sex_offender_detection/start \
  -H "Content-Type: application/json" \
  -d '{"camera_index": 0, "detection_interval": 2.0, "confidence_threshold": 0.3}'
```

**Stop Detection:**
```bash
curl -X POST http://localhost:5002/api/sex_offender_detection/stop
```

**Get Status:**
```bash
curl http://localhost:5002/api/sex_offender_detection/status
```

**Get Statistics:**
```bash
curl http://localhost:5002/api/sex_offender_detection/stats
```

**Test Camera:**
```bash
curl http://localhost:5002/api/sex_offender_detection/test_camera/0
```

**Detect in Image:**
```bash
curl -X POST http://localhost:5002/api/sex_offender_detection/detect_image \
  -F "image=@test_image.jpg" \
  -F "threshold=0.3"
```

### 4. WebSocket Events

The system provides real-time updates via WebSocket:

- `sex_offender_detection_update`: General detection events
- `sex_offender_alert`: High-confidence alerts
- `sex_offender_detection_status`: Status changes

## 📊 Detection Output

### Console Output Example

```
🚨 CRITICAL ALERT - HIGH CONFIDENCE
🚨 SEX OFFENDER DETECTED: John Doe
🚨 Confidence: 0.856
🚨 Method: opencv
🚨==================================================

============================================================
🚨 SEX OFFENDER DETECTED
============================================================
Name: John Doe
Offender ID: 12345
Confidence: 0.856
Detection Method: opencv
Address: 123 Main St, City, State
Offenses: Sexual assault, Indecent exposure
Risk Level: High
Methods Used: opencv, vector
Face Region: x=150, y=100, width=80, height=80
Timestamp: 2024-01-15 14:30:25
============================================================
```

### API Response Example

```json
{
  "status": "started",
  "camera_index": 0,
  "detection_interval": 2.0,
  "confidence_threshold": 0.3,
  "message": "Continuous sex offender detection started"
}
```

## 🔧 Configuration

### Detection Settings

- **Detection Interval**: Time between detection attempts (default: 2.0 seconds)
- **Confidence Threshold**: Minimum confidence for matches (default: 0.3)
- **Max Detections per Frame**: Maximum matches to return (default: 5)

### Alert Levels

- **CRITICAL**: Confidence > 0.8
- **HIGH**: Confidence > 0.7
- **MEDIUM**: Confidence > 0.5
- **LOW**: Confidence > 0.3

## 🧪 Testing

### Run Test Suite

```bash
python test_continuous_sex_offender_detection.py
```

This will test:
1. Direct backend detection
2. Web API integration
3. Image-based detection
4. Camera functionality

### Test Components

```bash
# Test camera access
python run_continuous_sex_offender_detection.py --test

# Test specific camera
python run_continuous_sex_offender_detection.py --test --camera 1
```

## 📁 File Structure

```
backend/
├── continuous_sex_offender_detector.py  # Main detection service
├── improved_image_matcher.py            # Face recognition engine
├── camera_detection_service.py          # Existing camera service
└── ...

web_app/
├── app.py                               # Web application with API endpoints
└── ...

run_continuous_sex_offender_detection.py # Command-line interface
test_continuous_sex_offender_detection.py # Test suite
```

## 🔒 Security Considerations

- **Data Privacy**: All detection data is processed locally
- **Access Control**: Web API should be secured in production
- **Logging**: Sensitive information should be filtered from logs
- **Camera Access**: Ensure proper camera permissions

## 🚀 Deployment

### Production Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Database**:
   - Ensure sex offender database is populated
   - Verify face recognition databases are available

3. **Start Services**:
   ```bash
   # Start web server
   python web_app/app.py
   
   # Or run as daemon
   python run_continuous_sex_offender_detection.py --daemon
   ```

4. **Monitor Logs**:
   - Check detection logs for alerts
   - Monitor system performance
   - Review false positive rates

## 📈 Performance

### Recommended Settings

- **Detection Interval**: 2-5 seconds (balance between responsiveness and CPU usage)
- **Confidence Threshold**: 0.3-0.5 (adjust based on false positive tolerance)
- **Camera Resolution**: 640x480 or 1280x720 (balance between accuracy and performance)

### System Requirements

- **CPU**: Multi-core recommended for real-time processing
- **Memory**: 4GB+ RAM for face recognition databases
- **Storage**: SSD recommended for database access
- **Camera**: USB or network camera with good lighting

## 🛠️ Troubleshooting

### Common Issues

1. **Camera Not Found**:
   - Check camera permissions
   - Verify camera index (try 0, 1, 2, etc.)
   - Ensure no other applications are using the camera

2. **No Matches Found**:
   - Verify sex offender database is populated
   - Check confidence threshold settings
   - Ensure good lighting and face visibility

3. **High False Positives**:
   - Increase confidence threshold
   - Improve lighting conditions
   - Update face recognition databases

4. **Performance Issues**:
   - Increase detection interval
   - Reduce camera resolution
   - Close other applications

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs for error messages
3. Test with the provided test suite
4. Verify camera and database setup

## 🔄 Updates

The system is designed to be easily extensible:
- Add new detection methods in `improved_image_matcher.py`
- Extend API endpoints in `web_app/app.py`
- Add new alert types in the detector service
- Integrate with external notification systems

---

**⚠️ Important**: This system is designed for security and safety applications. Ensure proper authorization and legal compliance when deploying in production environments.

