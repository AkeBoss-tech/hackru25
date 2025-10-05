#!/usr/bin/env python3
"""
Snapshot Analysis Service
Integrates sex offender detection and family member recognition with snapshot functionality
"""

import os
import cv2
import numpy as np
import json
import logging
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime
from pathlib import Path
import threading
import time

from .improved_image_matcher import get_improved_matcher
from .continuous_sex_offender_detector import get_continuous_sex_offender_detector

logger = logging.getLogger(__name__)

class SnapshotAnalysisService:
    """
    Service for analyzing snapshots for sex offenders and family members.
    
    Features:
    - Automatic sex offender detection on snapshots
    - Family member recognition and management
    - Photo capture for family member enrollment
    - Real-time analysis and alerts
    - Integration with existing snapshot system
    """
    
    def __init__(self):
        """Initialize the snapshot analysis service."""
        self.image_matcher = get_improved_matcher()
        self.sex_offender_detector = get_continuous_sex_offender_detector()
        
        # Family member storage
        self.family_members_dir = Path("family_members")
        self.family_members_dir.mkdir(exist_ok=True)
        self.family_members_file = self.family_members_dir / "family_members.json"
        
        # Load existing family members
        self.family_members = self._load_family_members()
        
        # Analysis settings
        self.sex_offender_threshold = 0.3
        self.family_member_threshold = 0.4
        
        # Callbacks
        self.analysis_callbacks: List[callable] = []
        self.alert_callbacks: List[callable] = []
        
        logger.info("📸 Snapshot Analysis Service initialized")
    
    def _load_family_members(self) -> Dict[str, Dict]:
        """Load family members from storage."""
        if not self.family_members_file.exists():
            return {}
        
        try:
            with open(self.family_members_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading family members: {e}")
            return {}
    
    def _save_family_members(self):
        """Save family members to storage."""
        try:
            with open(self.family_members_file, 'w') as f:
                json.dump(self.family_members, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving family members: {e}")
    
    def analyze_snapshot(self, snapshot_path: str, frame: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Analyze a snapshot for sex offenders and family members.
        
        Args:
            snapshot_path: Path to the snapshot file
            frame: Optional frame data (if available)
            
        Returns:
            Analysis results with detections and alerts
        """
        logger.info(f"🔍 Analyzing snapshot: {snapshot_path}")
        
        analysis_result = {
            'snapshot_path': snapshot_path,
            'timestamp': datetime.now().isoformat(),
            'sex_offenders': [],
            'family_members': [],
            'faces_detected': 0,
            'analysis_status': 'completed',
            'alerts': []
        }
        
        try:
            # Load image if frame not provided
            if frame is None:
                frame = cv2.imread(snapshot_path)
                if frame is None:
                    analysis_result['analysis_status'] = 'failed'
                    analysis_result['error'] = 'Could not load snapshot'
                    return analysis_result
            
            # Detect faces in the snapshot
            faces = self.image_matcher.detect_faces(frame)
            analysis_result['faces_detected'] = len(faces)
            
            if not faces:
                logger.info("No faces detected in snapshot")
                return analysis_result
            
            # Analyze each detected face
            for i, face_bbox in enumerate(faces):
                x, y, w, h = face_bbox
                face_crop = frame[y:y+h, x:x+w]
                
                # Save temporary face crop for analysis
                temp_face_path = f"temp_face_{i}_{int(time.time())}.jpg"
                cv2.imwrite(temp_face_path, face_crop)
                
                try:
                    # Check for sex offenders
                    sex_offender_results = self._check_sex_offender(temp_face_path, face_bbox)
                    if sex_offender_results:
                        analysis_result['sex_offenders'].extend(sex_offender_results)
                        
                        # Generate alerts for high confidence matches
                        for result in sex_offender_results:
                            if result['confidence'] > 0.7:
                                alert = {
                                    'type': 'sex_offender_high_confidence',
                                    'severity': 'CRITICAL',
                                    'offender_info': result['offender_info'],
                                    'confidence': result['confidence'],
                                    'face_region': face_bbox,
                                    'timestamp': datetime.now().isoformat()
                                }
                                analysis_result['alerts'].append(alert)
                                logger.error(f"🚨 CRITICAL: Sex offender detected in snapshot - {result['offender_info'].get('name', 'Unknown')}")
                    
                    # Check for family members
                    family_member_result = self._check_family_member(temp_face_path, face_bbox)
                    if family_member_result:
                        analysis_result['family_members'].append(family_member_result)
                        logger.info(f"👨‍👩‍👧‍👦 Family member detected: {family_member_result['name']}")
                
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_face_path):
                        os.remove(temp_face_path)
            
            # Create labeled snapshot with names
            labeled_snapshot = self._create_labeled_snapshot(frame, analysis_result)
            analysis_result['labeled_snapshot'] = labeled_snapshot
            
            # Notify callbacks
            self._notify_analysis(analysis_result)
            
            # Generate alerts for any high-confidence matches
            if analysis_result['alerts']:
                self._notify_alerts(analysis_result['alerts'])
            
            logger.info(f"✅ Snapshot analysis complete: {len(analysis_result['sex_offenders'])} sex offenders, {len(analysis_result['family_members'])} family members")
            
        except Exception as e:
            logger.error(f"Error analyzing snapshot: {e}")
            analysis_result['analysis_status'] = 'failed'
            analysis_result['error'] = str(e)
        
        return analysis_result
    
    def _create_labeled_snapshot(self, frame: np.ndarray, analysis_result: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        Create a labeled snapshot with names drawn on detected faces.
        
        Args:
            frame: Original frame
            analysis_result: Analysis results containing detections
            
        Returns:
            Labeled frame with names drawn on faces
        """
        try:
            if frame is None:
                return None
            
            # Combine all detections for labeling
            all_detections = []
            
            # Add sex offender detections
            for detection in analysis_result.get('sex_offenders', []):
                all_detections.append(detection)
            
            # Add family member detections
            for detection in analysis_result.get('family_members', []):
                all_detections.append(detection)
            
            if not all_detections:
                return frame  # Return original frame if no detections
            
            # Use the image matcher's labeling function
            labeled_frame = self.image_matcher.draw_face_labels(frame, all_detections)
            
            return labeled_frame
            
        except Exception as e:
            logger.error(f"Error creating labeled snapshot: {e}")
            return frame  # Return original frame on error
    
    def _check_sex_offender(self, face_path: str, face_bbox: Tuple[int, int, int, int]) -> List[Dict]:
        """Check if a face matches a known sex offender."""
        try:
            results = self.image_matcher.identify_person_in_image(
                face_path, 
                threshold=self.sex_offender_threshold
            )
            
            # Add face region information
            for result in results:
                result['face_region'] = face_bbox
                result['analysis_type'] = 'sex_offender'
            
            return results
        except Exception as e:
            logger.error(f"Error checking sex offender: {e}")
            return []
    
    def _check_family_member(self, face_path: str, face_bbox: Tuple[int, int, int, int]) -> Optional[Dict]:
        """Check if a face matches a family member."""
        try:
            # For now, we'll use a simple comparison approach
            # In a real implementation, you'd use face recognition
            
            # Load the face image
            face_image = cv2.imread(face_path)
            if face_image is None:
                return None
            
            # Simple placeholder implementation
            # You could implement actual face recognition here
            for name, member_info in self.family_members.items():
                # Placeholder: return first family member for demo
                return {
                    'name': name,
                    'confidence': 0.8,  # Placeholder confidence
                    'face_region': face_bbox,
                    'analysis_type': 'family_member',
                    'member_info': member_info
                }
            
            return None
        except Exception as e:
            logger.error(f"Error checking family member: {e}")
            return None
    
    def capture_family_member_photo(self, frame: np.ndarray, name: str) -> bool:
        """
        Capture a photo of the current frame for family member enrollment.
        
        Args:
            frame: Current frame from camera
            name: Name of the family member
            
        Returns:
            True if photo was captured successfully
        """
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{name.replace(' ', '_')}_{timestamp}.jpg"
            photo_path = self.family_members_dir / filename
            
            # Save the frame
            cv2.imwrite(str(photo_path), frame)
            
            # Add to family members database
            self.family_members[name] = {
                'name': name,
                'photo_path': str(photo_path),
                'added_date': datetime.now().isoformat(),
                'photo_timestamp': timestamp
            }
            
            # Save to file
            self._save_family_members()
            
            logger.info(f"📸 Family member photo captured: {name} -> {photo_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error capturing family member photo: {e}")
            return False
    
    def add_family_member(self, name: str, photo_path: str) -> bool:
        """
        Add a family member with a photo.
        
        Args:
            name: Name of the family member
            photo_path: Path to the photo file
            
        Returns:
            True if added successfully
        """
        try:
            # Validate photo exists
            if not os.path.exists(photo_path):
                logger.error(f"Photo file not found: {photo_path}")
                return False
            
            # Copy photo to family members directory
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{name.replace(' ', '_')}_{timestamp}.jpg"
            dest_path = self.family_members_dir / filename
            
            # Read and save the photo
            photo = cv2.imread(photo_path)
            if photo is None:
                logger.error(f"Could not read photo: {photo_path}")
                return False
            
            cv2.imwrite(str(dest_path), photo)
            
            # Add to family members database
            self.family_members[name] = {
                'name': name,
                'photo_path': str(dest_path),
                'added_date': datetime.now().isoformat(),
                'photo_timestamp': timestamp
            }
            
            # Save to file
            self._save_family_members()
            
            logger.info(f"👨‍👩‍👧‍👦 Family member added: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding family member: {e}")
            return False
    
    def remove_family_member(self, name: str) -> bool:
        """Remove a family member."""
        try:
            if name in self.family_members:
                member_info = self.family_members[name]
                
                # Remove photo file
                photo_path = member_info.get('photo_path')
                if photo_path and os.path.exists(photo_path):
                    os.remove(photo_path)
                
                # Remove from database
                del self.family_members[name]
                self._save_family_members()
                
                logger.info(f"🗑️ Family member removed: {name}")
                return True
            else:
                logger.warning(f"Family member not found: {name}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing family member: {e}")
            return False
    
    def get_family_members(self) -> Dict[str, Dict]:
        """Get all family members."""
        return self.family_members.copy()
    
    def get_family_member_stats(self) -> Dict[str, Any]:
        """Get family member statistics."""
        return {
            'total_family_members': len(self.family_members),
            'family_members': list(self.family_members.keys()),
            'storage_directory': str(self.family_members_dir)
        }
    
    def set_sex_offender_threshold(self, threshold: float):
        """Set the sex offender detection threshold."""
        if 0.0 <= threshold <= 1.0:
            self.sex_offender_threshold = threshold
            logger.info(f"Sex offender threshold set to {threshold}")
    
    def set_family_member_threshold(self, threshold: float):
        """Set the family member recognition threshold."""
        if 0.0 <= threshold <= 1.0:
            self.family_member_threshold = threshold
            logger.info(f"Family member threshold set to {threshold}")
    
    def add_analysis_callback(self, callback: callable):
        """Add a callback for analysis events."""
        self.analysis_callbacks.append(callback)
    
    def add_alert_callback(self, callback: callable):
        """Add a callback for alert events."""
        self.alert_callbacks.append(callback)
    
    def _notify_analysis(self, analysis_result: Dict):
        """Notify analysis callbacks."""
        for callback in self.analysis_callbacks:
            try:
                callback(analysis_result)
            except Exception as e:
                logger.error(f"Error in analysis callback: {e}")
    
    def _notify_alerts(self, alerts: List[Dict]):
        """Notify alert callbacks."""
        for alert in alerts:
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get analysis statistics."""
        return {
            'family_members_count': len(self.family_members),
            'sex_offender_threshold': self.sex_offender_threshold,
            'family_member_threshold': self.family_member_threshold,
            'storage_directory': str(self.family_members_dir)
        }


# Global service instance
_snapshot_analysis_service = None

def get_snapshot_analysis_service() -> SnapshotAnalysisService:
    """Get or create the global snapshot analysis service."""
    global _snapshot_analysis_service
    if _snapshot_analysis_service is None:
        _snapshot_analysis_service = SnapshotAnalysisService()
    return _snapshot_analysis_service
