# YOLOv8n Object Detection

This project provides a simple setup for running YOLOv8n (nano) object detection model.

## Setup

### 1. Create and activate virtual environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Usage

### Basic usage (webcam detection)

```bash
python scripts/run_yolov8n.py
```

### Detect objects in an image

```bash
python scripts/run_yolov8n.py --source path/to/image.jpg --save
```

### Detect objects in a video

```bash
python scripts/run_yolov8n.py --source path/to/video.mp4 --save
```

### Custom confidence threshold

```bash
python scripts/run_yolov8n.py --source 0 --conf 0.5
```

## Arguments

- `--source`: Source for detection (image path, video path, or '0' for webcam)
- `--conf`: Confidence threshold (default: 0.25)
- `--save`: Save detection results
- `--show`: Show detection results in real-time (default: True)
- `--output-dir`: Directory to save results (default: runs/detect)

## What is YOLOv8n?

YOLOv8n is the nano (smallest) version of YOLOv8, designed for:
- Fast inference speed
- Low computational requirements
- Real-time object detection
- 80 COCO classes detection (person, car, dog, etc.)

Perfect for edge devices and applications requiring quick detection.

