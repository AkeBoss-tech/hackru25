#!/usr/bin/env python3
"""
Test script for OpenCV Face Search functionality
Demonstrates face search capabilities without interactive interface
"""

import os
import sys
from pathlib import Path
from opencv_face_db import OpenCVFaceDatabase
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_face_search():
    """Test the face search functionality"""
    print("🔍 Testing OpenCV Face Search Functionality")
    print("=" * 50)
    
    # Initialize database
    db = OpenCVFaceDatabase()
    
    # Show database stats
    stats = db.get_database_stats()
    print(f"\n📊 Database Statistics:")
    print(f"   Total Offenders: {stats['total_offenders']}")
    print(f"   Total Faces: {stats['total_faces']}")
    print(f"   Total Searches: {stats['total_searches']}")
    
    if stats['total_offenders'] == 0:
        print("\n❌ No offenders in database. Please run the main script first:")
        print("   python scripts/opencv_face_db.py")
        return
    
    # List all offenders
    offenders = db.get_all_offenders()
    print(f"\n👥 Processed Offenders ({len(offenders)}):")
    for i, offender in enumerate(offenders, 1):
        print(f"   {i}. {offender['name']} (ID: {offender['offender_id']}) - {offender['face_count']} face(s)")
    
    # Test name search
    print(f"\n🔍 Testing Name Search:")
    test_names = ["JAMES", "JOSE", "THOMAS"]
    
    for name in test_names:
        results = db.search_by_name(name)
        print(f"   Search for '{name}': {len(results)} results")
        for result in results:
            print(f"     - {result['name']} (ID: {result['offender_id']})")
    
    # Test face similarity search using one of the existing images
    print(f"\n🔍 Testing Face Similarity Search:")
    
    # Get the first offender's image
    if offenders:
        first_offender = offenders[0]
        test_image_path = first_offender['image_path']
        
        if os.path.exists(test_image_path):
            print(f"   Using test image: {first_offender['name']} ({test_image_path})")
            
            # Search for similar faces
            results = db.search_by_face(test_image_path, top_k=3, min_similarity=0.1)
            
            print(f"   Found {len(results)} similar faces:")
            for i, result in enumerate(results, 1):
                print(f"     {i}. {result['name']} (ID: {result['offender_id']})")
                print(f"        Similarity: {result['similarity_score']:.3f}")
        else:
            print(f"   ❌ Test image not found: {test_image_path}")
    
    # Test face detection on a sample image
    print(f"\n🧪 Testing Face Detection:")
    if offenders:
        test_image_path = offenders[0]['image_path']
        if os.path.exists(test_image_path):
            face_locations, face_images = db.detect_faces(test_image_path)
            print(f"   Detected {len(face_locations)} faces in {Path(test_image_path).name}")
            
            if face_locations:
                print(f"   Face locations: {face_locations}")
        else:
            print(f"   ❌ Test image not found: {test_image_path}")
    
    print(f"\n✅ Face search testing completed!")
    print(f"\n💡 To use the interactive interface:")
    print(f"   python scripts/opencv_search_interface.py")

def test_face_detection_on_sample():
    """Test face detection on a sample image"""
    print("\n🧪 Testing Face Detection on Sample Image")
    print("-" * 40)
    
    db = OpenCVFaceDatabase()
    
    # Find a sample image
    images_dir = Path("sex-offenders/images")
    if images_dir.exists():
        image_files = list(images_dir.glob("*.jpg"))
        if image_files:
            sample_image = str(image_files[0])
            print(f"Testing face detection on: {Path(sample_image).name}")
            
            face_locations, face_images = db.detect_faces(sample_image)
            print(f"Detected {len(face_locations)} faces")
            
            if face_locations:
                for i, (x, y, x2, y2) in enumerate(face_locations):
                    print(f"  Face {i+1}: ({x}, {y}) to ({x2}, {y2})")
        else:
            print("No images found in sex-offenders/images/")
    else:
        print("Images directory not found")

def main():
    """Main test function"""
    try:
        test_face_search()
        test_face_detection_on_sample()
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()
