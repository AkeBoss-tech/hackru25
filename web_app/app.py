"""
Flask web application for real-time video processing with YOLOv8.
Provides web interface for camera streams, video uploads, and object detection.
"""

import os
import sys
import json
import base64
import threading
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, Response, send_file
from flask_socketio import SocketIO, emit
import io
from werkzeug.utils import secure_filename

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

try:
    from video_processor import VideoProcessor
    from camera_handler import CameraHandler
    from config import Config
except ImportError:
    # Fallback to backend module import
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from backend.video_processor import VideoProcessor
    from backend.camera_handler import CameraHandler
    from backend.config import Config

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Initialize SocketIO for real-time communication
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables for video processing
video_processor = None
camera_handler = None
processing_thread = None
is_processing = False
current_mode = None  # 'camera', 'upload', 'stream'
processing_stats = {
    'total_frames': 0,
    'total_detections': 0,
    'fps': 0,
    'detection_counts': {},
    'active_tracks': 0,
    'processing_time': 0
}

# Create upload directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebVideoProcessor:
    """Web-specific video processor wrapper."""
    
    def __init__(self):
        self.processor = None
        self.is_running = False
        self.frame_buffer = None
        self.stats = {}
        
    def initialize(self, model_path=None, confidence=0.25, enable_tracking=True):
        """Initialize the video processor."""
        try:
            self.processor = VideoProcessor(
                model_path=model_path,
                confidence_threshold=confidence,
                enable_tracking=enable_tracking
            )
            
            # Set up callbacks
            self.processor.set_detection_callback(self._on_detection)
            self.processor.set_frame_callback(self._on_frame)
            self.processor.set_timeline_event_callback(self._on_timeline_event)
            
            logger.info("Video processor initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize video processor: {e}")
            return False
    
    def _on_detection(self, detections, frame, frame_number):
        """Callback for when objects are detected."""
        if detections:
            # Update global stats
            global processing_stats
            processing_stats['total_detections'] += len(detections)
            
            for detection in detections:
                class_name = detection['class_name']
                processing_stats['detection_counts'][class_name] = \
                    processing_stats['detection_counts'].get(class_name, 0) + 1
            
            # Emit detection data to web clients (convert numpy types to Python types)
            detection_data = {
                'frame_number': int(frame_number),
                'detections': [
                    {
                        'class_name': str(d['class_name']),
                        'confidence': float(d['confidence']),
                        'bbox': [float(x) for x in d['bbox']],
                        'track_id': int(d.get('track_id', 0)) if d.get('track_id') is not None else None
                    }
                    for d in detections
                ],
                'timestamp': datetime.now().isoformat()
            }
            socketio.emit('detection_update', detection_data)
    
    def _on_frame(self, processed_frame, frame_number, raw_frame=None):
        """Callback for each processed frame."""
        global processing_stats
        processing_stats['total_frames'] = int(frame_number)
        
        # Convert frames to base64 for web display
        try:
            # Processed frame
            _, buffer = cv2.imencode('.jpg', processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            processed_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Raw frame (if provided)
            raw_base64 = None
            if raw_frame is not None:
                _, raw_buffer = cv2.imencode('.jpg', raw_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                raw_base64 = base64.b64encode(raw_buffer).decode('utf-8')
            
            # Get timeline statistics
            timeline_stats = {}
            if self.processor and self.processor.get_timeline_manager():
                timeline_stats = self.processor.get_timeline_manager().get_statistics()
            
            # Emit frame data to web clients
            frame_data = {
                'frame_number': int(frame_number),
                'processed_frame': processed_base64,
                'raw_frame': raw_base64,
                'timestamp': datetime.now().isoformat(),
                'timeline_stats': timeline_stats
            }
            socketio.emit('frame_update', frame_data)
            
        except Exception as e:
            logger.error(f"Error encoding frame: {e}")
    
    def _on_timeline_event(self, timeline_event):
        """Callback for when timeline events are created."""
        try:
            # Emit timeline event to web clients
            event_data = timeline_event.to_dict()
            socketio.emit('timeline_event', event_data)
            logger.info(f"Timeline event emitted: {event_data['event_id']}")
        except Exception as e:
            logger.error(f"Error handling timeline event: {e}")
    
    def start_camera_processing(self, camera_index=0):
        """Start processing camera stream."""
        if not self.processor:
            return False
        
        self.is_running = True
        
        def process_camera():
            try:
                stats = self.processor.process_camera_stream(
                    camera_index=camera_index,
                    display=False,  # Don't display, we'll send to web
                    max_frames=None  # Unlimited
                )
                self.stats = stats
            except Exception as e:
                logger.error(f"Camera processing error: {e}")
                socketio.emit('processing_error', {'error': str(e)})
            finally:
                self.is_running = False
        
        # Start processing in separate thread
        thread = threading.Thread(target=process_camera, daemon=True)
        thread.start()
        return True
    
    def start_video_processing(self, video_path):
        """Start processing video file."""
        if not self.processor:
            return False
        
        self.is_running = True
        
        def process_video():
            try:
                stats = self.processor.process_video_file(
                    video_path=video_path,
                    display=False,  # Don't display, we'll send to web
                    save_video=False
                )
                self.stats = stats
            except Exception as e:
                logger.error(f"Video processing error: {e}")
                socketio.emit('processing_error', {'error': str(e)})
            finally:
                self.is_running = False
        
        # Start processing in separate thread
        thread = threading.Thread(target=process_video, daemon=True)
        thread.start()
        return True
    
    def stop_processing(self):
        """Stop current processing."""
        if self.processor:
            self.processor.stop_processing()
        self.is_running = False


# Initialize web video processor
web_processor = WebVideoProcessor()


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/api/cameras')
def get_cameras():
    """Get available cameras."""
    try:
        camera_handler = CameraHandler()
        cameras = camera_handler.discover_cameras(max_cameras=5)
        camera_info = []
        
        for camera_id in cameras:
            if camera_handler.open_camera(camera_id):
                properties = camera_handler.get_camera_properties(camera_id)
                camera_info.append({
                    'id': camera_id,
                    'properties': properties
                })
                camera_handler.close_camera(camera_id)
        
        return jsonify({'cameras': camera_info})
    except Exception as e:
        logger.error(f"Error getting cameras: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/start_camera', methods=['POST'])
def start_camera():
    """Start camera processing."""
    global current_mode, is_processing
    
    try:
        data = request.get_json()
        camera_index = data.get('camera_index', 0)
        confidence = data.get('confidence', 0.25)
        enable_tracking = data.get('enable_tracking', True)
        
        # Stop any current processing
        if is_processing:
            web_processor.stop_processing()
            time.sleep(1)
        
        # Initialize processor
        if not web_processor.initialize(confidence=confidence, enable_tracking=enable_tracking):
            return jsonify({'error': 'Failed to initialize video processor'}), 500
        
        # Start processing
        if web_processor.start_camera_processing(camera_index):
            current_mode = 'camera'
            is_processing = True
            
            # Reset stats
            global processing_stats
            processing_stats = {
                'total_frames': 0,
                'total_detections': 0,
                'fps': 0,
                'detection_counts': {},
                'active_tracks': 0,
                'processing_time': 0
            }
            
            return jsonify({'status': 'started', 'camera_index': camera_index})
        else:
            return jsonify({'error': 'Failed to start camera processing'}), 500
            
    except Exception as e:
        logger.error(f"Error starting camera: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload_video', methods=['POST'])
def upload_video():
    """Handle video file upload."""
    global current_mode, is_processing
    
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file:
            # Secure filename and save
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Get processing parameters
            confidence = float(request.form.get('confidence', 0.25))
            enable_tracking = request.form.get('enable_tracking', 'true').lower() == 'true'
            
            # Stop any current processing
            if is_processing:
                web_processor.stop_processing()
                time.sleep(1)
            
            # Initialize processor
            if not web_processor.initialize(confidence=confidence, enable_tracking=enable_tracking):
                return jsonify({'error': 'Failed to initialize video processor'}), 500
            
            # Start processing
            if web_processor.start_video_processing(filepath):
                current_mode = 'upload'
                is_processing = True
                
                # Reset stats
                global processing_stats
                processing_stats = {
                    'total_frames': 0,
                    'total_detections': 0,
                    'fps': 0,
                    'detection_counts': {},
                    'active_tracks': 0,
                    'processing_time': 0
                }
                
                return jsonify({
                    'status': 'started',
                    'filename': filename,
                    'filepath': filepath
                })
            else:
                return jsonify({'error': 'Failed to start video processing'}), 500
                
    except Exception as e:
        logger.error(f"Error uploading video: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stop_processing', methods=['POST'])
def stop_processing():
    """Stop current processing."""
    global is_processing, current_mode
    
    try:
        web_processor.stop_processing()
        is_processing = False
        current_mode = None
        
        return jsonify({'status': 'stopped'})
    except Exception as e:
        logger.error(f"Error stopping processing: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/status')
def get_status():
    """Get current processing status."""
    global processing_stats, is_processing, current_mode
    
    # Calculate FPS if we have enough data
    if processing_stats['total_frames'] > 0 and processing_stats['processing_time'] > 0:
        processing_stats['fps'] = processing_stats['total_frames'] / processing_stats['processing_time']
    
    return jsonify({
        'is_processing': is_processing,
        'mode': current_mode,
        'stats': processing_stats,
        'processor_stats': web_processor.stats if web_processor.stats else {}
    })


@app.route('/api/config')
def get_config():
    """Get current configuration."""
    try:
        config = Config()
        return jsonify({
            'model_path': config.get_model_path(),
            'confidence_threshold': config.CONFIDENCE_THRESHOLD,
            'enable_tracking': config.ENABLE_TRACKING,
            'tracking_method': config.TRACKING_METHOD,
            'device': config.DEVICE
        })
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/timeline/events')
def get_timeline_events():
    """Get timeline events."""
    try:
        if not web_processor.processor or not web_processor.processor.get_timeline_manager():
            return jsonify({'events': [], 'message': 'Timeline not available'})
        
        timeline_manager = web_processor.processor.get_timeline_manager()
        
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        video_source = request.args.get('video_source', type=str)
        
        events = timeline_manager.get_events(
            limit=limit,
            video_source=video_source
        )
        
        return jsonify({
            'events': events,
            'count': len(events)
        })
    except Exception as e:
        logger.error(f"Error getting timeline events: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/timeline/events/<event_id>')
def get_timeline_event(event_id):
    """Get a specific timeline event by ID."""
    try:
        if not web_processor.processor or not web_processor.processor.get_timeline_manager():
            return jsonify({'error': 'Timeline not available'}), 404
        
        timeline_manager = web_processor.processor.get_timeline_manager()
        event = timeline_manager.get_event_by_id(event_id)
        
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        return jsonify(event)
    except Exception as e:
        logger.error(f"Error getting timeline event {event_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/timeline/snapshots/<path:snapshot_path>')
def get_timeline_snapshot(snapshot_path):
    """Get a timeline snapshot image."""
    try:
        if not web_processor.processor or not web_processor.processor.get_timeline_manager():
            return jsonify({'error': 'Timeline not available'}), 404
        
        timeline_manager = web_processor.processor.get_timeline_manager()
        image_data = timeline_manager.get_snapshot(snapshot_path)
        
        if not image_data:
            return jsonify({'error': 'Snapshot not found'}), 404
        
        return Response(
            image_data,
            mimetype='image/jpeg',
            headers={'Content-Disposition': f'attachment; filename={os.path.basename(snapshot_path)}'}
        )
    except Exception as e:
        logger.error(f"Error getting snapshot {snapshot_path}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/timeline/snapshots/<path:snapshot_path>/raw')
def get_timeline_raw_snapshot(snapshot_path):
    """Get a raw timeline snapshot image (without annotations)."""
    try:
        if not web_processor.processor or not web_processor.processor.get_timeline_manager():
            return jsonify({'error': 'Timeline not available'}), 404
        
        timeline_manager = web_processor.processor.get_timeline_manager()
        
        # Get the raw snapshot path
        raw_path = timeline_manager.get_raw_snapshot_path(snapshot_path)
        if not raw_path:
            return jsonify({'error': 'Raw snapshot not found'}), 404
        
        image_data = timeline_manager.get_snapshot(raw_path)
        
        if not image_data:
            return jsonify({'error': 'Raw snapshot not found'}), 404
        
        return Response(
            image_data,
            mimetype='image/jpeg',
            headers={'Content-Disposition': f'attachment; filename={os.path.basename(raw_path)}'}
        )
    except Exception as e:
        logger.error(f"Error getting raw snapshot {snapshot_path}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/timeline/statistics')
def get_timeline_statistics():
    """Get timeline statistics."""
    try:
        if not web_processor.processor or not web_processor.processor.get_timeline_manager():
            return jsonify({'error': 'Timeline not available'}), 404
        
        timeline_manager = web_processor.processor.get_timeline_manager()
        stats = timeline_manager.get_statistics()
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting timeline statistics: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/timeline/clear', methods=['POST'])
def clear_timeline_events():
    """Clear all timeline events."""
    try:
        if not web_processor.processor or not web_processor.processor.get_timeline_manager():
            return jsonify({'error': 'Timeline not available'}), 404
        
        timeline_manager = web_processor.processor.get_timeline_manager()
        timeline_manager.clear_events()
        
        return jsonify({'status': 'cleared', 'message': 'All timeline events cleared'})
    except Exception as e:
        logger.error(f"Error clearing timeline events: {e}")
        return jsonify({'error': str(e)}), 500




@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info(f"Client connected: {request.sid}")
    emit('status', {'message': 'Connected to video processing server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on('request_stats')
def handle_stats_request():
    """Handle stats request from client."""
    global processing_stats
    emit('stats_update', processing_stats)


if __name__ == '__main__':
    # Initialize video processor
    if not web_processor.initialize():
        logger.error("Failed to initialize video processor")
        sys.exit(1)
    
    # Start Flask-SocketIO app
    socketio.run(app, debug=True, host='0.0.0.0', port=5002, allow_unsafe_werkzeug=True)
