#!/usr/bin/env python3
"""
Quick camera test for offender detection
Simple version to test camera functionality with improved detection
"""

import cv2
import numpy as np
import time
import os
from improved_image_matcher import ImprovedImageMatcher

def test_camera():
    """Test camera and basic detection"""
    print("🎥 Testing camera access...")
    
    # Try to open camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return False
    
    # Test camera reading
    ret, frame = cap.read()
    if not ret:
        print("❌ Cannot read from camera")
        cap.release()
        return False
    
    print(f"✅ Camera working! Resolution: {frame.shape[1]}x{frame.shape[0]}")
    cap.release()
    return True

def run_simple_detection():
    """Run simple live detection"""
    print("🔍 Starting simple live detection...")
    print("📝 Controls:")
    print("  - Press 'q' to quit")
    print("  - Press 's' to take screenshot")
    print("  - Press SPACE to pause/resume")
    print("  - Press 'd' to detect on current frame")
    print("  - Press 'r' to record person image")
    
    # Initialize detector
    try:
        detector = ImprovedImageMatcher()
        print("✅ Improved detector initialized")
    except Exception as e:
        print(f"❌ Failed to initialize detector: {e}")
        return
    
    # Open camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot open camera")
        return
    
    frame_count = 0
    paused = False
    last_detection_time = 0
    detection_results = []
    
    try:
        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # Simple display with frame info
                display_frame = frame.copy()
                
                # Add frame counter
                cv2.putText(display_frame, f"Frame: {frame_count}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Add detection results overlay
                if detection_results:
                    y_offset = 70
                    for i, result in enumerate(detection_results[:3]):  # Show top 3
                        name = result['offender_info'].get('name', result['offender_id'])
                        threat_lvl = result['offender_info'].get('level', result['offender_id'])
                        confidence = result['confidence']
                        method = result['method']
                        
                        # Color based on confidence
                        if confidence > 0.7:
                            color = (0, 0, 255)  # Red for high confidence
                            alert_text = f"🚨 HIGH: {name} ({confidence:.2f}, SEVERITY: {threat_lvl})"
                        elif confidence > 0.4:
                            color = (0, 255, 255)  # Yellow for medium
                            alert_text = f"⚠️ MED: {name} ({confidence:.2f}, SEVERITY: {threat_lvl})"
                        else:
                            color = (255, 255, 0)  # Cyan for low
                            alert_text = f"💡 LOW: {name} ({confidence:.2f}, SEVERITY: {threat_lvl})"
                        
                        cv2.putText(display_frame, alert_text, 
                                   (10, y_offset + i*30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                        
                        # Draw face region if available
                        if 'face_region' in result and result['face_region']:
                            x, y, w, h = result['face_region']
                            cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 3)
                
                # Add instructions
                cv2.putText(display_frame, "Press 'd' to detect, 'r' to record", 
                           (10, display_frame.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(display_frame, "Press 'q' to quit, 's' for screenshot", 
                           (10, display_frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                cv2.imshow('Quick Camera Test - Improved Detection', display_frame)
            
            # Handle keys
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"camera_capture_{timestamp}.jpg"
                cv2.imwrite(filename, display_frame)
                print(f"📸 Screenshot saved: {filename}")
            elif key == ord(' '):
                paused = not paused
                print("⏸️ Paused" if paused else "▶️ Resumed")
            elif key == ord('d'):
                # Manual detection
                current_time = time.time()
                if current_time - last_detection_time > 2:  # Cooldown
                    print("🔍 Running detection...")
                    try:
                        # Save temp frame
                        cv2.imwrite("temp_detection_frame.jpg", frame)
                        
                        # Run improved detection
                        results = detector.identify_person_in_image("temp_detection_frame.jpg", threshold=0.3)
                        
                        if results:
                            detection_results = results
                            print(f"✅ Found {len(results)} potential matches:")
                            for i, result in enumerate(results, 1):
                                name = result['offender_info'].get('name', result['offender_id'])
                                confidence = result['confidence']
                                method = result['method']
                                methods_used = ', '.join(result['methods_used'])
                                print(f"   {i}. {name}: {confidence:.3f} (via {method})")
                                print(f"      Methods: {methods_used}")
                        else:
                            detection_results = []
                            print("❌ No matches found")
                        
                        last_detection_time = current_time
                        
                    except Exception as e:
                        print(f"❌ Detection error: {e}")
                        cv2.putText(display_frame, f"Detection Error: {str(e)[:30]}", 
                                   (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                else:
                    print("⏳ Please wait before next detection...")
            elif key == ord('r'):
                # Record person image
                try:
                    # Create person_images directory if it doesn't exist
                    os.makedirs("person_images", exist_ok=True)
                    
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    filename = f"person_images/person_capture_{timestamp}.jpg"
                    cv2.imwrite(filename, frame)  # Save the original frame without overlays
                    print(f"👤 Person image recorded: {filename}")
                    
                    # Visual feedback - flash green border
                    feedback_frame = frame.copy()
                    cv2.rectangle(feedback_frame, (0, 0), 
                                (feedback_frame.shape[1]-1, feedback_frame.shape[0]-1), 
                                (0, 255, 0), 10)
                    cv2.imshow('Quick Camera Test - Improved Detection', feedback_frame)
                    cv2.waitKey(100)  # Show feedback for 100ms
                    
                except Exception as e:
                    print(f"❌ Failed to record person image: {e}")
    
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("✅ Camera released")

if __name__ == "__main__":
    print("🎥 Quick Camera Test for Offender Detection")
    print("=" * 50)
    
    # Test camera first
    if test_camera():
        print("\n🚀 Starting detection...")
        run_simple_detection()
    else:
        print("\n❌ Camera test failed. Please fix camera issues first.")
