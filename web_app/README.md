# Sentri

A modern web interface for real-time video processing using YOLOv8 object detection and tracking.

## Features

- 🎥 **Real-time Camera Processing**: Process live camera feeds with object detection
- 📁 **Video File Upload**: Upload and process video files (MP4, AVI, MOV)
- 🎯 **Object Tracking**: Track objects across frames with unique IDs
- 📊 **Live Statistics**: Real-time statistics and detection counts
- 🌐 **Web Interface**: Modern, responsive web interface
- ⚡ **WebSocket Communication**: Real-time updates via WebSocket
- 📱 **Mobile Friendly**: Responsive design that works on all devices

## Quick Start

### 1. Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install web app dependencies
pip install flask flask-socketio werkzeug
```

### 2. Start the Web Application

```bash
# From the project root directory
cd web_app
python run.py
```

### 3. Open in Browser

Open your web browser and navigate to: **http://localhost:5000**

## Usage

### Camera Processing

1. Select **"Camera"** mode
2. Choose your camera from the dropdown
3. Adjust confidence threshold (0.1 - 1.0)
4. Enable/disable object tracking
5. Click **"Start Processing"**

### Video Upload

1. Select **"Upload"** mode
2. Click **"Choose File"** and select a video file
3. Adjust processing parameters
4. Click **"Start Processing"**

### Real-time Features

- **Live Video Feed**: See the processed video with bounding boxes and labels
- **Detection Statistics**: View real-time counts of detected objects
- **Recent Detections**: See the latest detections with confidence scores
- **Processing Stats**: Monitor FPS, frame count, and processing time

## API Endpoints

### REST API

- `GET /api/cameras` - Get available cameras
- `POST /api/start_camera` - Start camera processing
- `POST /api/upload_video` - Upload and process video file
- `POST /api/stop_processing` - Stop current processing
- `GET /api/status` - Get processing status
- `GET /api/config` - Get current configuration

### WebSocket Events

- `frame_update` - New processed frame data
- `detection_update` - New detection results
- `stats_update` - Updated statistics
- `processing_error` - Processing error notifications

## Configuration

The web application uses the same configuration system as the backend. You can modify settings in `backend/config.py` or create a custom configuration file.

### Key Settings

- **Model Path**: Path to YOLOv8 model file
- **Confidence Threshold**: Minimum confidence for detections
- **Tracking**: Enable/disable object tracking
- **Device**: CPU, CUDA, or auto-detection

## File Structure

```
web_app/
├── app.py              # Main Flask application
├── run.py              # Startup script
├── README.md           # This file
├── static/
│   ├── css/
│   │   └── style.css   # Custom styles
│   └── js/
│       └── app.js      # Frontend JavaScript
└── templates/
    └── index.html      # Main HTML template
```

## Troubleshooting

### Common Issues

1. **Camera Not Found**
   - Check camera permissions
   - Ensure camera is not used by other applications
   - Try different camera indices

2. **Video Upload Fails**
   - Check file size (max 100MB)
   - Ensure supported format (MP4, AVI, MOV)
   - Check file permissions

3. **Processing Errors**
   - Verify YOLOv8 model file exists
   - Check system resources (CPU/Memory)
   - Review console logs for detailed errors

4. **WebSocket Connection Issues**
   - Check firewall settings
   - Ensure port 5000 is available
   - Try refreshing the browser

### Debug Mode

Run with debug mode for detailed logging:

```bash
export FLASK_DEBUG=1
python run.py
```

## Performance Tips

- **Lower Resolution**: Use lower camera resolution for better performance
- **Adjust Confidence**: Higher confidence = fewer detections = better performance
- **Disable Tracking**: Turn off tracking if not needed
- **Close Other Apps**: Free up system resources

## Browser Compatibility

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## Security Notes

- The application runs in debug mode by default
- Change the secret key in production
- Consider using HTTPS for production deployment
- Implement proper authentication if needed

## Development

### Adding New Features

1. **Backend**: Modify `app.py` for new API endpoints
2. **Frontend**: Update `app.js` for new UI functionality
3. **Styling**: Modify `style.css` for visual changes
4. **Templates**: Update `index.html` for layout changes

### Testing

```bash
# Run backend tests
cd ../tests
python test_backend.py

# Test web app manually
# Open browser and test all features
```

## Production Deployment

For production deployment:

1. Set `debug=False` in `app.py`
2. Use a production WSGI server (Gunicorn, uWSGI)
3. Configure reverse proxy (Nginx)
4. Set up SSL certificates
5. Implement proper logging
6. Add authentication/authorization

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review console logs
3. Check browser developer tools
4. Create an issue with detailed information
