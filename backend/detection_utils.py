"""
Utility functions for object detection, visualization, and data processing.
Provides helper functions for working with YOLOv8 results and visualizations.
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
import logging
from pathlib import Path
import json
import time
from collections import defaultdict


class DetectionUtils:
    """
    Utility class for object detection operations.
    
    Features:
    - Detection extraction and formatting
    - Visualization utilities
    - Detection filtering and analysis
    - Export/import functionality
    - Performance metrics
    """
    
    def __init__(self):
        """Initialize DetectionUtils."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Detection statistics
        self.detection_stats = defaultdict(int)
        self.frame_detections = []
        
        self.logger.info("DetectionUtils initialized")
    
    def extract_detections(self, result, class_names: Dict[int, str]) -> List[Dict]:
        """
        Extract detections from YOLOv8 result.
        
        Args:
            result: YOLOv8 result object
            class_names: Dictionary mapping class IDs to names
            
        Returns:
            List of detection dictionaries
        """
        detections = []
        
        if result.boxes is None or len(result.boxes) == 0:
            return detections
        
        boxes = result.boxes
        
        for i in range(len(boxes)):
            # Extract bounding box coordinates
            box = boxes.xyxy[i].cpu().numpy()  # [x1, y1, x2, y2]
            x1, y1, x2, y2 = box
            
            # Extract confidence and class
            confidence = float(boxes.conf[i].cpu().numpy())
            class_id = int(boxes.cls[i].cpu().numpy())
            class_name = class_names.get(class_id, f"class_{class_id}")
            
            # Calculate box dimensions
            width = x2 - x1
            height = y2 - y1
            area = width * height
            
            # Create detection dictionary
            detection = {
                'bbox': [x1, y1, x2, y2],
                'confidence': confidence,
                'class_id': class_id,
                'class_name': class_name,
                'width': width,
                'height': height,
                'area': area,
                'center': [(x1 + x2) / 2, (y1 + y2) / 2],
                'timestamp': time.time()
            }
            
            detections.append(detection)
        
        # Update statistics
        self._update_detection_stats(detections)
        
        return detections
    
    def _update_detection_stats(self, detections: List[Dict]):
        """Update detection statistics."""
        for detection in detections:
            class_name = detection['class_name']
            self.detection_stats[class_name] += 1
    
    def filter_detections(
        self,
        detections: List[Dict],
        min_confidence: float = 0.0,
        min_area: float = 0.0,
        target_classes: Optional[List[str]] = None,
        max_detections: Optional[int] = None
    ) -> List[Dict]:
        """
        Filter detections based on various criteria.
        
        Args:
            detections: List of detection dictionaries
            min_confidence: Minimum confidence threshold
            min_area: Minimum bounding box area
            target_classes: List of target class names (None for all)
            max_detections: Maximum number of detections to return
            
        Returns:
            Filtered list of detections
        """
        filtered = []
        
        for detection in detections:
            # Confidence filter
            if detection['confidence'] < min_confidence:
                continue
            
            # Area filter
            if detection['area'] < min_area:
                continue
            
            # Class filter
            if target_classes and detection['class_name'] not in target_classes:
                continue
            
            filtered.append(detection)
        
        # Sort by confidence (highest first)
        filtered.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Limit number of detections
        if max_detections and len(filtered) > max_detections:
            filtered = filtered[:max_detections]
        
        return filtered
    
    def draw_detections(
        self,
        frame: np.ndarray,
        detections: List[Dict],
        show_confidence: bool = True,
        show_class: bool = True,
        show_bbox: bool = True,
        color_map: Optional[Dict[str, Tuple[int, int, int]]] = None
    ) -> np.ndarray:
        """
        Draw detections on a frame.
        
        Args:
            frame: Input frame
            detections: List of detection dictionaries
            show_confidence: Whether to show confidence scores
            show_class: Whether to show class names
            show_bbox: Whether to show bounding boxes
            color_map: Custom color mapping for classes
            
        Returns:
            Frame with drawn detections
        """
        if not detections:
            return frame
        
        # Default colors (BGR format)
        default_colors = [
            (0, 255, 0),    # Green
            (255, 0, 0),    # Blue
            (0, 0, 255),    # Red
            (255, 255, 0),  # Cyan
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Yellow
            (128, 0, 128),  # Purple
            (255, 165, 0),  # Orange
        ]
        
        for i, detection in enumerate(detections):
            bbox = detection['bbox']
            x1, y1, x2, y2 = [int(coord) for coord in bbox]
            class_name = detection['class_name']
            confidence = detection['confidence']
            
            # Get color for this class
            if color_map and class_name in color_map:
                color = color_map[class_name]
            else:
                color = default_colors[i % len(default_colors)]
            
            # Draw bounding box
            if show_bbox:
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Prepare label text
            label_parts = []
            if show_class:
                label_parts.append(class_name)
            if show_confidence:
                label_parts.append(f"{confidence:.2f}")
            
            if label_parts:
                label = " ".join(label_parts)
                
                # Get text size for background
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.6
                thickness = 2
                (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
                
                # Draw background rectangle
                cv2.rectangle(
                    frame,
                    (x1, y1 - text_height - baseline - 5),
                    (x1 + text_width, y1),
                    color,
                    -1
                )
                
                # Draw text
                cv2.putText(
                    frame,
                    label,
                    (x1, y1 - baseline - 5),
                    font,
                    font_scale,
                    (255, 255, 255),
                    thickness
                )
        
        return frame
    
    def draw_detection_summary(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """
        Draw a summary of detections on the frame.
        
        Args:
            frame: Input frame
            detections: List of detection dictionaries
            
        Returns:
            Frame with detection summary
        """
        if not detections:
            return frame
        
        # Count detections by class
        class_counts = defaultdict(int)
        for detection in detections:
            class_counts[detection['class_name']] += 1
        
        # Draw summary
        y_offset = 30
        summary_text = f"Detections: {len(detections)}"
        cv2.putText(
            frame,
            summary_text,
            (frame.shape[1] - 200, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )
        
        y_offset += 30
        for class_name, count in class_counts.items():
            text = f"{class_name}: {count}"
            cv2.putText(
                frame,
                text,
                (frame.shape[1] - 200, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                2
            )
            y_offset += 25
        
        return frame
    
    def calculate_detection_metrics(self, detections: List[Dict]) -> Dict:
        """
        Calculate various metrics for detections.
        
        Args:
            detections: List of detection dictionaries
            
        Returns:
            Dictionary with calculated metrics
        """
        if not detections:
            return {
                'total_detections': 0,
                'avg_confidence': 0,
                'class_distribution': {},
                'size_distribution': {},
                'spatial_distribution': {}
            }
        
        # Basic metrics
        total_detections = len(detections)
        confidences = [d['confidence'] for d in detections]
        avg_confidence = sum(confidences) / len(confidences)
        
        # Class distribution
        class_distribution = defaultdict(int)
        for detection in detections:
            class_distribution[detection['class_name']] += 1
        
        # Size distribution
        areas = [d['area'] for d in detections]
        size_distribution = {
            'min_area': min(areas),
            'max_area': max(areas),
            'avg_area': sum(areas) / len(areas),
            'total_area': sum(areas)
        }
        
        # Spatial distribution
        centers = [d['center'] for d in detections]
        if centers:
            center_x = [c[0] for c in centers]
            center_y = [c[1] for c in centers]
            spatial_distribution = {
                'center_x_range': [min(center_x), max(center_x)],
                'center_y_range': [min(center_y), max(center_y)],
                'avg_center': [sum(center_x) / len(center_x), sum(center_y) / len(center_y)]
            }
        else:
            spatial_distribution = {}
        
        return {
            'total_detections': total_detections,
            'avg_confidence': avg_confidence,
            'class_distribution': dict(class_distribution),
            'size_distribution': size_distribution,
            'spatial_distribution': spatial_distribution
        }
    
    def export_detections(
        self,
        detections: List[Dict],
        filepath: Union[str, Path],
        format: str = "json"
    ) -> bool:
        """
        Export detections to a file.
        
        Args:
            detections: List of detection dictionaries
            filepath: Path to save file
            format: Export format ('json', 'csv', 'txt')
            
        Returns:
            True if export was successful
        """
        try:
            filepath = Path(filepath)
            
            if format.lower() == "json":
                with open(filepath, 'w') as f:
                    json.dump(detections, f, indent=2)
            
            elif format.lower() == "csv":
                import pandas as pd
                df = pd.DataFrame(detections)
                df.to_csv(filepath, index=False)
            
            elif format.lower() == "txt":
                with open(filepath, 'w') as f:
                    for detection in detections:
                        f.write(f"{detection['class_name']} {detection['confidence']:.3f} "
                               f"{detection['bbox'][0]} {detection['bbox'][1]} "
                               f"{detection['bbox'][2]} {detection['bbox'][3]}\n")
            
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            self.logger.info(f"Detections exported to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export detections: {e}")
            return False
    
    def load_detections(self, filepath: Union[str, Path]) -> List[Dict]:
        """
        Load detections from a file.
        
        Args:
            filepath: Path to file
            
        Returns:
            List of detection dictionaries
        """
        try:
            filepath = Path(filepath)
            
            if filepath.suffix.lower() == '.json':
                with open(filepath, 'r') as f:
                    detections = json.load(f)
            
            elif filepath.suffix.lower() == '.csv':
                import pandas as pd
                df = pd.read_csv(filepath)
                detections = df.to_dict('records')
            
            else:
                raise ValueError(f"Unsupported file format: {filepath.suffix}")
            
            self.logger.info(f"Detections loaded from {filepath}")
            return detections
            
        except Exception as e:
            self.logger.error(f"Failed to load detections: {e}")
            return []
    
    def get_detection_statistics(self) -> Dict:
        """Get overall detection statistics."""
        total_detections = sum(self.detection_stats.values())
        
        return {
            'total_detections': total_detections,
            'class_counts': dict(self.detection_stats),
            'unique_classes': len(self.detection_stats),
            'most_detected_class': max(self.detection_stats.items(), key=lambda x: x[1])[0] if self.detection_stats else None
        }
    
    def reset_statistics(self):
        """Reset detection statistics."""
        self.detection_stats.clear()
        self.frame_detections.clear()
        self.logger.info("Detection statistics reset")
    
    def create_detection_heatmap(
        self,
        detections: List[Dict],
        frame_shape: Tuple[int, int],
        grid_size: int = 50
    ) -> np.ndarray:
        """
        Create a heatmap showing detection density.
        
        Args:
            detections: List of detection dictionaries
            frame_shape: Shape of the frame (height, width)
            grid_size: Size of grid cells for heatmap
            
        Returns:
            Heatmap as numpy array
        """
        height, width = frame_shape
        heatmap = np.zeros((height // grid_size, width // grid_size), dtype=np.float32)
        
        for detection in detections:
            center = detection['center']
            x, y = int(center[0] // grid_size), int(center[1] // grid_size)
            
            if 0 <= x < heatmap.shape[1] and 0 <= y < heatmap.shape[0]:
                heatmap[y, x] += 1
        
        # Normalize heatmap
        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()
        
        return heatmap
    
    def visualize_heatmap(self, heatmap: np.ndarray, colormap: int = cv2.COLORMAP_JET) -> np.ndarray:
        """
        Visualize a heatmap with color mapping.
        
        Args:
            heatmap: Input heatmap
            colormap: OpenCV colormap to use
            
        Returns:
            Colorized heatmap
        """
        # Convert to 8-bit
        heatmap_8bit = (heatmap * 255).astype(np.uint8)
        
        # Apply colormap
        colored_heatmap = cv2.applyColorMap(heatmap_8bit, colormap)
        
        return colored_heatmap
    
    def detect_objects_in_roi(
        self,
        detections: List[Dict],
        roi: Tuple[int, int, int, int]
    ) -> List[Dict]:
        """
        Filter detections that are within a region of interest.
        
        Args:
            detections: List of detection dictionaries
            roi: Region of interest as (x1, y1, x2, y2)
            
        Returns:
            Detections within the ROI
        """
        roi_x1, roi_y1, roi_x2, roi_y2 = roi
        roi_detections = []
        
        for detection in detections:
            bbox = detection['bbox']
            det_x1, det_y1, det_x2, det_y2 = bbox
            
            # Check if detection overlaps with ROI
            if (det_x1 < roi_x2 and det_x2 > roi_x1 and
                det_y1 < roi_y2 and det_y2 > roi_y1):
                roi_detections.append(detection)
        
        return roi_detections
    
    def calculate_detection_overlap(self, det1: Dict, det2: Dict) -> float:
        """
        Calculate overlap between two detections.
        
        Args:
            det1: First detection
            det2: Second detection
            
        Returns:
            Overlap ratio (0-1)
        """
        bbox1 = det1['bbox']
        bbox2 = det2['bbox']
        
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
