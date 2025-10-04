#!/usr/bin/env python3
"""
Test script to demonstrate YOLOv8 class filtering functionality.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.surveillance_classes import get_available_class_sets, print_class_info
from backend.video_processor import VideoProcessor

def test_class_filtering():
    """Test class filtering functionality."""
    print("Testing YOLOv8 Class Filtering")
    print("=" * 50)
    
    # Show available class sets
    print_class_info()
    
    print("\n" + "=" * 50)
    print("Testing VideoProcessor with different class sets...")
    
    # Test with surveillance core classes
    print("\n1. Testing with SURVEILLANCE_CORE classes:")
    core_classes = get_available_class_sets()['core']
    print(f"   Classes: {core_classes}")
    
    try:
        processor = VideoProcessor(
            confidence_threshold=0.25,
            target_classes=core_classes
        )
        print("   ✅ VideoProcessor initialized successfully with core classes")
        print(f"   Target classes: {processor.target_classes}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test with traffic monitoring classes
    print("\n2. Testing with TRAFFIC_MONITORING classes:")
    traffic_classes = get_available_class_sets()['traffic']
    print(f"   Classes: {traffic_classes}")
    
    try:
        processor = VideoProcessor(
            confidence_threshold=0.25,
            target_classes=traffic_classes
        )
        print("   ✅ VideoProcessor initialized successfully with traffic classes")
        print(f"   Target classes: {processor.target_classes}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test with people only
    print("\n3. Testing with PEOPLE_ONLY classes:")
    people_classes = get_available_class_sets()['people_only']
    print(f"   Classes: {people_classes}")
    
    try:
        processor = VideoProcessor(
            confidence_threshold=0.25,
            target_classes=people_classes
        )
        print("   ✅ VideoProcessor initialized successfully with people-only classes")
        print(f"   Target classes: {processor.target_classes}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test with all classes (default)
    print("\n4. Testing with ALL classes (default):")
    try:
        processor = VideoProcessor(
            confidence_threshold=0.25,
            target_classes=None  # No filtering
        )
        print("   ✅ VideoProcessor initialized successfully with all classes")
        print(f"   Target classes: {processor.target_classes}")
        print(f"   All available classes: {list(processor.model.names.values())}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("Class filtering test completed!")
    print("\nBenefits of class filtering:")
    print("- Faster processing (fewer detections to process)")
    print("- Reduced false positives")
    print("- Better accuracy for specific use cases")
    print("- Lower computational overhead")
    print("- More focused detection results")

if __name__ == "__main__":
    test_class_filtering()
