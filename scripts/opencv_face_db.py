#!/usr/bin/env python3
"""
OpenCV-based Face Vector Database for Sex Offender Images
Uses OpenCV's built-in face detection and simple feature extraction
"""

import os
import json
import pickle
import numpy as np
import cv2
from pathlib import Path
import logging
from typing import List, Dict, Tuple, Optional
import sqlite3
from datetime import datetime
import hashlib

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OpenCVFaceDatabase:
    def __init__(self, db_path: str = "opencv_face_db.db", images_dir: str = "sex-offenders/images"):
        self.db_path = db_path
        self.images_dir = Path(images_dir)
        self.embeddings_dir = Path("opencv_embeddings")
        self.embeddings_dir.mkdir(exist_ok=True)
        
        # Initialize face cascade
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Initialize database
        self.init_database()
        
        # Load offender data
        self.offender_data = self.load_offender_data()
    
    def init_database(self):
        """Initialize SQLite database for storing face embeddings and metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offender_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                image_path TEXT NOT NULL,
                embedding_path TEXT NOT NULL,
                face_count INTEGER DEFAULT 0,
                face_locations TEXT,
                face_features TEXT,
                image_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_type TEXT NOT NULL,
                query_data TEXT,
                results_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def load_offender_data(self) -> Dict[str, Dict]:
        """Load offender data from JSON files"""
        offender_data = {}
        
        # Try to load from the most recent data file
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
    
    def detect_faces(self, image_path: str) -> Tuple[List[Tuple], np.ndarray]:
        """Detect faces in image using OpenCV"""
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not load image: {image_path}")
                return [], np.array([])
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            face_locations = []
            face_images = []
            
            for (x, y, w, h) in faces:
                face_locations.append((x, y, x+w, y+h))
                face_img = gray[y:y+h, x:x+w]
                face_images.append(face_img)
            
            logger.info(f"Detected {len(faces)} faces in {image_path}")
            return face_locations, face_images
            
        except Exception as e:
            logger.error(f"Error detecting faces in {image_path}: {e}")
            return [], np.array([])
    
    def extract_face_features(self, face_image: np.ndarray) -> np.ndarray:
        """Extract features from face image using simple methods"""
        try:
            # Resize face to standard size
            face_resized = cv2.resize(face_image, (64, 64))
            
            # Apply histogram equalization
            face_equalized = cv2.equalizeHist(face_resized)
            
            # Extract features using multiple methods
            features = []
            
            # 1. Histogram features
            hist = cv2.calcHist([face_equalized], [0], None, [32], [0, 256])
            features.extend(hist.flatten())
            
            # 2. LBP-like features (simplified)
            lbp_features = self.extract_lbp_features(face_equalized)
            features.extend(lbp_features)
            
            # 3. Gradient features
            grad_x = cv2.Sobel(face_equalized, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(face_equalized, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            features.extend(gradient_magnitude.flatten()[::4])  # Sample every 4th pixel
            
            # 4. Texture features using Gabor filters
            gabor_features = self.extract_gabor_features(face_equalized)
            features.extend(gabor_features)
            
            return np.array(features, dtype=np.float32)
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return np.array([])
    
    def extract_lbp_features(self, image: np.ndarray) -> List[float]:
        """Extract simplified LBP features"""
        try:
            # Simple LBP implementation
            lbp = np.zeros_like(image)
            
            for i in range(1, image.shape[0] - 1):
                for j in range(1, image.shape[1] - 1):
                    center = image[i, j]
                    binary_string = ""
                    
                    # 8-neighborhood
                    neighbors = [
                        image[i-1, j-1], image[i-1, j], image[i-1, j+1],
                        image[i, j+1], image[i+1, j+1], image[i+1, j],
                        image[i+1, j-1], image[i, j-1]
                    ]
                    
                    for neighbor in neighbors:
                        binary_string += "1" if neighbor >= center else "0"
                    
                    lbp[i, j] = int(binary_string, 2)
            
            # Calculate histogram
            hist, _ = np.histogram(lbp.flatten(), bins=16, range=(0, 256))
            return hist.tolist()
            
        except Exception as e:
            logger.error(f"Error extracting LBP features: {e}")
            return [0] * 16
    
    def extract_gabor_features(self, image: np.ndarray) -> List[float]:
        """Extract Gabor filter features"""
        try:
            features = []
            
            # Create Gabor kernels
            for theta in [0, 45, 90, 135]:  # 4 orientations
                kernel = cv2.getGaborKernel((21, 21), 5, np.radians(theta), 10, 0.5, 0, ktype=cv2.CV_32F)
                filtered = cv2.filter2D(image, cv2.CV_8UC3, kernel)
                features.extend([np.mean(filtered), np.std(filtered)])
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting Gabor features: {e}")
            return [0] * 8
    
    def calculate_image_hash(self, image_path: str) -> str:
        """Calculate hash of image file"""
        try:
            with open(image_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {image_path}: {e}")
            return ""
    
    def save_embedding(self, offender_id: str, face_features: List[np.ndarray], 
                      face_locations: List[Tuple], image_hash: str) -> Optional[str]:
        """Save face features to file"""
        if not face_features:
            return None
        
        # Use the first face features as primary
        primary_features = face_features[0]
        
        embedding_path = self.embeddings_dir / f"{offender_id}.pkl"
        
        embedding_data = {
            'offender_id': offender_id,
            'primary_features': primary_features,
            'all_features': face_features,
            'face_locations': face_locations,
            'face_count': len(face_features),
            'image_hash': image_hash
        }
        
        with open(embedding_path, 'wb') as f:
            pickle.dump(embedding_data, f)
        
        return str(embedding_path)
    
    def process_image(self, image_path: str, offender_id: str = None) -> bool:
        """Process a single image and store face features"""
        try:
            if not offender_id:
                # Extract offender ID from filename
                offender_id = Path(image_path).stem
            
            # Check if already processed
            if self.is_processed(offender_id):
                logger.info(f"Image {offender_id} already processed, skipping")
                return True
            
            # Calculate image hash
            image_hash = self.calculate_image_hash(image_path)
            
            # Detect faces
            face_locations, face_images = self.detect_faces(image_path)
            
            if not face_images:
                logger.warning(f"No faces found in {image_path}")
                return False
            
            # Extract features from each face
            face_features = []
            for face_img in face_images:
                features = self.extract_face_features(face_img)
                if len(features) > 0:
                    face_features.append(features)
            
            if not face_features:
                logger.warning(f"No features extracted from {image_path}")
                return False
            
            # Save embeddings
            embedding_path = self.save_embedding(offender_id, face_features, face_locations, image_hash)
            
            if not embedding_path:
                return False
            
            # Get offender name
            name = "Unknown"
            if offender_id in self.offender_data:
                name = self.offender_data[offender_id].get('name', 'Unknown')
            
            # Store in database
            self.store_in_database(
                offender_id=offender_id,
                name=name,
                image_path=str(image_path),
                embedding_path=embedding_path,
                face_count=len(face_features),
                face_locations=face_locations,
                face_features=face_features,
                image_hash=image_hash
            )
            
            logger.info(f"Successfully processed {name} (ID: {offender_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return False
    
    def store_in_database(self, offender_id: str, name: str, image_path: str, 
                         embedding_path: str, face_count: int, face_locations: List[Tuple],
                         face_features: List[np.ndarray], image_hash: str):
        """Store face embedding metadata in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Convert data to strings for storage
        face_locations_str = json.dumps([[int(x) for x in loc] for loc in face_locations])
        face_features_str = json.dumps([f.tolist() for f in face_features])
        
        cursor.execute('''
            INSERT OR REPLACE INTO face_embeddings 
            (offender_id, name, image_path, embedding_path, face_count, face_locations, face_features, image_hash, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (offender_id, name, image_path, embedding_path, face_count, face_locations_str, face_features_str, image_hash))
        
        conn.commit()
        conn.close()
    
    def is_processed(self, offender_id: str) -> bool:
        """Check if an offender's image has already been processed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM face_embeddings WHERE offender_id = ?', (offender_id,))
        count = cursor.fetchone()[0]
        
        conn.close()
        return count > 0
    
    def process_all_images(self) -> Dict[str, bool]:
        """Process all images in the images directory"""
        if not self.images_dir.exists():
            logger.error(f"Images directory {self.images_dir} does not exist")
            return {}
        
        results = {}
        image_files = list(self.images_dir.glob("*.jpg")) + list(self.images_dir.glob("*.png"))
        
        logger.info(f"Processing {len(image_files)} images...")
        
        for image_path in image_files:
            offender_id = image_path.stem
            success = self.process_image(str(image_path), offender_id)
            results[offender_id] = success
        
        successful = sum(1 for success in results.values() if success)
        logger.info(f"Successfully processed {successful}/{len(image_files)} images")
        
        return results
    
    def load_embedding(self, offender_id: str) -> Optional[Dict]:
        """Load face embedding for a specific offender"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT embedding_path FROM face_embeddings WHERE offender_id = ?', (offender_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if not result:
            return None
        
        embedding_path = result[0]
        
        try:
            with open(embedding_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Error loading embedding for {offender_id}: {e}")
            return None
    
    def calculate_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """Calculate similarity between two feature vectors"""
        try:
            # Normalize features
            features1_norm = features1 / (np.linalg.norm(features1) + 1e-8)
            features2_norm = features2 / (np.linalg.norm(features2) + 1e-8)
            
            # Calculate cosine similarity
            similarity = np.dot(features1_norm, features2_norm)
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def search_by_face(self, query_image_path: str, top_k: int = 5, min_similarity: float = 0.3) -> List[Dict]:
        """Search for similar faces using a query image"""
        try:
            # Detect and extract features from query image
            query_locations, query_images = self.detect_faces(query_image_path)
            
            if not query_images:
                logger.warning("No faces detected in query image")
                return []
            
            query_features = self.extract_face_features(query_images[0])
            
            if len(query_features) == 0:
                logger.warning("No features extracted from query image")
                return []
            
            # Get all stored embeddings
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT offender_id, name, image_path, embedding_path FROM face_embeddings')
            results = cursor.fetchall()
            
            conn.close()
            
            similarities = []
            
            for offender_id, name, image_path, embedding_path in results:
                try:
                    # Load embedding
                    with open(embedding_path, 'rb') as f:
                        embedding_data = pickle.load(f)
                    
                    stored_features = embedding_data['primary_features']
                    
                    # Calculate similarity
                    similarity = self.calculate_similarity(query_features, stored_features)
                    
                    if similarity >= min_similarity:
                        similarities.append({
                            'offender_id': offender_id,
                            'name': name,
                            'image_path': image_path,
                            'similarity_score': similarity
                        })
                
                except Exception as e:
                    logger.error(f"Error comparing with {offender_id}: {e}")
                    continue
            
            # Sort by similarity score (highest first)
            similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # Log search
            self.log_search('face_search', query_image_path, len(similarities))
            
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Error in face search: {e}")
            return []
    
    def search_by_name(self, name_query: str) -> List[Dict]:
        """Search for offenders by name"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT offender_id, name, image_path, face_count 
            FROM face_embeddings 
            WHERE LOWER(name) LIKE LOWER(?)
            ORDER BY name
        ''', (f'%{name_query}%',))
        
        results = cursor.fetchall()
        conn.close()
        
        offenders = []
        for offender_id, name, image_path, face_count in results:
            offenders.append({
                'offender_id': offender_id,
                'name': name,
                'image_path': image_path,
                'face_count': face_count
            })
        
        # Log search
        self.log_search('name_search', name_query, len(offenders))
        
        return offenders
    
    def get_all_offenders(self) -> List[Dict]:
        """Get all processed offenders"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT offender_id, name, image_path, face_count, created_at
            FROM face_embeddings
            ORDER BY name
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        offenders = []
        for offender_id, name, image_path, face_count, created_at in results:
            offenders.append({
                'offender_id': offender_id,
                'name': name,
                'image_path': image_path,
                'face_count': face_count,
                'created_at': created_at
            })
        
        return offenders
    
    def log_search(self, query_type: str, query_data: str, results_count: int):
        """Log search queries for analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO search_history (query_type, query_data, results_count)
            VALUES (?, ?, ?)
        ''', (query_type, query_data, results_count))
        
        conn.commit()
        conn.close()
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get total offenders
        cursor.execute('SELECT COUNT(*) FROM face_embeddings')
        total_offenders = cursor.fetchone()[0]
        
        # Get total faces
        cursor.execute('SELECT SUM(face_count) FROM face_embeddings')
        total_faces = cursor.fetchone()[0] or 0
        
        # Get search history
        cursor.execute('SELECT COUNT(*) FROM search_history')
        total_searches = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_offenders': total_offenders,
            'total_faces': total_faces,
            'total_searches': total_searches,
            'database_path': self.db_path,
            'embeddings_dir': str(self.embeddings_dir)
        }
    
    def export_database(self, export_path: str = "opencv_face_export.json"):
        """Export database to JSON for backup"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all offenders
        cursor.execute('SELECT * FROM face_embeddings')
        offenders = cursor.fetchall()
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        
        # Convert to list of dictionaries
        offender_data = []
        for offender in offenders:
            offender_dict = dict(zip(column_names, offender))
            # Parse JSON fields
            if offender_dict['face_locations']:
                offender_dict['face_locations'] = json.loads(offender_dict['face_locations'])
            if offender_dict['face_features']:
                offender_dict['face_features'] = json.loads(offender_dict['face_features'])
            offender_data.append(offender_dict)
        
        conn.close()
        
        # Save to JSON
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(offender_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Database exported to {export_path}")
        return export_path


def main():
    """Main function to demonstrate the OpenCV face database"""
    print("🔍 OpenCV Face Database for Sex Offender Images")
    print("=" * 50)
    
    # Initialize database
    db = OpenCVFaceDatabase()
    
    # Process all images
    print("\n📸 Processing images...")
    results = db.process_all_images()
    
    # Show results
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    print(f"✅ Successfully processed {successful}/{total} images")
    
    # Show database stats
    stats = db.get_database_stats()
    print(f"\n📊 Database Statistics:")
    print(f"   Total Offenders: {stats['total_offenders']}")
    print(f"   Total Faces: {stats['total_faces']}")
    print(f"   Database Path: {stats['database_path']}")
    
    # Show all processed offenders
    offenders = db.get_all_offenders()
    if offenders:
        print(f"\n👥 Processed Offenders:")
        for offender in offenders:
            print(f"   {offender['name']} (ID: {offender['offender_id']}) - {offender['face_count']} face(s)")
    
    print(f"\n🎯 Database ready for face search!")
    print(f"   Use db.search_by_face('path/to/image.jpg') to search by face")
    print(f"   Use db.search_by_name('name') to search by name")


if __name__ == "__main__":
    main()
