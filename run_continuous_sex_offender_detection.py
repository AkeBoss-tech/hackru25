#!/usr/bin/env python3
"""
Command-line interface for Continuous Sex Offender Detection
Provides a simple way to start and monitor sex offender detection
"""

import os
import sys
import time
import signal
import argparse
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

try:
    from backend.continuous_sex_offender_detector import get_continuous_sex_offender_detector
except ImportError as e:
    print(f"Error importing backend modules: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

class SexOffenderDetectionCLI:
    """Command-line interface for sex offender detection."""
    
    def __init__(self):
        self.detector = get_continuous_sex_offender_detector()
        self.running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\n🛑 Received signal {signum}, shutting down...")
        self.stop_detection()
        sys.exit(0)
    
    def print_header(self):
        """Print the application header."""
        print("🚨" + "=" * 58 + "🚨")
        print("🚨           CONTINUOUS SEX OFFENDER DETECTION           🚨")
        print("🚨" + "=" * 58 + "🚨")
        print()
        print("This application continuously monitors camera feeds for")
        print("known sex offenders and provides real-time alerts.")
        print()
    
    def print_controls(self):
        """Print control instructions."""
        print("📋 Controls:")
        print("  - Press Ctrl+C to stop detection")
        print("  - Detection runs automatically every 2 seconds")
        print("  - High confidence matches will be logged with alerts")
        print()
    
    def test_camera(self, camera_index=0):
        """Test camera functionality."""
        print(f"🧪 Testing camera {camera_index}...")
        
        test_result = self.detector.test_camera(camera_index)
        
        if test_result['success']:
            print("✅ Camera test successful!")
            print(f"   📹 Resolution: {test_result['frame_shape'][1]}x{test_result['frame_shape'][0]}")
            print(f"   👤 Face detection: {'✅ Working' if test_result['faces_detected'] >= 0 else '❌ Failed'}")
            print(f"   🚨 Sex offender detection: {'✅ Working' if test_result['sex_offender_detection_working'] else '❌ Failed'}")
            
            db_status = test_result['database_available']
            print(f"   🗄️ Databases: OpenCV={'✅' if db_status['opencv'] else '❌'}, Vector={'✅' if db_status['vector'] else '❌'}")
            return True
        else:
            print(f"❌ Camera test failed: {test_result['error']}")
            return False
    
    def discover_cameras(self):
        """Discover available cameras."""
        print("🔍 Discovering available cameras...")
        
        cameras = self.detector.discover_cameras(max_cameras=5)
        
        if cameras:
            print(f"✅ Found {len(cameras)} available cameras:")
            for camera in cameras:
                status = "✅ Ready" if camera['sex_offender_detection_working'] else "❌ Issues"
                print(f"   Camera {camera['id']}: {camera['frame_shape']} - {status}")
            return cameras
        else:
            print("❌ No cameras found or accessible")
            return []
    
    def start_detection(self, camera_index=0, interval=2.0, threshold=0.3):
        """Start continuous detection."""
        print(f"🚀 Starting continuous sex offender detection...")
        print(f"   📹 Camera: {camera_index}")
        print(f"   ⏱️ Detection interval: {interval} seconds")
        print(f"   🎯 Confidence threshold: {threshold}")
        print()
        
        # Configure detector
        self.detector.set_detection_interval(interval)
        self.detector.set_detection_interval(threshold)
        
        # Add callbacks for real-time feedback
        self.detector.add_detection_callback(self._on_detection)
        self.detector.add_alert_callback(self._on_alert)
        self.detector.add_status_callback(self._on_status_change)
        
        # Start detection
        if self.detector.start_detection(camera_index):
            self.running = True
            print("✅ Detection started successfully!")
            print()
            self._monitor_detection()
        else:
            print("❌ Failed to start detection")
            return False
    
    def stop_detection(self):
        """Stop detection."""
        if self.running:
            print("🛑 Stopping detection...")
            self.detector.stop_detection()
            self.running = False
            print("✅ Detection stopped")
    
    def _on_detection(self, results):
        """Callback for detection events."""
        if results:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] 🎯 Detected {len(results)} potential matches")
            
            for result in results:
                offender_info = result.get('offender_info', {})
                name = offender_info.get('name', result.get('offender_id', 'Unknown'))
                confidence = result['confidence']
                
                if confidence > 0.7:
                    print(f"          🚨 HIGH: {name} ({confidence:.3f})")
                elif confidence > 0.4:
                    print(f"          ⚠️ MED: {name} ({confidence:.3f})")
                else:
                    print(f"          💡 LOW: {name} ({confidence:.3f})")
    
    def _on_alert(self, alert_data):
        """Callback for high-confidence alerts."""
        offender_info = alert_data.get('offender_info', {})
        name = offender_info.get('name', 'Unknown')
        confidence = alert_data['confidence']
        severity = alert_data['severity']
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"\n🚨 [{timestamp}] CRITICAL ALERT - {severity} CONFIDENCE")
        print(f"🚨 SEX OFFENDER DETECTED: {name}")
        print(f"🚨 Confidence: {confidence:.3f}")
        print(f"🚨 Method: {alert_data.get('method', 'unknown')}")
        print("🚨" + "=" * 50)
    
    def _on_status_change(self, status_data):
        """Callback for status changes."""
        status = status_data.get('status', 'unknown')
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] Status: {status}")
    
    def _monitor_detection(self):
        """Monitor detection and show statistics."""
        try:
            start_time = time.time()
            last_stats_time = start_time
            
            while self.running:
                time.sleep(1)
                
                # Show periodic statistics
                if time.time() - last_stats_time >= 30:  # Every 30 seconds
                    self._show_stats()
                    last_stats_time = time.time()
                
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_detection()
    
    def _show_stats(self):
        """Show current statistics."""
        stats = self.detector.get_detection_stats()
        
        uptime = stats.get('uptime_seconds', 0)
        total_detections = stats.get('total_detections', 0)
        sex_offenders = stats.get('total_sex_offenders_detected', 0)
        high_conf = stats.get('high_confidence_matches', 0)
        medium_conf = stats.get('medium_confidence_matches', 0)
        low_conf = stats.get('low_confidence_matches', 0)
        
        print(f"\n📊 Statistics (uptime: {uptime:.0f}s):")
        print(f"   🎯 Total detections: {total_detections}")
        print(f"   🚨 Sex offenders detected: {sex_offenders}")
        print(f"   🔴 High confidence: {high_conf}")
        print(f"   🟡 Medium confidence: {medium_conf}")
        print(f"   🟢 Low confidence: {low_conf}")
        print()
    
    def run_interactive(self):
        """Run interactive mode."""
        self.print_header()
        
        # Test camera
        if not self.test_camera():
            print("❌ Camera test failed. Please check your camera setup.")
            return
        
        print()
        
        # Discover cameras
        cameras = self.discover_cameras()
        if not cameras:
            print("❌ No cameras available. Exiting.")
            return
        
        print()
        self.print_controls()
        
        # Start detection
        self.start_detection()
    
    def run_daemon(self, camera_index=0, interval=2.0, threshold=0.3):
        """Run in daemon mode (non-interactive)."""
        print(f"🚨 Starting sex offender detection daemon...")
        print(f"   Camera: {camera_index}, Interval: {interval}s, Threshold: {threshold}")
        
        if not self.test_camera(camera_index):
            print("❌ Camera test failed. Exiting.")
            return False
        
        # Add callbacks for logging
        self.detector.add_detection_callback(self._on_detection)
        self.detector.add_alert_callback(self._on_alert)
        
        # Start detection
        if self.detector.start_detection(camera_index):
            print("✅ Daemon started successfully!")
            self.running = True
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            finally:
                self.stop_detection()
            
            return True
        else:
            print("❌ Failed to start daemon")
            return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Continuous Sex Offender Detection')
    parser.add_argument('--camera', type=int, default=0, help='Camera index (default: 0)')
    parser.add_argument('--interval', type=float, default=2.0, help='Detection interval in seconds (default: 2.0)')
    parser.add_argument('--threshold', type=float, default=0.3, help='Confidence threshold (default: 0.3)')
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode (non-interactive)')
    parser.add_argument('--test', action='store_true', help='Test camera and exit')
    
    args = parser.parse_args()
    
    cli = SexOffenderDetectionCLI()
    
    if args.test:
        # Test mode
        cli.print_header()
        success = cli.test_camera(args.camera)
        sys.exit(0 if success else 1)
    elif args.daemon:
        # Daemon mode
        success = cli.run_daemon(args.camera, args.interval, args.threshold)
        sys.exit(0 if success else 1)
    else:
        # Interactive mode
        cli.run_interactive()

if __name__ == "__main__":
    main()
