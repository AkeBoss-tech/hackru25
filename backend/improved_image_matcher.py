#!/usr/bin/env python3
"""
Improved Image Matcher for Offender Detection
Integrates multiple face detection and matching methods for robust identification
"""

import os
import sys
import cv2
import numpy as np
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime
import pickle

# Add scripts directory to path for importing face database modules
scripts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts')
sys.path.insert(0, scripts_dir)

try:
    from opencv_face_db import OpenCVFaceDatabase
    from face_vector_db import FaceVectorDatabase
except ImportError as e:
    print(f"Warning: Could not import face database modules: {e}")
    print("Face detection will be limited")

logger = logging.getLogger(__name__)

class ImprovedImageMatcher:
    """
    Advanced image matcher that combines multiple detection methods:
    1. OpenCV-based face detection and matching
    2. Vector-based face embeddings (if available)
    3. Confidence scoring and result ranking
    """
    
    def __init__(self, 
                 opencv_db_path: str = "opencv_face_db.db",
                 face_db_path: str = "face_vector_db.db",
                 images_dir: str = "sex-offenders/images"):
        """
        Initialize the improved image matcher.
        
        Args:
            opencv_db_path: Path to OpenCV face database
            face_db_path: Path to vector face database
            images_dir: Directory containing offender images
        """
        self.opencv_db_path = opencv_db_path
        self.face_db_path = face_db_path
        self.images_dir = Path(images_dir)
        
        # Initialize face detection
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # Initialize databases
        self.opencv_db = None
        self.face_db = None
        
        try:
            self.opencv_db = OpenCVFaceDatabase(opencv_db_path, str(self.images_dir))
            logger.info("✅ OpenCV face database initialized")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize OpenCV database: {e}")
        
        try:
            self.face_db = FaceVectorDatabase(face_db_path, str(self.images_dir))
            logger.info("✅ Vector face database initialized")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize vector database: {e}")
        
        # Load offender metadata
        self.offender_data = self._load_offender_metadata()
        
        logger.info("🔍 Improved Image Matcher initialized")
    
    def _load_offender_metadata(self) -> Dict[str, Dict]:
        """Load offender metadata from JSON files."""
        offender_data = {}
        
        data_files = [
            "sex-offenders/data/offenders_with_images.json",
            "sex-offenders/data/offenders.json"
        ]
        
        for data_file in data_files:
            if Path(data_file).exists():
                try:
                    with open(data_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    for offender in data:
                        offender_id = offender.get('offender_id')
                        if offender_id:
                            offender_data[offender_id] = offender
                    
                    logger.info(f"Loaded {len(offender_data)} offenders from {data_file}")
                    break
                except Exception as e:
                    logger.error(f"Error loading {data_file}: {e}")
        
        return offender_data
    
    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in an image using OpenCV.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            List of face bounding boxes (x, y, w, h)
        """
        if image is None:
            return []
        
        # Convert to grayscale for face detection
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        return [(x, y, w, h) for (x, y, w, h) in faces]
    
    def extract_face_features(self, image: np.ndarray, face_bbox: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """
        Extract features from a detected face region.
        
        Args:
            image: Input image
            face_bbox: Face bounding box (x, y, w, h)
            
        Returns:
            Face features or None if extraction fails
        """
        x, y, w, h = face_bbox
        
        # Extract face region
        face_region = image[y:y+h, x:x+w]
        
        if face_region.size == 0:
            return None
        
        # Resize to standard size
        face_resized = cv2.resize(face_region, (100, 100))
        
        # Convert to grayscale and flatten
        if len(face_resized.shape) == 3:
            face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        else:
            face_gray = face_resized
        
        # Normalize features
        features = face_gray.flatten().astype(np.float32) / 255.0
        
        return features
    
    def calculate_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """
        Calculate similarity between two feature vectors.
        
        Args:
            features1: First feature vector
            features2: Second feature vector
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        if features1 is None or features2 is None:
            return 0.0
        
        # Ensure same size
        if len(features1) != len(features2):
            return 0.0
        
        # Calculate cosine similarity
        dot_product = np.dot(features1, features2)
        norm1 = np.linalg.norm(features1)
        norm2 = np.linalg.norm(features2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return max(0.0, similarity)  # Ensure non-negative
    
    def search_opencv_database(self, image_path: str, threshold: float = 0.3) -> List[Dict]:
        """
        Search using OpenCV database.
        
        Args:
            image_path: Path to query image
            threshold: Minimum similarity threshold
            
        Returns:
            List of matching results
        """
        if not self.opencv_db:
            return []
        
        try:
            results = self.opencv_db.search_by_face(
                image_path, 
                top_k=10, 
                min_similarity=threshold
            )
            
            # Add method information
            for result in results:
                result['method'] = 'opencv'
                result['methods_used'] = ['opencv']
            
            return results
        except Exception as e:
            logger.error(f"OpenCV database search error: {e}")
            return []
    
    def search_vector_database(self, image_path: str, threshold: float = 0.3) -> List[Dict]:
        """
        Search using vector database.
        
        Args:
            image_path: Path to query image
            threshold: Minimum similarity threshold
            
        Returns:
            List of matching results
        """
        if not self.face_db:
            return []
        
        try:
            results = self.face_db.search_by_face(
                image_path,
                top_k=10,
                tolerance=1.0 - threshold  # Convert threshold to distance tolerance
            )
            
            # Add method information
            for result in results:
                result['method'] = 'vector'
                result['methods_used'] = ['vector']
            
            return results
        except Exception as e:
            logger.error(f"Vector database search error: {e}")
            return []
    
    def combine_results(self, opencv_results: List[Dict], vector_results: List[Dict]) -> List[Dict]:
        """
        Combine and rank results from multiple methods.
        
        Args:
            opencv_results: Results from OpenCV database
            vector_results: Results from vector database
            
        Returns:
            Combined and ranked results
        """
        # Create a combined result dictionary
        combined_results = {}
        
        # Add OpenCV results
        for result in opencv_results:
            offender_id = result['offender_id']
            if offender_id not in combined_results:
                combined_results[offender_id] = result.copy()
                combined_results[offender_id]['methods_used'] = ['opencv']
            else:
                # Average the confidence scores
                combined_results[offender_id]['confidence'] = (
                    combined_results[offender_id]['confidence'] + result['confidence']
                ) / 2
                combined_results[offender_id]['methods_used'].append('opencv')
        
        # Add vector results
        for result in vector_results:
            offender_id = result['offender_id']
            if offender_id not in combined_results:
                combined_results[offender_id] = result.copy()
                combined_results[offender_id]['methods_used'] = ['vector']
            else:
                # Average the confidence scores
                combined_results[offender_id]['confidence'] = (
                    combined_results[offender_id]['confidence'] + result['confidence']
                ) / 2
                combined_results[offender_id]['methods_used'].append('vector')
        
        # Convert back to list and sort by confidence
        final_results = list(combined_results.values())
        final_results.sort(key=lambda x: x['confidence'], reverse=True)
        
        return final_results
    
    def identify_person_in_image(self, image_path: str, threshold: float = 0.3) -> List[Dict]:
        """
        Identify persons in an image using multiple detection methods.
        
        Args:
            image_path: Path to the image to analyze
            threshold: Minimum confidence threshold for matches
            
        Returns:
            List of identification results with confidence scores
        """
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return []
        
        logger.info(f"🔍 Analyzing image: {image_path}")
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Could not load image: {image_path}")
            return []
        
        # Detect faces in the image
        faces = self.detect_faces(image)
        logger.info(f"Detected {len(faces)} faces in image")
        
        if not faces:
            logger.info("No faces detected in image")
            return []
        
        # Search using both databases
        opencv_results = self.search_opencv_database(image_path, threshold)
        vector_results = self.search_vector_database(image_path, threshold)
        
        # Combine results
        combined_results = self.combine_results(opencv_results, vector_results)
        
        # Filter by threshold and add face region information
        final_results = []
        for result in combined_results:
            if result['confidence'] >= threshold:
                # Add face region info (use first detected face for now)
                if faces:
                    result['face_region'] = faces[0]
                
                # Add offender metadata
                offender_id = result['offender_id']
                if offender_id in self.offender_data:
                    result['offender_info'] = self.offender_data[offender_id]
                else:
                    result['offender_info'] = {'name': result.get('name', offender_id)}
                
                final_results.append(result)
        
        logger.info(f"✅ Found {len(final_results)} matches above threshold {threshold}")
        
        return final_results
    
    def get_database_stats(self) -> Dict:
        """Get statistics from both databases."""
        stats = {
            'opencv_database': {},
            'vector_database': {},
            'offender_metadata': len(self.offender_data)
        }
        
        if self.opencv_db:
            try:
                stats['opencv_database'] = self.opencv_db.get_database_stats()
            except Exception as e:
                stats['opencv_database'] = {'error': str(e)}
        
        if self.face_db:
            try:
                stats['vector_database'] = self.face_db.get_database_stats()
            except Exception as e:
                stats['vector_database'] = {'error': str(e)}
        
        return stats
    
    def test_detection(self, image_path: str) -> Dict:
        """
        Test face detection on an image.
        
        Args:
            image_path: Path to test image
            
        Returns:
            Detection test results
        """
        if not os.path.exists(image_path):
            return {'error': 'Image file not found'}
        
        image = cv2.imread(image_path)
        if image is None:
            return {'error': 'Could not load image'}
        
        faces = self.detect_faces(image)
        
        return {
            'image_path': image_path,
            'faces_detected': len(faces),
            'face_regions': faces,
            'image_shape': image.shape,
            'databases_available': {
                'opencv': self.opencv_db is not None,
                'vector': self.face_db is not None
            }
        }


# Global instance for easy access
_improved_matcher = None

def get_improved_matcher() -> ImprovedImageMatcher:
    """Get or create the global improved image matcher instance."""
    global _improved_matcher
    if _improved_matcher is None:
        _improved_matcher = ImprovedImageMatcher()
    return _improved_matcher

def initialize_improved_matcher(**kwargs) -> ImprovedImageMatcher:
    """Initialize the global improved image matcher with custom parameters."""
    global _improved_matcher
    _improved_matcher = ImprovedImageMatcher(**kwargs)
    return _improved_matcher
