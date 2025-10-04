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

# Add the parent directory to Python path to import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from werkzeug.utils import secure_filename

try:
    from backend.video_processor import VideoProcessor
    from backend.camera_handler import CameraHandler
    from backend.config import Config
except ImportError as e:
    print(f"Error importing backend modules: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

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
        
    def initialize(self, model_path=None, confidence=0.25, enable_tracking=True, target_classes=None):
        """Initialize the video processor."""
        try:
            self.processor = VideoProcessor(
                model_path=model_path,
                confidence_threshold=confidence,
                enable_tracking=enable_tracking,
                target_classes=target_classes
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


@app.route('/api/classes')
def get_detection_classes():
    """Get available detection class sets."""
    try:
        from backend.surveillance_classes import get_available_class_sets
        
        class_sets = get_available_class_sets()
        
        return jsonify({
            'class_sets': class_sets,
            'default': 'core'
        })
    except Exception as e:
        logger.error(f"Error getting detection classes: {e}")
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
        target_classes = data.get('target_classes', None)
        
        # Stop any current processing
        if is_processing:
            web_processor.stop_processing()
            time.sleep(1)
        
        # Initialize processor
        if not web_processor.initialize(confidence=confidence, enable_tracking=enable_tracking, target_classes=target_classes):
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
            target_classes_str = request.form.get('target_classes', '')
            target_classes = target_classes_str.split(',') if target_classes_str else None
            
            # Stop any current processing
            if is_processing:
                web_processor.stop_processing()
                time.sleep(1)
            
            # Initialize processor
            if not web_processor.initialize(confidence=confidence, enable_tracking=enable_tracking, target_classes=target_classes):
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


@app.route('/api/gemini/reports/<event_id>')
def get_gemini_report(event_id):
    """Get Gemini AI report for a specific event."""
    try:
        from backend.auto_gemini_reporter import get_auto_reporter
        
        auto_reporter = get_auto_reporter()
        if not auto_reporter.enabled:
            return jsonify({'error': 'Gemini reporting not enabled'}), 404
        
        report = auto_reporter.get_report(event_id)
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        return jsonify(report)
    except Exception as e:
        logger.error(f"Error getting Gemini report for {event_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/gemini/reports')
def get_recent_gemini_reports():
    """Get recent Gemini AI reports."""
    try:
        from backend.auto_gemini_reporter import get_auto_reporter
        
        auto_reporter = get_auto_reporter()
        if not auto_reporter.enabled:
            return jsonify({'error': 'Gemini reporting not enabled'}), 404
        
        limit = request.args.get('limit', 10, type=int)
        reports = auto_reporter.get_recent_reports(limit)
        
        return jsonify({
            'reports': reports,
            'count': len(reports)
        })
    except Exception as e:
        logger.error(f"Error getting recent Gemini reports: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/gemini/stats')
def get_gemini_stats():
    """Get Gemini reporter statistics."""
    try:
        from backend.auto_gemini_reporter import get_auto_reporter
        
        auto_reporter = get_auto_reporter()
        stats = auto_reporter.get_stats()
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting Gemini stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/gemini/check-env')
def check_gemini_env():
    """Check if Gemini API key is available in environment."""
    try:
        import os
        api_key = os.getenv('GEMINI_API_KEY')
        
        return jsonify({
            'has_api_key': bool(api_key),
            'message': 'API key found in environment' if api_key else 'No API key in environment'
        })
    except Exception as e:
        logger.error(f"Error checking Gemini environment: {e}")
        return jsonify({'has_api_key': False, 'error': str(e)}), 500


@app.route('/api/gemini/enable', methods=['POST'])
def enable_gemini_reporting():
    """Enable Gemini auto-reporting."""
    try:
        from backend.auto_gemini_reporter import enable_auto_reporting
        import os
        
        data = request.get_json() or {}
        api_key = data.get('api_key')
        
        # If api_key is 'from_env', use environment variable
        if api_key == 'from_env':
            api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            return jsonify({'error': 'GEMINI_API_KEY not found in environment variables'}), 400
        
        auto_reporter = enable_auto_reporting(api_key)
        
        return jsonify({
            'status': 'enabled',
            'message': 'Gemini auto-reporting enabled using environment variable',
            'stats': auto_reporter.get_stats()
        })
    except Exception as e:
        logger.error(f"Error enabling Gemini reporting: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/gemini/disable', methods=['POST'])
def disable_gemini_reporting():
    """Disable Gemini auto-reporting."""
    try:
        from backend.auto_gemini_reporter import disable_auto_reporting
        
        disable_auto_reporting()
        
        return jsonify({
            'status': 'disabled',
            'message': 'Gemini auto-reporting disabled'
        })
    except Exception as e:
        logger.error(f"Error disabling Gemini reporting: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/vector/search')
def vector_search():
    """Search events using semantic similarity."""
    try:
        from backend.vector_database import get_vector_database
        
        # Get search parameters
        query = request.args.get('q', '')
        limit = request.args.get('limit', 10, type=int)
        min_similarity = request.args.get('min_similarity', 0.7, type=float)
        
        if not query:
            return jsonify({'error': 'Query parameter required'}), 400
        
        vector_db = get_vector_database()
        results = vector_db.search_similar_events(
            query=query,
            limit=limit,
            min_similarity=min_similarity
        )
        
        return jsonify({
            'query': query,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Error in vector search: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/vector/search/similar/<event_id>')
def search_similar_to_event(event_id):
    """Find events similar to a specific event."""
    try:
        from backend.vector_database import get_vector_database
        
        limit = request.args.get('limit', 10, type=int)
        
        vector_db = get_vector_database()
        
        # Get the event first
        event = vector_db.get_event_by_id(event_id)
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        # Search for similar events using the event's document
        results = vector_db.search_similar_events(
            query=event['document'],
            limit=limit + 1,  # +1 because the original event will be included
            min_similarity=0.7
        )
        
        # Filter out the original event
        similar_results = [r for r in results if r['event_id'] != event_id]
        
        return jsonify({
            'original_event': event,
            'similar_events': similar_results,
            'count': len(similar_results)
        })
        
    except Exception as e:
        logger.error(f"Error searching similar events: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/vector/events')
def get_vector_events():
    """Get recent events from vector database."""
    try:
        from backend.vector_database import get_vector_database
        
        limit = request.args.get('limit', 50, type=int)
        
        vector_db = get_vector_database()
        events = vector_db.get_recent_events(limit)
        
        return jsonify({
            'events': events,
            'count': len(events)
        })
        
    except Exception as e:
        logger.error(f"Error getting vector events: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/vector/stats')
def get_vector_stats():
    """Get vector database statistics."""
    try:
        from backend.vector_database import get_vector_database
        
        vector_db = get_vector_database()
        stats = vector_db.get_stats()
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting vector stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/vector/clear', methods=['POST'])
def clear_vector_database():
    """Clear all events from vector database."""
    try:
        from backend.vector_database import get_vector_database
        
        vector_db = get_vector_database()
        vector_db.clear_database()
        
        return jsonify({
            'status': 'cleared',
            'message': 'Vector database cleared'
        })
        
    except Exception as e:
        logger.error(f"Error clearing vector database: {e}")
        return jsonify({'error': str(e)}), 500


# Notification System API Endpoints
@app.route('/api/notifications')
def get_notifications():
    """Get recent notifications."""
    try:
        from backend.notification_manager import get_notification_manager, NotificationImportance
        
        notification_manager = get_notification_manager()
        
        # Get query parameters
        limit = int(request.args.get('limit', 10))
        importance_filter = request.args.get('importance')
        
        # Parse importance filter
        importance = None
        if importance_filter:
            try:
                importance = NotificationImportance(importance_filter)
            except ValueError:
                return jsonify({'error': f'Invalid importance level: {importance_filter}'}), 400
        
        notifications = notification_manager.get_recent_notifications(limit, importance)
        
        # Convert to JSON-serializable format
        notifications_data = []
        for notif in notifications:
            notifications_data.append({
                'id': notif.id,
                'timestamp': notif.timestamp.isoformat(),
                'importance': notif.importance.value,
                'title': notif.title,
                'message': notif.message,
                'event_data': notif.event_data,
                'gemini_report': notif.gemini_report,
                'dismissed': notif.dismissed
            })
        
        return jsonify({
            'notifications': notifications_data,
            'count': len(notifications_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/notifications/<notification_id>/dismiss', methods=['POST'])
def dismiss_notification(notification_id):
    """Dismiss a notification."""
    try:
        from backend.notification_manager import get_notification_manager
        
        notification_manager = get_notification_manager()
        notification_manager.dismiss_notification(notification_id)
        
        return jsonify({
            'status': 'dismissed',
            'message': f'Notification {notification_id} dismissed'
        })
        
    except Exception as e:
        logger.error(f"Error dismissing notification: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/notifications/stats')
def get_notification_stats():
    """Get notification statistics."""
    try:
        from backend.notification_manager import get_notification_manager
        
        notification_manager = get_notification_manager()
        stats = notification_manager.get_notification_stats()
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting notification stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/notifications/clear', methods=['POST'])
def clear_notifications():
    """Clear notification history."""
    try:
        from backend.notification_manager import get_notification_manager
        
        notification_manager = get_notification_manager()
        notification_manager.clear_history()
        
        return jsonify({
            'status': 'cleared',
            'message': 'Notification history cleared'
        })
        
    except Exception as e:
        logger.error(f"Error clearing notifications: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/tracking/stats')
def get_tracking_stats():
    """Get enter/exit tracking statistics."""
    try:
        if web_processor.processor and hasattr(web_processor.processor, 'enter_exit_tracker'):
            stats = web_processor.processor.enter_exit_tracker.get_stats()
            return jsonify(stats)
        else:
            return jsonify({
                'total_enters': 0,
                'total_exits': 0,
                'active_objects': 0,
                'currently_tracking': 0,
                'recently_exited': 0,
                'total_seen': 0
            })
        
    except Exception as e:
        logger.error(f"Error getting tracking stats: {e}")
        return jsonify({'error': str(e)}), 500


# Initialize notification system callback
def setup_notification_callbacks():
    """Setup notification callbacks for real-time updates."""
    try:
        from backend.notification_manager import get_notification_manager
        
        def on_notification(notification):
            """Callback for new notifications - broadcast to all clients."""
            try:
                notification_data = {
                    'id': notification.id,
                    'timestamp': notification.timestamp.isoformat(),
                    'importance': notification.importance.value,
                    'title': notification.title,
                    'message': notification.message,
                    'event_data': notification.event_data,
                    'gemini_report': notification.gemini_report
                }
                
                # Broadcast to all connected clients
                socketio.emit('new_notification', notification_data)
                logger.info(f"Broadcasted notification: {notification.title}")
                
            except Exception as e:
                logger.error(f"Error broadcasting notification: {e}")
        
        # Register callback
        notification_manager = get_notification_manager()
        notification_manager.add_notification_callback(on_notification)
        logger.info("Notification callbacks setup complete")
        
    except Exception as e:
        logger.error(f"Error setting up notification callbacks: {e}")


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
    
    # Setup notification system
    setup_notification_callbacks()
    
    # Start Flask-SocketIO app
    socketio.run(app, debug=True, host='0.0.0.0', port=5002, allow_unsafe_werkzeug=True)
