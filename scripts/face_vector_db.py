#!/usr/bin/env python3
"""
Face Vector Database for Sex Offender Images
Uses face detection and recognition to create vector embeddings and enable similarity search
"""

import os
import json
import pickle
import numpy as np
import cv2
import face_recognition
from pathlib import Path
import logging
from typing import List, Dict, Tuple, Optional
import sqlite3
from datetime import datetime
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FaceVectorDatabase:
    def __init__(self, db_path: str = "face_vector_db.db", images_dir: str = "sex-offenders/images"):
        self.db_path = db_path
        self.images_dir = Path(images_dir)
        self.embeddings_dir = Path("face_embeddings")
        self.embeddings_dir.mkdir(exist_ok=True)
        
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
    
    def detect_and_encode_faces(self, image_path: str) -> Tuple[List[np.ndarray], List[Tuple]]:
        """Detect faces in image and return encodings and locations"""
        try:
            # Load image
            image = face_recognition.load_image_file(image_path)
            
            # Find face locations
            face_locations = face_recognition.face_locations(image, model="hog")
            
            if not face_locations:
                logger.warning(f"No faces detected in {image_path}")
                return [], []
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            logger.info(f"Detected {len(face_encodings)} faces in {image_path}")
            return face_encodings, face_locations
            
        except Exception as e:
            logger.error(f"Error processing {image_path}: {e}")
            return [], []
    
    def save_embedding(self, offender_id: str, face_encodings: List[np.ndarray], face_locations: List[Tuple]):
        """Save face embeddings to file"""
        if not face_encodings:
            return None
        
        # Use the first face encoding as the primary one
        primary_encoding = face_encodings[0]
        
        embedding_path = self.embeddings_dir / f"{offender_id}.pkl"
        
        embedding_data = {
            'offender_id': offender_id,
            'primary_encoding': primary_encoding,
            'all_encodings': face_encodings,
            'face_locations': face_locations,
            'face_count': len(face_encodings)
        }
        
        with open(embedding_path, 'wb') as f:
            pickle.dump(embedding_data, f)
        
        return str(embedding_path)
    
    def process_image(self, image_path: str, offender_id: str = None) -> bool:
        """Process a single image and store face embeddings"""
        try:
            if not offender_id:
                # Extract offender ID from filename
                offender_id = Path(image_path).stem
            
            # Check if already processed
            if self.is_processed(offender_id):
                logger.info(f"Image {offender_id} already processed, skipping")
                return True
            
            # Detect and encode faces
            face_encodings, face_locations = self.detect_and_encode_faces(image_path)
            
            if not face_encodings:
                logger.warning(f"No faces found in {image_path}")
                return False
            
            # Save embeddings
            embedding_path = self.save_embedding(offender_id, face_encodings, face_locations)
            
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
                face_count=len(face_encodings),
                face_locations=face_locations
            )
            
            logger.info(f"Successfully processed {name} (ID: {offender_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return False
    
    def store_in_database(self, offender_id: str, name: str, image_path: str, 
                         embedding_path: str, face_count: int, face_locations: List[Tuple]):
        """Store face embedding metadata in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Convert face locations to string for storage
        face_locations_str = json.dumps(face_locations)
        
        cursor.execute('''
            INSERT OR REPLACE INTO face_embeddings 
            (offender_id, name, image_path, embedding_path, face_count, face_locations, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (offender_id, name, image_path, embedding_path, face_count, face_locations_str))
        
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
    
    def search_by_face(self, query_image_path: str, top_k: int = 5, tolerance: float = 0.6) -> List[Dict]:
        """Search for similar faces using a query image"""
        try:
            # Detect and encode faces in query image
            query_encodings, query_locations = self.detect_and_encode_faces(query_image_path)
            
            if not query_encodings:
                logger.warning("No faces detected in query image")
                return []
            
            query_encoding = query_encodings[0]  # Use first face
            
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
                    
                    stored_encoding = embedding_data['primary_encoding']
                    
                    # Calculate face distance
                    face_distance = face_recognition.face_distance([stored_encoding], query_encoding)[0]
                    
                    # Convert distance to similarity score (lower distance = higher similarity)
                    similarity_score = 1 - face_distance
                    
                    if face_distance <= tolerance:
                        similarities.append({
                            'offender_id': offender_id,
                            'name': name,
                            'image_path': image_path,
                            'similarity_score': similarity_score,
                            'face_distance': face_distance
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
    
    def export_database(self, export_path: str = "face_vector_export.json"):
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
            # Parse face locations
            if offender_dict['face_locations']:
                offender_dict['face_locations'] = json.loads(offender_dict['face_locations'])
            offender_data.append(offender_dict)
        
        conn.close()
        
        # Save to JSON
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(offender_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Database exported to {export_path}")
        return export_path


def main():
    """Main function to demonstrate the face vector database"""
    print("🔍 Face Vector Database for Sex Offender Images")
    print("=" * 50)
    
    # Initialize database
    db = FaceVectorDatabase()
    
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
