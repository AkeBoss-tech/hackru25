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
    from backend.camera_detection_service import get_camera_detection_service
    from backend.improved_image_matcher import get_improved_matcher
    from backend.distributed_camera_manager import get_distributed_camera_manager
    from backend.continuous_sex_offender_detector import get_continuous_sex_offender_detector
    from backend.snapshot_analysis_service import get_snapshot_analysis_service
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

# Initialize camera detection service
camera_detection_service = get_camera_detection_service()

# Initialize distributed camera manager
distributed_manager = get_distributed_camera_manager()

# Initialize continuous sex offender detector
continuous_sex_offender_detector = get_continuous_sex_offender_detector()

# Initialize snapshot analysis service
snapshot_analysis_service = get_snapshot_analysis_service()

# Setup camera detection callbacks for real-time updates
def setup_camera_detection_callbacks():
    """Setup callbacks for camera detection events."""
    
    def on_detection(results):
        """Callback for detection events."""
        try:
            detection_data = {
                'timestamp': datetime.now().isoformat(),
                'results': results,
                'count': len(results)
            }
            socketio.emit('camera_detection_update', detection_data)
            logger.info(f"Emitted camera detection update: {len(results)} matches")
        except Exception as e:
            logger.error(f"Error emitting detection update: {e}")
    
    def on_alert(alert_data):
        """Callback for high-confidence alerts."""
        try:
            alert_data['timestamp'] = datetime.now().isoformat()
            socketio.emit('camera_detection_alert', alert_data)
            logger.warning(f"Emitted camera detection alert: {alert_data.get('severity', 'UNKNOWN')}")
        except Exception as e:
            logger.error(f"Error emitting alert: {e}")
    
    def on_status_change(status_data):
        """Callback for status changes."""
        try:
            socketio.emit('camera_detection_status', status_data)
            logger.info(f"Emitted camera detection status: {status_data.get('status', 'UNKNOWN')}")
        except Exception as e:
            logger.error(f"Error emitting status change: {e}")
    
    # Register callbacks
    camera_detection_service.add_detection_callback(on_detection)
    camera_detection_service.add_alert_callback(on_alert)
    camera_detection_service.add_status_callback(on_status_change)
    
    logger.info("Camera detection callbacks setup complete")

# Setup callbacks
setup_camera_detection_callbacks()

# Setup continuous sex offender detector callbacks for real-time updates
def setup_sex_offender_detector_callbacks():
    """Setup callbacks for continuous sex offender detection events."""
    
    def on_sex_offender_detection(results):
        """Callback for sex offender detection events."""
        try:
            detection_data = {
                'timestamp': datetime.now().isoformat(),
                'results': results,
                'count': len(results),
                'detection_type': 'sex_offender'
            }
            socketio.emit('sex_offender_detection_update', detection_data)
            logger.warning(f"🚨 Sex offender detection: {len(results)} matches found")
        except Exception as e:
            logger.error(f"Error emitting sex offender detection update: {e}")
    
    def on_sex_offender_alert(alert_data):
        """Callback for high-confidence sex offender alerts."""
        try:
            alert_data['timestamp'] = datetime.now().isoformat()
            socketio.emit('sex_offender_alert', alert_data)
            logger.error(f"🚨 SEX OFFENDER ALERT: {alert_data.get('severity', 'UNKNOWN')} - {alert_data.get('offender_info', {}).get('name', 'Unknown')}")
        except Exception as e:
            logger.error(f"Error emitting sex offender alert: {e}")
    
    def on_sex_offender_status_change(status_data):
        """Callback for sex offender detection status changes."""
        try:
            socketio.emit('sex_offender_detection_status', status_data)
            logger.info(f"Sex offender detection status: {status_data.get('status', 'UNKNOWN')}")
        except Exception as e:
            logger.error(f"Error emitting sex offender status change: {e}")
    
    # Register callbacks
    continuous_sex_offender_detector.add_detection_callback(on_sex_offender_detection)
    continuous_sex_offender_detector.add_alert_callback(on_sex_offender_alert)
    continuous_sex_offender_detector.add_status_callback(on_sex_offender_status_change)
    
    logger.info("Sex offender detector callbacks setup complete")

# Setup sex offender detector callbacks
setup_sex_offender_detector_callbacks()

# Setup distributed camera manager callbacks
def setup_distributed_manager_callbacks():
    """Setup callbacks for distributed camera manager events."""
    
    def on_distributed_frame(frame_data):
        """Callback for distributed frame processing."""
        try:
            # Convert frame to base64 for web display
            processed_frame = frame_data['processed_frame']
            _, buffer = cv2.imencode('.jpg', processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            processed_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Raw frame if available
            raw_base64 = None
            if frame_data.get('raw_frame') is not None:
                raw_frame = frame_data['raw_frame']
                _, raw_buffer = cv2.imencode('.jpg', raw_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                raw_base64 = base64.b64encode(raw_buffer).decode('utf-8')
            
            # Emit frame data to web clients
            frame_info = {
                'stream_id': frame_data['stream_id'],
                'frame_number': frame_data['frame_number'],
                'processed_frame': processed_base64,
                'raw_frame': raw_base64,
                'timestamp': frame_data['timestamp']
            }
            socketio.emit('distributed_frame_update', frame_info)
            
        except Exception as e:
            logger.error(f"Error handling distributed frame: {e}")
    
    def on_distributed_detection(detection_data):
        """Callback for distributed detection events."""
        try:
            detection_info = {
                'stream_id': detection_data['stream_id'],
                'frame_number': detection_data['frame_number'],
                'detections': detection_data['detections'],
                'timestamp': detection_data['timestamp']
            }
            socketio.emit('distributed_detection_update', detection_info)
            
        except Exception as e:
            logger.error(f"Error handling distributed detection: {e}")
    
    def on_face_analysis_detection(detection_data):
        """Callback for face analysis detection events."""
        try:
            socketio.emit('face_analysis_detection', detection_data)
            
        except Exception as e:
            logger.error(f"Error handling face analysis detection: {e}")
    
    def on_client_change(change_type, client):
        """Callback for client changes."""
        try:
            client_info = {
                'change_type': change_type,
                'client': client.get_status(),
                'timestamp': datetime.now().isoformat()
            }
            socketio.emit('distributed_client_change', client_info)
            
        except Exception as e:
            logger.error(f"Error handling client change: {e}")
    
    # Register callbacks
    distributed_manager.add_frame_callback(on_distributed_frame)
    distributed_manager.add_detection_callback(on_distributed_detection)
    distributed_manager.add_detection_callback(on_face_analysis_detection)  # For face analysis
    distributed_manager.add_client_callback(on_client_change)
    
    logger.info("Distributed camera manager callbacks setup complete")

# Setup distributed manager callbacks
setup_distributed_manager_callbacks()


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/distributed')
def distributed():
    """Distributed camera system page."""
    return render_template('distributed.html')


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


@app.route('/api/ai/summary')
def get_ai_security_summary():
    """Get AI-generated summary of recent security events and snapshots."""
    try:
        # Get recent timeline events with snapshots
        if not web_processor.processor or not web_processor.processor.get_timeline_manager():
            return jsonify({
                'summary': 'No security data available. Start video processing to begin monitoring.',
                'recent_events': [],
                'security_level': 'normal',
                'last_updated': datetime.now().isoformat()
            })
        
        timeline_manager = web_processor.processor.get_timeline_manager()
        recent_events = timeline_manager.get_events(limit=20)
        
        # Filter events with snapshots and generate descriptions
        snapshot_events = []
        for event in recent_events:
            if event.get('snapshot_path'):
                # Generate description for each snapshot event
                objects = event.get('objects', [])
                object_descriptions = []
                for obj in objects:
                    object_descriptions.append(f"{obj['class_name']} (confidence: {obj['confidence']:.2f})")
                
                event_description = {
                    'event_id': event['event_id'],
                    'timestamp': event['timestamp'],
                    'source': event['video_source'],
                    'objects_detected': object_descriptions,
                    'summary': f"Detected {len(objects)} objects: {', '.join([obj['class_name'] for obj in objects])}",
                    'snapshot_path': event['snapshot_path'],
                    'confidence_scores': [obj['confidence'] for obj in objects] if objects else []
                }
                snapshot_events.append(event_description)
        
        # Generate overall security summary
        total_events = len(snapshot_events)
        if total_events == 0:
            summary = "No security events detected. All systems normal."
            security_level = "normal"
        else:
            recent_count = len([e for e in snapshot_events if 
                              (datetime.now() - datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00'))).total_seconds() < 3600])
            
            # Analyze security level based on recent activity
            if recent_count > 10:
                security_level = "high_activity"
                summary = f"High security activity detected. {recent_count} events in the last hour. Monitor closely."
            elif recent_count > 5:
                security_level = "elevated"
                summary = f"Elevated security activity. {recent_count} events in the last hour."
            else:
                security_level = "normal"
                summary = f"Normal security monitoring. {total_events} total events detected."
        
        return jsonify({
            'summary': summary,
            'security_level': security_level,
            'recent_events': snapshot_events[:10],  # Return top 10 most recent
            'total_events': total_events,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error generating AI security summary: {e}")
        return jsonify({
            'summary': 'Unable to generate security summary at this time.',
            'security_level': 'unknown',
            'recent_events': [],
            'error': str(e),
            'last_updated': datetime.now().isoformat()
        }), 500


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


# Distributed Camera Management SocketIO Events
@socketio.on('client_register')
def handle_client_register(data):
    """Handle camera client registration."""
    try:
        client_id = data.get('client_id')
        client_type = data.get('client_type', 'camera')
        
        if not client_id:
            emit('error', {'message': 'Client ID required'})
            return
        
        client = distributed_manager.register_client(client_id, client_type)
        emit('client_registered', {
            'client_id': client_id,
            'status': 'success',
            'message': f'Client {client_id} registered successfully'
        })
        
        logger.info(f"✅ Camera client registered: {client_id}")
        
    except Exception as e:
        logger.error(f"Error registering client: {e}")
        emit('error', {'message': str(e)})


@socketio.on('camera_info')
def handle_camera_info(data):
    """Handle camera information from client."""
    try:
        client_id = data.get('client_id')
        camera_info = data.get('cameras', {})
        
        if not client_id:
            emit('error', {'message': 'Client ID required'})
            return
        
        distributed_manager.add_camera_info(client_id, {'cameras': camera_info})
        
        logger.info(f"📹 Camera info received from {client_id}: {len(camera_info)} cameras")
        
    except Exception as e:
        logger.error(f"Error handling camera info: {e}")
        emit('error', {'message': str(e)})


@socketio.on('camera_frame')
def handle_camera_frame(data):
    """Handle camera frame from client."""
    try:
        client_id = data.get('client_id')
        camera_index = data.get('camera_index')
        frame_data = data.get('frame_data')
        
        if not all([client_id, camera_index is not None, frame_data]):
            return
        
        success = distributed_manager.handle_camera_frame(client_id, camera_index, frame_data)
        
        if not success:
            logger.warning(f"Failed to process frame from {client_id}, camera {camera_index}")
        
    except Exception as e:
        logger.error(f"Error handling camera frame: {e}")


@socketio.on('start_streaming')
def handle_start_streaming(data):
    """Handle start streaming request."""
    try:
        client_id = data.get('client_id')
        camera_index = data.get('camera_index', 0)
        
        if not client_id:
            emit('error', {'message': 'Client ID required'})
            return
        
        # Update client heartbeat
        distributed_manager.update_client_heartbeat(client_id)
        
        # Send start streaming command to client
        socketio.emit('start_streaming', {
            'camera_index': camera_index
        }, room=client_id)
        
        logger.info(f"📡 Start streaming request sent to {client_id}, camera {camera_index}")
        
    except Exception as e:
        logger.error(f"Error starting streaming: {e}")
        emit('error', {'message': str(e)})


@socketio.on('stop_streaming')
def handle_stop_streaming(data):
    """Handle stop streaming request."""
    try:
        client_id = data.get('client_id')
        camera_index = data.get('camera_index', 0)
        
        if not client_id:
            emit('error', {'message': 'Client ID required'})
            return
        
        # Send stop streaming command to client
        socketio.emit('stop_streaming', {
            'camera_index': camera_index
        }, room=client_id)
        
        logger.info(f"⏹️ Stop streaming request sent to {client_id}, camera {camera_index}")
        
    except Exception as e:
        logger.error(f"Error stopping streaming: {e}")
        emit('error', {'message': str(e)})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {request.sid}")


# Camera Detection API Endpoints
@app.route('/api/camera_detection/start', methods=['POST'])
def start_camera_detection():
    """Start camera-based offender detection."""
    try:
        data = request.get_json() or {}
        camera_index = data.get('camera_index', 0)
        detection_interval = data.get('detection_interval', 2.0)
        confidence_threshold = data.get('confidence_threshold', 0.3)
        
        # Configure service
        camera_detection_service.set_detection_interval(detection_interval)
        camera_detection_service.set_confidence_threshold(confidence_threshold)
        
        # Start detection
        if camera_detection_service.start_detection(camera_index):
            return jsonify({
                'status': 'started',
                'camera_index': camera_index,
                'detection_interval': detection_interval,
                'confidence_threshold': confidence_threshold
            })
        else:
            return jsonify({'error': 'Failed to start camera detection'}), 500
            
    except Exception as e:
        logger.error(f"Error starting camera detection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/camera_detection/stop', methods=['POST'])
def stop_camera_detection():
    """Stop camera-based offender detection."""
    try:
        camera_detection_service.stop_detection()
        return jsonify({'status': 'stopped'})
    except Exception as e:
        logger.error(f"Error stopping camera detection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/camera_detection/pause', methods=['POST'])
def pause_camera_detection():
    """Pause camera-based offender detection."""
    try:
        camera_detection_service.pause_detection()
        return jsonify({'status': 'paused'})
    except Exception as e:
        logger.error(f"Error pausing camera detection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/camera_detection/resume', methods=['POST'])
def resume_camera_detection():
    """Resume camera-based offender detection."""
    try:
        camera_detection_service.resume_detection()
        return jsonify({'status': 'resumed'})
    except Exception as e:
        logger.error(f"Error resuming camera detection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/camera_detection/status')
def get_camera_detection_status():
    """Get camera detection service status."""
    try:
        status = camera_detection_service.get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting camera detection status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/camera_detection/stats')
def get_camera_detection_stats():
    """Get camera detection statistics."""
    try:
        stats = camera_detection_service.get_detection_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting camera detection stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/camera_detection/recent_detections')
def get_recent_detections():
    """Get recent detection results."""
    try:
        limit = request.args.get('limit', 10, type=int)
        detections = camera_detection_service.get_recent_detections(limit)
        return jsonify({
            'detections': detections,
            'count': len(detections)
        })
    except Exception as e:
        logger.error(f"Error getting recent detections: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/camera_detection/test_camera/<int:camera_index>')
def test_camera_detection(camera_index):
    """Test camera for detection capabilities."""
    try:
        test_result = camera_detection_service.test_camera(camera_index)
        return jsonify(test_result)
    except Exception as e:
        logger.error(f"Error testing camera {camera_index}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/camera_detection/discover_cameras')
def discover_cameras_for_detection():
    """Discover cameras available for detection."""
    try:
        max_cameras = request.args.get('max_cameras', 5, type=int)
        cameras = camera_detection_service.discover_cameras(max_cameras)
        return jsonify({
            'cameras': cameras,
            'count': len(cameras)
        })
    except Exception as e:
        logger.error(f"Error discovering cameras: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/camera_detection/detect_image', methods=['POST'])
def detect_offender_in_image():
    """Detect offenders in an uploaded image."""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file:
            # Secure filename and save
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Get detection parameters
            threshold = float(request.form.get('threshold', 0.3))
            
            # Run detection
            image_matcher = get_improved_matcher()
            results = image_matcher.identify_person_in_image(filepath, threshold=threshold)
            
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
            
            return jsonify({
                'results': results,
                'count': len(results),
                'threshold': threshold
            })
        else:
            return jsonify({'error': 'Invalid file'}), 400
            
    except Exception as e:
        logger.error(f"Error detecting offenders in image: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/camera_detection/database_stats')
def get_detection_database_stats():
    """Get database statistics for detection."""
    try:
        image_matcher = get_improved_matcher()
        stats = image_matcher.get_database_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return jsonify({'error': str(e)}), 500


# Continuous Sex Offender Detection API Endpoints
@app.route('/api/sex_offender_detection/start', methods=['POST'])
def start_sex_offender_detection():
    """Start continuous sex offender detection."""
    try:
        data = request.get_json() or {}
        camera_index = data.get('camera_index', 0)
        detection_interval = data.get('detection_interval', 2.0)
        confidence_threshold = data.get('confidence_threshold', 0.3)
        
        # Configure service
        continuous_sex_offender_detector.set_detection_interval(detection_interval)
        continuous_sex_offender_detector.set_confidence_threshold(confidence_threshold)
        
        # Start detection
        if continuous_sex_offender_detector.start_detection(camera_index):
            return jsonify({
                'status': 'started',
                'camera_index': camera_index,
                'detection_interval': detection_interval,
                'confidence_threshold': confidence_threshold,
                'message': 'Continuous sex offender detection started'
            })
        else:
            return jsonify({'error': 'Failed to start sex offender detection'}), 500
            
    except Exception as e:
        logger.error(f"Error starting sex offender detection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sex_offender_detection/stop', methods=['POST'])
def stop_sex_offender_detection():
    """Stop continuous sex offender detection."""
    try:
        continuous_sex_offender_detector.stop_detection()
        return jsonify({'status': 'stopped', 'message': 'Sex offender detection stopped'})
    except Exception as e:
        logger.error(f"Error stopping sex offender detection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sex_offender_detection/pause', methods=['POST'])
def pause_sex_offender_detection():
    """Pause continuous sex offender detection."""
    try:
        continuous_sex_offender_detector.pause_detection()
        return jsonify({'status': 'paused', 'message': 'Sex offender detection paused'})
    except Exception as e:
        logger.error(f"Error pausing sex offender detection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sex_offender_detection/resume', methods=['POST'])
def resume_sex_offender_detection():
    """Resume continuous sex offender detection."""
    try:
        continuous_sex_offender_detector.resume_detection()
        return jsonify({'status': 'resumed', 'message': 'Sex offender detection resumed'})
    except Exception as e:
        logger.error(f"Error resuming sex offender detection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sex_offender_detection/status')
def get_sex_offender_detection_status():
    """Get sex offender detection service status."""
    try:
        status = continuous_sex_offender_detector.get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting sex offender detection status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sex_offender_detection/stats')
def get_sex_offender_detection_stats():
    """Get sex offender detection statistics."""
    try:
        stats = continuous_sex_offender_detector.get_detection_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting sex offender detection stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sex_offender_detection/recent_detections')
def get_recent_sex_offender_detections():
    """Get recent sex offender detection results."""
    try:
        limit = request.args.get('limit', 10, type=int)
        detections = continuous_sex_offender_detector.get_recent_detections(limit)
        return jsonify({
            'detections': detections,
            'count': len(detections)
        })
    except Exception as e:
        logger.error(f"Error getting recent sex offender detections: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sex_offender_detection/test_camera/<int:camera_index>')
def test_sex_offender_detection_camera(camera_index):
    """Test camera for sex offender detection capabilities."""
    try:
        test_result = continuous_sex_offender_detector.test_camera(camera_index)
        return jsonify(test_result)
    except Exception as e:
        logger.error(f"Error testing camera {camera_index} for sex offender detection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sex_offender_detection/discover_cameras')
def discover_cameras_for_sex_offender_detection():
    """Discover cameras available for sex offender detection."""
    try:
        max_cameras = request.args.get('max_cameras', 5, type=int)
        cameras = continuous_sex_offender_detector.discover_cameras(max_cameras)
        return jsonify({
            'cameras': cameras,
            'count': len(cameras)
        })
    except Exception as e:
        logger.error(f"Error discovering cameras for sex offender detection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sex_offender_detection/detect_image', methods=['POST'])
def detect_sex_offenders_in_image():
    """Detect sex offenders in an uploaded image."""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file:
            # Secure filename and save
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"sex_offender_detection_{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Get detection parameters
            threshold = float(request.form.get('threshold', 0.3))
            
            # Run sex offender detection
            results = continuous_sex_offender_detector.detect_in_image(filepath, threshold=threshold)
            
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
            
            return jsonify({
                'results': results,
                'count': len(results),
                'threshold': threshold,
                'message': f'Found {len(results)} potential sex offender matches'
            })
        else:
            return jsonify({'error': 'Invalid file'}), 400
            
    except Exception as e:
        logger.error(f"Error detecting sex offenders in image: {e}")
        return jsonify({'error': str(e)}), 500


# Snapshot Analysis API Endpoints
@app.route('/api/snapshot/analyze', methods=['POST'])
def analyze_snapshot():
    """Analyze a snapshot for sex offenders and family members."""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file:
            # Secure filename and save
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"snapshot_analysis_{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Run snapshot analysis
            analysis_result = snapshot_analysis_service.analyze_snapshot(filepath)
            
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
            
            return jsonify(analysis_result)
        else:
            return jsonify({'error': 'Invalid file'}), 400
            
    except Exception as e:
        logger.error(f"Error analyzing snapshot: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/snapshot/capture_family_photo', methods=['POST'])
def capture_family_photo():
    """Capture current frame for family member enrollment."""
    try:
        data = request.get_json() or {}
        name = data.get('name')
        
        if not name:
            return jsonify({'error': 'Family member name required'}), 400
        
        # Get current frame from the video processor
        # This would need to be implemented based on your current frame capture mechanism
        # For now, we'll return an error indicating this needs to be implemented
        return jsonify({
            'error': 'Frame capture not implemented yet',
            'message': 'This feature requires integration with the current video processor'
        }), 501
            
    except Exception as e:
        logger.error(f"Error capturing family photo: {e}")
        return jsonify({'error': str(e)}), 500


# Family Member Management API Endpoints
@app.route('/api/family/analysis/members')
def get_family_members_analysis():
    """Get all family members from snapshot analysis service."""
    try:
        family_members = snapshot_analysis_service.get_family_members()
        stats = snapshot_analysis_service.get_family_member_stats()
        
        return jsonify({
            'family_members': family_members,
            'stats': stats,
            'count': len(family_members)
        })
    except Exception as e:
        logger.error(f"Error getting family members: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/family/analysis/members', methods=['POST'])
def add_family_member_analysis():
    """Add a family member with photo."""
    try:
        if 'photo' not in request.files:
            return jsonify({'error': 'No photo file provided'}), 400
        
        file = request.files['photo']
        name = request.form.get('name')
        
        if not name:
            return jsonify({'error': 'Name required'}), 400
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file:
            # Secure filename and save
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"family_{name}_{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Add to family members
            success = snapshot_analysis_service.add_family_member(name, filepath)
            
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
            
            if success:
                return jsonify({
                    'status': 'added',
                    'name': name,
                    'message': f'Family member {name} added successfully'
                })
            else:
                return jsonify({'error': 'Failed to add family member'}), 500
        else:
            return jsonify({'error': 'Invalid file'}), 400
            
    except Exception as e:
        logger.error(f"Error adding family member: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/family/analysis/members/<name>', methods=['DELETE'])
def remove_family_member_analysis(name):
    """Remove a family member."""
    try:
        success = snapshot_analysis_service.remove_family_member(name)
        
        if success:
            return jsonify({
                'status': 'removed',
                'name': name,
                'message': f'Family member {name} removed successfully'
            })
        else:
            return jsonify({'error': 'Family member not found'}), 404
            
    except Exception as e:
        logger.error(f"Error removing family member: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/snapshot/analysis/stats')
def get_snapshot_analysis_stats():
    """Get snapshot analysis statistics."""
    try:
        stats = snapshot_analysis_service.get_analysis_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting snapshot analysis stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/snapshot/analysis/settings', methods=['POST'])
def update_snapshot_analysis_settings():
    """Update snapshot analysis settings."""
    try:
        data = request.get_json() or {}
        
        sex_offender_threshold = data.get('sex_offender_threshold')
        family_member_threshold = data.get('family_member_threshold')
        
        if sex_offender_threshold is not None:
            snapshot_analysis_service.set_sex_offender_threshold(sex_offender_threshold)
        
        if family_member_threshold is not None:
            snapshot_analysis_service.set_family_member_threshold(family_member_threshold)
        
        return jsonify({
            'status': 'updated',
            'settings': {
                'sex_offender_threshold': sex_offender_threshold,
                'family_member_threshold': family_member_threshold
            }
        })
    except Exception as e:
        logger.error(f"Error updating snapshot analysis settings: {e}")
        return jsonify({'error': str(e)}), 500


# Distributed Camera Management API Endpoints
@app.route('/api/distributed/clients')
def get_distributed_clients():
    """Get all connected camera clients."""
    try:
        clients_status = distributed_manager.get_all_clients_status()
        return jsonify({
            'clients': clients_status,
            'count': len(clients_status)
        })
    except Exception as e:
        logger.error(f"Error getting distributed clients: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/distributed/clients/<client_id>')
def get_distributed_client(client_id):
    """Get specific client status."""
    try:
        client_status = distributed_manager.get_client_status(client_id)
        if not client_status:
            return jsonify({'error': 'Client not found'}), 404
        
        return jsonify(client_status)
    except Exception as e:
        logger.error(f"Error getting client {client_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/distributed/processing')
def get_processing_status():
    """Get processing status for all streams."""
    try:
        processing_status = distributed_manager.get_processing_status()
        return jsonify(processing_status)
    except Exception as e:
        logger.error(f"Error getting processing status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/distributed/start_processing', methods=['POST'])
def start_distributed_processing():
    """Start processing a camera stream."""
    try:
        data = request.get_json()
        client_id = data.get('client_id')
        camera_index = data.get('camera_index', 0)
        confidence = data.get('confidence', 0.25)
        enable_tracking = data.get('enable_tracking', True)
        target_classes = data.get('target_classes', None)
        
        if not client_id:
            return jsonify({'error': 'Client ID required'}), 400
        
        # Generate stream ID
        stream_id = f"{client_id}_{camera_index}"
        
        success = distributed_manager.start_processing_stream(
            stream_id=stream_id,
            client_id=client_id,
            camera_index=camera_index,
            confidence=confidence,
            enable_tracking=enable_tracking,
            target_classes=target_classes
        )
        
        if success:
            return jsonify({
                'status': 'started',
                'stream_id': stream_id,
                'client_id': client_id,
                'camera_index': camera_index
            })
        else:
            return jsonify({'error': 'Failed to start processing'}), 500
            
    except Exception as e:
        logger.error(f"Error starting distributed processing: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/distributed/stop_processing', methods=['POST'])
def stop_distributed_processing():
    """Stop processing a camera stream."""
    try:
        data = request.get_json()
        stream_id = data.get('stream_id')
        
        if not stream_id:
            return jsonify({'error': 'Stream ID required'}), 400
        
        distributed_manager.stop_processing_stream(stream_id)
        
        return jsonify({
            'status': 'stopped',
            'stream_id': stream_id
        })
        
    except Exception as e:
        logger.error(f"Error stopping distributed processing: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/distributed/stats')
def get_distributed_stats():
    """Get distributed system statistics."""
    try:
        stats = distributed_manager.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting distributed stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/distributed/cleanup', methods=['POST'])
def cleanup_inactive_clients():
    """Clean up inactive clients."""
    try:
        timeout = request.args.get('timeout', 30, type=int)
        distributed_manager.cleanup_inactive_clients(timeout)
        
        return jsonify({
            'status': 'cleanup_completed',
            'timeout_seconds': timeout
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up inactive clients: {e}")
        return jsonify({'error': str(e)}), 500


# Simple HTTP endpoint for camera frames
@app.route('/api/send_frame', methods=['POST'])
def receive_frame():
    """Receive frame from simple camera sender."""
    try:
        data = request.get_json()
        client_id = data.get('client_id')
        camera_index = data.get('camera_index', 0)
        frame_data = data.get('frame_data')
        frame_number = data.get('frame_number', 0)
        
        if not all([client_id, frame_data]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Register client if not exists
        if client_id not in [c.client_id for c in distributed_manager.clients.values()]:
            distributed_manager.register_client(client_id, "camera")
        
        # Handle the frame
        success = distributed_manager.handle_camera_frame(client_id, camera_index, frame_data)
        
        if success:
            return jsonify({'status': 'received', 'frame_number': frame_number})
        else:
            return jsonify({'error': 'Failed to process frame'}), 500
            
    except Exception as e:
        logger.error(f"Error receiving frame: {e}")
        return jsonify({'error': str(e)}), 500


# Family Member Management API Endpoints
@app.route('/api/family/members')
def get_family_members():
    """Get all family members."""
    try:
        family_members = distributed_manager.get_family_members()
        return jsonify({
            'family_members': family_members,
            'count': len(family_members)
        })
    except Exception as e:
        logger.error(f"Error getting family members: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/family/members', methods=['POST'])
def add_family_member():
    """Add a family member."""
    try:
        data = request.get_json()
        name = data.get('name')
        image_path = data.get('image_path')
        
        if not name or not image_path:
            return jsonify({'error': 'Name and image_path required'}), 400
        
        success = distributed_manager.add_family_member(name, image_path)
        
        if success:
            return jsonify({
                'status': 'added',
                'name': name,
                'message': f'Family member {name} added successfully'
            })
        else:
            return jsonify({'error': 'Failed to add family member'}), 500
            
    except Exception as e:
        logger.error(f"Error adding family member: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/family/members/<name>', methods=['DELETE'])
def remove_family_member(name):
    """Remove a family member."""
    try:
        success = distributed_manager.remove_family_member(name)
        
        if success:
            return jsonify({
                'status': 'removed',
                'name': name,
                'message': f'Family member {name} removed successfully'
            })
        else:
            return jsonify({'error': 'Family member not found'}), 404
            
    except Exception as e:
        logger.error(f"Error removing family member: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/family/upload', methods=['POST'])
def upload_family_member_photo():
    """Upload photo for family member."""
    try:
        if 'photo' not in request.files:
            return jsonify({'error': 'No photo file provided'}), 400
        
        file = request.files['photo']
        name = request.form.get('name')
        
        if not name:
            return jsonify({'error': 'Name required'}), 400
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file:
            # Secure filename and save
            from werkzeug.utils import secure_filename
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"family_{name}_{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Add to family members
            success = distributed_manager.add_family_member(name, filepath)
            
            if success:
                return jsonify({
                    'status': 'uploaded',
                    'name': name,
                    'filepath': filepath,
                    'message': f'Family member {name} added successfully'
                })
            else:
                return jsonify({'error': 'Failed to add family member'}), 500
        else:
            return jsonify({'error': 'Invalid file'}), 400
            
    except Exception as e:
        logger.error(f"Error uploading family member photo: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Initialize video processor
    if not web_processor.initialize():
        logger.error("Failed to initialize video processor")
        sys.exit(1)
    
    # Setup notification system
    setup_notification_callbacks()
    
    # Start Flask-SocketIO app
    socketio.run(app, debug=True, host='0.0.0.0', port=5002, allow_unsafe_werkzeug=True)
