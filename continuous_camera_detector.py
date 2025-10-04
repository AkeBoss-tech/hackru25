#!/usr/bin/env python3
"""
Continuous camera detection for offender identification
Automatically runs detection on every frame without manual trigger
"""

import cv2
import numpy as np
import time
from improved_image_matcher import ImprovedImageMatcher

def test_camera():
    """Test camera and basic detection"""
    print("🎥 Testing camera access...")
    
    # Try to open camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot access camera. Please check:")
        print("  - Camera is connected")
        print("  - Camera permissions are granted")
        print("  - No other app is using the camera")
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

def run_continuous_detection():
    """Run continuous live detection with automatic processing"""
    print("🔍 Starting continuous live detection...")
    print("📝 Controls:")
    print("  - Press 'q' to quit")
    print("  - Press 's' to take screenshot")
    print("  - Press SPACE to pause/resume")
    print("  - Detection runs automatically every 2 seconds")
    
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
    detection_interval = 2.0  # Run detection every 2 seconds
    processing_detection = False
    
    try:
        print("🚀 Continuous detection started!")
        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                current_time = time.time()
                
                # Automatic detection every interval
                if (current_time - last_detection_time > detection_interval and 
                    not processing_detection):
                    processing_detection = True
                    print(f"🔍 Auto-detection #{frame_count//60}...")
                    
                    try:
                        # Save temp frame
                        cv2.imwrite("temp_frame.jpg", frame)
                        
                        # Run improved detection
                        results = detector.identify_person_in_image("temp_frame.jpg", threshold=0.3)
                        
                        if results:
                            detection_results = results
                            print(f"✅ Found {len(results)} potential matches:")
                            for i, result in enumerate(results, 1):
                                name = result['offender_info'].get('name', result['offender_id'])
                                confidence = result['confidence']
                                method = result['method']
                                methods_used = ', '.join(result['methods_used'])
                                
                                # Alert level based on confidence
                                if confidence > 0.7:
                                    alert = "🚨 HIGH ALERT"
                                elif confidence > 0.4:
                                    alert = "⚠️ MEDIUM"
                                else:
                                    alert = "💡 LOW"
                                
                                print(f"   {alert}: {name} - {confidence:.3f} (via {method})")
                                print(f"      Methods: {methods_used}")
                        else:
                            detection_results = []
                            print("❌ No matches detected")
                        
                        last_detection_time = current_time
                        
                    except Exception as e:
                        print(f"❌ Detection error: {e}")
                        detection_results = []
                    
                    processing_detection = False
                
                # Create display frame
                display_frame = frame.copy()
                
                # Add frame counter and status
                cv2.putText(display_frame, f"Frame: {frame_count}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Add detection status
                time_since_detection = current_time - last_detection_time
                next_detection_in = max(0, detection_interval - time_since_detection)
                
                if processing_detection:
                    status_text = "🔍 DETECTING..."
                    status_color = (0, 255, 255)  # Yellow
                elif next_detection_in < 0.5:
                    status_text = "🔄 READY"
                    status_color = (0, 255, 0)  # Green
                else:
                    status_text = f"⏱️ NEXT: {next_detection_in:.1f}s"
                    status_color = (255, 255, 255)  # White
                
                cv2.putText(display_frame, status_text, 
                           (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                
                # Add detection results overlay
                if detection_results:
                    y_offset = 110
                    for i, result in enumerate(detection_results[:3]):  # Show top 3
                        name = result['offender_info'].get('name', result['offender_id'])
                        confidence = result['confidence']
                        method = result['method']
                        
                        # Color and alert based on confidence
                        if confidence > 0.7:
                            color = (0, 0, 255)  # Red for high confidence
                            alert_text = f"🚨 HIGH: {name} ({confidence:.2f})"
                            # Add warning box
                            cv2.rectangle(display_frame, (5, y_offset + i*35 - 25), 
                                        (display_frame.shape[1] - 5, y_offset + i*35 + 10), 
                                        (0, 0, 255), 2)
                        elif confidence > 0.4:
                            color = (0, 255, 255)  # Yellow for medium
                            alert_text = f"⚠️ MED: {name} ({confidence:.2f})"
                        else:
                            color = (255, 255, 0)  # Cyan for low
                            alert_text = f"💡 LOW: {name} ({confidence:.2f})"
                        
                        cv2.putText(display_frame, alert_text, 
                                   (10, y_offset + i*35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                        
                        # Draw face region if available
                        if 'face_region' in result and result['face_region']:
                            x, y, w, h = result['face_region']
                            cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 3)
                            
                            # Add name label above face
                            cv2.putText(display_frame, name[:15], 
                                       (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # Add continuous detection indicator
                if detection_results:
                    # Flashing red border for alerts
                    if any(r['confidence'] > 0.7 for r in detection_results):
                        if int(current_time * 2) % 2:  # Flash every 0.5 seconds
                            cv2.rectangle(display_frame, (0, 0), 
                                        (display_frame.shape[1]-1, display_frame.shape[0]-1), 
                                        (0, 0, 255), 8)
                
                # Add instructions at bottom
                cv2.putText(display_frame, "CONTINUOUS DETECTION ACTIVE", 
                           (10, display_frame.shape[0] - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(display_frame, "Press 'q' to quit, 's' for screenshot, SPACE to pause", 
                           (10, display_frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                cv2.imshow('Continuous Camera Detection - Auto Offender Detection', display_frame)
            
            # Handle keys
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"continuous_capture_{timestamp}.jpg"
                cv2.imwrite(filename, display_frame)
                print(f"📸 Screenshot saved: {filename}")
                
                # Also save detection log if there are results
                if detection_results:
                    log_filename = f"detection_log_{timestamp}.txt"
                    with open(log_filename, 'w') as f:
                        f.write(f"Detection Results - {timestamp}\n")
                        f.write("=" * 40 + "\n")
                        for i, result in enumerate(detection_results, 1):
                            name = result['offender_info'].get('name', result['offender_id'])
                            confidence = result['confidence']
                            method = result['method']
                            methods_used = ', '.join(result['methods_used'])
                            f.write(f"{i}. {name}\n")
                            f.write(f"   Confidence: {confidence:.3f}\n")
                            f.write(f"   Method: {method}\n")
                            f.write(f"   All methods: {methods_used}\n\n")
                    print(f"📝 Detection log saved: {log_filename}")
                    
            elif key == ord(' '):
                paused = not paused
                if paused:
                    print("⏸️ Detection paused")
                else:
                    print("▶️ Detection resumed")
                    last_detection_time = 0  # Reset detection timer
    
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("✅ Camera released")
        print("📊 Detection session complete")

def run_high_frequency_detection():
    """Run high-frequency detection mode (every frame) - USE WITH CAUTION"""
    print("⚡ Starting HIGH FREQUENCY detection mode...")
    print("⚠️ WARNING: This will run detection on EVERY frame!")
    print("⚠️ This is very CPU intensive and may be slow!")
    print("📝 Controls:")
    print("  - Press 'q' to quit")
    print("  - Press 's' to take screenshot")
    print("  - Press SPACE to pause/resume")
    
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
    detection_results = []
    
    try:
        print("🚀 High frequency detection started!")
        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # Run detection on every frame
                if frame_count % 10 == 0:  # Actually every 10th frame to prevent overload
                    print(f"🔍 Detection frame {frame_count}...")
                    
                    try:
                        # Save temp frame
                        cv2.imwrite("temp_frame.jpg", frame)
                        
                        # Run improved detection
                        results = detector.identify_person_in_image("temp_frame.jpg", threshold=0.4)
                        
                        if results:
                            detection_results = results
                            # Only print high confidence results to avoid spam
                            high_conf_results = [r for r in results if r['confidence'] > 0.6]
                            if high_conf_results:
                                print(f"🚨 HIGH CONFIDENCE MATCHES:")
                                for result in high_conf_results:
                                    name = result['offender_info'].get('name', result['offender_id'])
                                    confidence = result['confidence']
                                    print(f"   🚨 {name}: {confidence:.3f}")
                        else:
                            detection_results = []
                        
                    except Exception as e:
                        print(f"❌ Detection error: {e}")
                        detection_results = []
                
                # Create display frame (same as before but with different title)
                display_frame = frame.copy()
                
                # Add frame counter
                cv2.putText(display_frame, f"Frame: {frame_count}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Add high frequency mode indicator
                cv2.putText(display_frame, "⚡ HIGH FREQ MODE", 
                           (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                
                # Add detection results (same as before)
                if detection_results:
                    y_offset = 110
                    for i, result in enumerate(detection_results[:3]):
                        name = result['offender_info'].get('name', result['offender_id'])
                        confidence = result['confidence']
                        
                        if confidence > 0.7:
                            color = (0, 0, 255)
                            alert_text = f"🚨 {name} ({confidence:.2f})"
                        elif confidence > 0.4:
                            color = (0, 255, 255)
                            alert_text = f"⚠️ {name} ({confidence:.2f})"
                        else:
                            color = (255, 255, 0)
                            alert_text = f"💡 {name} ({confidence:.2f})"
                        
                        cv2.putText(display_frame, alert_text, 
                                   (10, y_offset + i*35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                        
                        if 'face_region' in result and result['face_region']:
                            x, y, w, h = result['face_region']
                            cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 3)
                
                cv2.imshow('High Frequency Continuous Detection', display_frame)
            
            # Handle keys (same as before)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"highfreq_capture_{timestamp}.jpg"
                cv2.imwrite(filename, display_frame)
                print(f"📸 Screenshot saved: {filename}")
            elif key == ord(' '):
                paused = not paused
                print("⏸️ Paused" if paused else "▶️ Resumed")
    
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("✅ High frequency detection complete")

if __name__ == "__main__":
    print("🎥 Continuous Camera Detection for Offender Identification")
    print("=" * 60)
    
    # Test camera first
    if test_camera():
        print("\n🚀 Choose detection mode:")
        print("1. Normal continuous detection (every 2 seconds)")
        print("2. High frequency detection (every 10th frame - CPU intensive)")
        
        while True:
            choice = input("\nEnter choice (1 or 2): ").strip()
            if choice == "1":
                print("\n🔄 Starting normal continuous detection...")
                run_continuous_detection()
                break
            elif choice == "2":
                print("\n⚡ Starting high frequency detection...")
                run_high_frequency_detection()
                break
            else:
                print("❌ Invalid choice. Please enter 1 or 2.")
    else:
        print("\n❌ Camera test failed. Please fix camera issues first.")
