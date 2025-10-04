#!/usr/bin/env python3
"""
Test script to verify auto-reporter functionality.
"""

import os
import sys
import json
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_auto_reporter_workflow():
    """Test the complete auto-reporter workflow."""
    print("Testing Auto-Reporter Workflow...")
    
    try:
        from backend.auto_gemini_reporter import get_auto_reporter
        import cv2
        import numpy as np
        
        # Get the auto reporter
        reporter = get_auto_reporter()
        print(f"[OK] Got auto reporter: {reporter}")
        print(f"   - Enabled: {reporter.enabled}")
        
        if not reporter.enabled:
            print("[INFO] Enabling auto reporter...")
            reporter.enable()
            print(f"   - After enable: {reporter.enabled}")
        
        # Create a test event data
        event_data = {
            'event_id': 'test_event_123',
            'timestamp': '2025-10-04T16:50:00',
            'video_source': 'camera:0',
            'frame_number': 100,
            'objects': [
                {
                    'class_name': 'person',
                    'track_id': 1,
                    'confidence': 0.95,
                    'bbox': [100, 100, 200, 300]
                },
                {
                    'class_name': 'car',
                    'track_id': 2,
                    'confidence': 0.87,
                    'bbox': [300, 150, 500, 250]
                }
            ]
        }
        
        # Create a test snapshot image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        test_image[100:300, 100:200] = [0, 255, 0]  # Green rectangle (person)
        test_image[150:250, 300:500] = [255, 0, 0]  # Blue rectangle (car)
        
        snapshot_path = "test_snapshot.jpg"
        cv2.imwrite(snapshot_path, test_image)
        print(f"[OK] Created test snapshot: {snapshot_path}")
        
        # Queue the report
        print("[INFO] Queueing report...")
        reporter.queue_report(event_data, snapshot_path)
        
        # Wait a bit for processing
        print("[INFO] Waiting for report generation...")
        time.sleep(5)
        
        # Check if report was generated
        report = reporter.get_report('test_event_123')
        if report:
            print("[OK] Report generated successfully!")
            print(f"   - Report: {json.dumps(report, indent=2)}")
            
            # Clean up
            os.remove(snapshot_path)
            return True
        else:
            print("[ERROR] No report generated")
            os.remove(snapshot_path)
            return False
            
    except Exception as e:
        print(f"[ERROR] Auto reporter workflow test failed: {e}")
        # Clean up
        if os.path.exists("test_snapshot.jpg"):
            os.remove("test_snapshot.jpg")
        return False

def main():
    """Run the auto reporter test."""
    print("Auto-Reporter Test")
    print("=" * 40)
    
    success = test_auto_reporter_workflow()
    
    print("\n" + "=" * 40)
    if success:
        print("[SUCCESS] Auto-reporter workflow is working!")
    else:
        print("[ERROR] Auto-reporter workflow failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
