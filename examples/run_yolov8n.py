#!/usr/bin/env python3
"""
YOLOv8n Object Detection Script
This script runs YOLOv8n (nano) model for object detection on images, videos, or webcam.
"""

import argparse
from pathlib import Path
import torch
import cv2

# Fix for PyTorch 2.6+ weights_only security feature with ultralytics
# Monkey patch torch.load to allow loading YOLOv8 models
original_torch_load = torch.load
def patched_torch_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return original_torch_load(*args, **kwargs)
torch.load = patched_torch_load

from ultralytics import YOLO


def run_webcam(model, conf=0.25):
    """Run detection on webcam feed"""
    print("Opening webcam... Press 'q' to quit")
    
    # Try different camera indices
    cap = None
    for camera_idx in [0, 1]:
        print(f"Trying camera index {camera_idx}...")
        test_cap = cv2.VideoCapture(camera_idx)
        if test_cap.isOpened():
            # Try reading a frame to verify it works
            ret, _ = test_cap.read()
            if ret:
                cap = test_cap
                print(f"✓ Camera {camera_idx} working!")
                break
            else:
                test_cap.release()
        else:
            test_cap.release()
    
    if cap is None:
        print("\n❌ Error: Could not access any camera")
        print("\nPlease check:")
        print("  1. Camera is not being used by another application")
        print("  2. Camera permissions are granted in System Preferences > Security & Privacy > Camera")
        print("  3. Camera is properly connected")
        print("  4. Try closing other apps that might be using the camera (Zoom, Teams, etc.)")
        return
    
    print("Webcam opened successfully!")
    print("Press 'q' to quit\n")
    
    # Give camera time to warm up
    import time
    time.sleep(1)
    
    frame_count = 0
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to read frame from webcam")
                break
            
            # Run inference
            results = model(frame, conf=conf, verbose=False)
            
            # Get annotated frame
            annotated_frame = results[0].plot()
            
            # Print detections every 30 frames
            if frame_count % 30 == 0:
                boxes = results[0].boxes
                if len(boxes) > 0:
                    print(f"Frame {frame_count}: Detected {len(boxes)} objects")
                    detected = {}
                    for box in boxes:
                        cls = int(box.cls[0])
                        class_name = model.names[cls]
                        detected[class_name] = detected.get(class_name, 0) + 1
                    for obj, count in detected.items():
                        print(f"  - {obj}: {count}")
            
            # Display
            cv2.imshow('YOLOv8n - Press Q to quit', annotated_frame)
            
            # Check for 'q' key to quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\nStopping detection...")
                break
            
            frame_count += 1
            
    except KeyboardInterrupt:
        print("\nDetection interrupted by user")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print(f"Processed {frame_count} frames")


def main():
    parser = argparse.ArgumentParser(description='Run YOLOv8n object detection')
    parser.add_argument(
        '--source',
        type=str,
        default='0',
        help='Source for detection: image path, video path, or 0 for webcam (default: 0)'
    )
    parser.add_argument(
        '--conf',
        type=float,
        default=0.25,
        help='Confidence threshold (default: 0.25)'
    )
    parser.add_argument(
        '--save',
        action='store_true',
        help='Save detection results'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='runs/detect',
        help='Directory to save results (default: runs/detect)'
    )
    
    args = parser.parse_args()
    
    # Load YOLOv8n model
    print("Loading YOLOv8n model...")
    model = YOLO('yolov8n.pt')  # This will automatically download if not present
    
    # Check if source is webcam
    if args.source == '0':
        run_webcam(model, conf=args.conf)
    else:
        # Run inference on image/video
        print(f"Running detection on: {args.source}")
        results = model.predict(
            source=args.source,
            conf=args.conf,
            save=args.save,
            show=True,
            project=args.output_dir
        )
        
        # Process results
        for result in results:
            boxes = result.boxes
            
            if len(boxes) > 0:
                print(f"\nDetected {len(boxes)} objects:")
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = model.names[cls]
                    print(f"  - {class_name}: {conf:.2f}")
            else:
                print("No objects detected")
        
        print(f"\nDetection complete!")
        if args.save:
            print(f"Results saved to: {args.output_dir}")


if __name__ == '__main__':
    main()

