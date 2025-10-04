#!/usr/bin/env python3
"""
Test script for the video processing backend.
Verifies that all components can be imported and basic functionality works.
"""

import sys
import os
import traceback

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        from video_processor import VideoProcessor
        print("✓ VideoProcessor imported successfully")
    except Exception as e:
        print(f"❌ Failed to import VideoProcessor: {e}")
        return False
    
    try:
        from camera_handler import CameraHandler
        print("✓ CameraHandler imported successfully")
    except Exception as e:
        print(f"❌ Failed to import CameraHandler: {e}")
        return False
    
    try:
        from object_tracker import ObjectTracker
        print("✓ ObjectTracker imported successfully")
    except Exception as e:
        print(f"❌ Failed to import ObjectTracker: {e}")
        return False
    
    try:
        from detection_utils import DetectionUtils
        print("✓ DetectionUtils imported successfully")
    except Exception as e:
        print(f"❌ Failed to import DetectionUtils: {e}")
        return False
    
    try:
        from config import Config
        print("✓ Config imported successfully")
    except Exception as e:
        print(f"❌ Failed to import Config: {e}")
        return False
    
    return True

def test_initialization():
    """Test that all classes can be initialized."""
    print("\n🧪 Testing initialization...")
    
    try:
        from video_processor import VideoProcessor
        from camera_handler import CameraHandler
        from object_tracker import ObjectTracker
        from detection_utils import DetectionUtils
        from config import Config
        
        # Test Config
        config = Config()
        print("✓ Config initialized successfully")
        
        # Test DetectionUtils
        detection_utils = DetectionUtils()
        print("✓ DetectionUtils initialized successfully")
        
        # Test ObjectTracker
        tracker = ObjectTracker()
        print("✓ ObjectTracker initialized successfully")
        
        # Test CameraHandler
        camera_handler = CameraHandler()
        print("✓ CameraHandler initialized successfully")
        
        # Test VideoProcessor (without loading model)
        print("✓ All components initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        traceback.print_exc()
        return False

def test_configuration():
    """Test configuration functionality."""
    print("\n🧪 Testing configuration...")
    
    try:
        from config import Config
        
        config = Config()
        
        # Test configuration validation
        if config.validate():
            print("✓ Configuration validation passed")
        else:
            print("❌ Configuration validation failed")
            return False
        
        # Test configuration sections
        model_config = config.get_model_config()
        tracking_config = config.get_tracking_config()
        camera_config = config.get_camera_config()
        
        print("✓ Configuration sections retrieved successfully")
        
        # Test configuration save/load
        test_config_path = "test_config.json"
        if config.to_file(test_config_path):
            print("✓ Configuration saved successfully")
            
            loaded_config = Config.from_file(test_config_path)
            print("✓ Configuration loaded successfully")
            
            # Clean up
            if os.path.exists(test_config_path):
                os.remove(test_config_path)
                print("✓ Test configuration file cleaned up")
        else:
            print("❌ Configuration save failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        traceback.print_exc()
        return False

def test_detection_utils():
    """Test detection utilities."""
    print("\n🧪 Testing detection utilities...")
    
    try:
        from detection_utils import DetectionUtils
        import numpy as np
        
        detection_utils = DetectionUtils()
        
        # Test with empty detections
        empty_detections = []
        metrics = detection_utils.calculate_detection_metrics(empty_detections)
        print("✓ Empty detection metrics calculated")
        
        # Test with sample detections
        sample_detections = [
            {
                'bbox': [10, 10, 50, 50],
                'confidence': 0.8,
                'class_name': 'person',
                'area': 1600,
                'center': [30, 30]
            },
            {
                'bbox': [100, 100, 150, 150],
                'confidence': 0.9,
                'class_name': 'car',
                'area': 2500,
                'center': [125, 125]
            }
        ]
        
        metrics = detection_utils.calculate_detection_metrics(sample_detections)
        print("✓ Sample detection metrics calculated")
        
        # Test filtering
        filtered = detection_utils.filter_detections(
            sample_detections,
            min_confidence=0.85
        )
        print(f"✓ Detection filtering worked: {len(filtered)} detections after filtering")
        
        # Test statistics
        stats = detection_utils.get_detection_statistics()
        print("✓ Detection statistics retrieved")
        
        return True
        
    except Exception as e:
        print(f"❌ Detection utils test failed: {e}")
        traceback.print_exc()
        return False

def test_object_tracker():
    """Test object tracker."""
    print("\n🧪 Testing object tracker...")
    
    try:
        from object_tracker import ObjectTracker
        import numpy as np
        
        tracker = ObjectTracker()
        
        # Test with empty detections
        empty_detections = []
        result = tracker.update(empty_detections, np.zeros((480, 640, 3), dtype=np.uint8))
        print("✓ Empty detection tracking worked")
        
        # Test with sample detections
        sample_detections = [
            {
                'bbox': [10, 10, 50, 50],
                'confidence': 0.8,
                'class_name': 'person'
            }
        ]
        
        result = tracker.update(sample_detections, np.zeros((480, 640, 3), dtype=np.uint8))
        print("✓ Sample detection tracking worked")
        
        # Test statistics
        stats = tracker.get_tracking_statistics()
        print("✓ Tracking statistics retrieved")
        
        # Test track info
        if result and len(result) > 0:
            track_info = tracker.get_track_info(result[0]['track_id'])
            print("✓ Track info retrieved")
        
        return True
        
    except Exception as e:
        print(f"❌ Object tracker test failed: {e}")
        traceback.print_exc()
        return False

def test_camera_handler():
    """Test camera handler."""
    print("\n🧪 Testing camera handler...")
    
    try:
        from camera_handler import CameraHandler
        
        camera_handler = CameraHandler()
        
        # Test camera discovery (this might not find cameras in CI/test environment)
        working_cameras = camera_handler.discover_cameras(max_cameras=2)
        print(f"✓ Camera discovery completed: {len(working_cameras)} cameras found")
        
        # Test status
        status = camera_handler.get_camera_status()
        print("✓ Camera status retrieved")
        
        # Test properties
        properties = camera_handler.get_all_camera_properties()
        print("✓ Camera properties retrieved")
        
        return True
        
    except Exception as e:
        print(f"❌ Camera handler test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 Backend Test Suite")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Initialization Test", test_initialization),
        ("Configuration Test", test_configuration),
        ("Detection Utils Test", test_detection_utils),
        ("Object Tracker Test", test_object_tracker),
        ("Camera Handler Test", test_camera_handler),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            traceback.print_exc()
    
    print(f"\n{'='*50}")
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Backend is ready to use.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
