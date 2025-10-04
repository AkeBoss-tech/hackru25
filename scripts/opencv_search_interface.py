#!/usr/bin/env python3
"""
OpenCV Face Search Interface for Sex Offender Vector Database
Interactive interface for searching faces using OpenCV-based face detection
"""

import os
import sys
from pathlib import Path
import cv2
import numpy as np
from opencv_face_db import OpenCVFaceDatabase
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OpenCVSearchInterface:
    def __init__(self):
        self.db = OpenCVFaceDatabase()
        self.running = True
    
    def display_menu(self):
        """Display the main menu"""
        print("\n" + "="*60)
        print("🔍 OPENCV FACE SEARCH INTERFACE - Sex Offender Database")
        print("="*60)
        print("1. 📸 Search by Face Image")
        print("2. 👤 Search by Name")
        print("3. 📋 List All Offenders")
        print("4. 📊 Database Statistics")
        print("5. 🔄 Reprocess Images")
        print("6. 📤 Export Database")
        print("7. 🖼️  View Offender Image")
        print("8. 🧪 Test Face Detection")
        print("9. ❌ Exit")
        print("="*60)
    
    def search_by_face(self):
        """Search for similar faces using an image"""
        print("\n🔍 FACE SEARCH")
        print("-" * 30)
        
        # Get query image path
        query_path = input("Enter path to query image: ").strip()
        
        if not os.path.exists(query_path):
            print("❌ Image file not found!")
            return
        
        # Get search parameters
        try:
            top_k = int(input("Number of results to show (default 5): ") or "5")
            min_similarity = float(input("Minimum similarity 0.0-1.0 (default 0.3): ") or "0.3")
        except ValueError:
            print("❌ Invalid input, using defaults")
            top_k = 5
            min_similarity = 0.3
        
        print(f"\n🔍 Searching for similar faces...")
        print(f"   Query image: {query_path}")
        print(f"   Max results: {top_k}")
        print(f"   Min similarity: {min_similarity}")
        
        # Perform search
        results = self.db.search_by_face(query_path, top_k=top_k, min_similarity=min_similarity)
        
        if not results:
            print("❌ No similar faces found!")
            return
        
        print(f"\n✅ Found {len(results)} similar faces:")
        print("-" * 50)
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['name']} (ID: {result['offender_id']})")
            print(f"   Similarity: {result['similarity_score']:.3f}")
            print(f"   Image: {result['image_path']}")
            print()
        
        # Option to view images
        if input("View images? (y/n): ").lower() == 'y':
            self.view_search_results(results)
    
    def search_by_name(self):
        """Search for offenders by name"""
        print("\n👤 NAME SEARCH")
        print("-" * 30)
        
        name_query = input("Enter name to search for: ").strip()
        
        if not name_query:
            print("❌ Please enter a name!")
            return
        
        print(f"\n🔍 Searching for: '{name_query}'")
        
        results = self.db.search_by_name(name_query)
        
        if not results:
            print("❌ No offenders found with that name!")
            return
        
        print(f"\n✅ Found {len(results)} offenders:")
        print("-" * 50)
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['name']} (ID: {result['offender_id']})")
            print(f"   Faces detected: {result['face_count']}")
            print(f"   Image: {result['image_path']}")
            print()
        
        # Option to view images
        if input("View images? (y/n): ").lower() == 'y':
            self.view_search_results(results)
    
    def list_all_offenders(self):
        """List all processed offenders"""
        print("\n📋 ALL OFFENDERS")
        print("-" * 30)
        
        offenders = self.db.get_all_offenders()
        
        if not offenders:
            print("❌ No offenders in database!")
            return
        
        print(f"✅ Found {len(offenders)} offenders:")
        print("-" * 50)
        
        for i, offender in enumerate(offenders, 1):
            print(f"{i}. {offender['name']} (ID: {offender['offender_id']})")
            print(f"   Faces: {offender['face_count']}")
            print(f"   Added: {offender['created_at']}")
            print()
    
    def show_database_stats(self):
        """Show database statistics"""
        print("\n📊 DATABASE STATISTICS")
        print("-" * 30)
        
        stats = self.db.get_database_stats()
        
        print(f"Total Offenders: {stats['total_offenders']}")
        print(f"Total Faces: {stats['total_faces']}")
        print(f"Total Searches: {stats['total_searches']}")
        print(f"Database Path: {stats['database_path']}")
        print(f"Embeddings Dir: {stats['embeddings_dir']}")
    
    def reprocess_images(self):
        """Reprocess all images"""
        print("\n🔄 REPROCESSING IMAGES")
        print("-" * 30)
        
        confirm = input("This will reprocess all images. Continue? (y/n): ").lower()
        if confirm != 'y':
            print("❌ Cancelled")
            return
        
        print("🔄 Reprocessing images...")
        results = self.db.process_all_images()
        
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        print(f"✅ Successfully processed {successful}/{total} images")
    
    def export_database(self):
        """Export database to JSON"""
        print("\n📤 EXPORT DATABASE")
        print("-" * 30)
        
        export_path = input("Enter export file path (default: opencv_face_export.json): ").strip()
        if not export_path:
            export_path = "opencv_face_export.json"
        
        try:
            result_path = self.db.export_database(export_path)
            print(f"✅ Database exported to: {result_path}")
        except Exception as e:
            print(f"❌ Export failed: {e}")
    
    def view_offender_image(self):
        """View a specific offender's image"""
        print("\n🖼️  VIEW OFFENDER IMAGE")
        print("-" * 30)
        
        offender_id = input("Enter offender ID: ").strip()
        
        if not offender_id:
            print("❌ Please enter an offender ID!")
            return
        
        # Get offender info
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT name, image_path FROM face_embeddings WHERE offender_id = ?', (offender_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if not result:
            print(f"❌ Offender {offender_id} not found!")
            return
        
        name, image_path = result
        
        if not os.path.exists(image_path):
            print(f"❌ Image file not found: {image_path}")
            return
        
        print(f"👤 {name} (ID: {offender_id})")
        print(f"📁 Image: {image_path}")
        
        # Display image
        try:
            image = cv2.imread(image_path)
            if image is not None:
                # Resize if too large
                height, width = image.shape[:2]
                if width > 800:
                    scale = 800 / width
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    image = cv2.resize(image, (new_width, new_height))
                
                cv2.imshow(f"{name} - {offender_id}", image)
                print("Press any key to close image...")
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            else:
                print("❌ Could not load image")
        except Exception as e:
            print(f"❌ Error displaying image: {e}")
    
    def test_face_detection(self):
        """Test face detection on an image"""
        print("\n🧪 TEST FACE DETECTION")
        print("-" * 30)
        
        image_path = input("Enter path to test image: ").strip()
        
        if not os.path.exists(image_path):
            print("❌ Image file not found!")
            return
        
        try:
            # Load and display image with face detection
            image = cv2.imread(image_path)
            if image is None:
                print("❌ Could not load image")
                return
            
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.db.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            print(f"🔍 Detected {len(faces)} faces")
            
            # Draw rectangles around faces
            for (x, y, w, h) in faces:
                cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Resize if too large
            height, width = image.shape[:2]
            if width > 800:
                scale = 800 / width
                new_width = int(width * scale)
                new_height = int(height * scale)
                image = cv2.resize(image, (new_width, new_height))
            
            cv2.imshow(f"Face Detection Test - {len(faces)} faces", image)
            print("Press any key to close...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            
        except Exception as e:
            print(f"❌ Error testing face detection: {e}")
    
    def view_search_results(self, results):
        """View images from search results"""
        print("\n🖼️  VIEWING SEARCH RESULTS")
        print("-" * 30)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['name']} (ID: {result['offender_id']})")
            
            if 'similarity_score' in result:
                print(f"   Similarity: {result['similarity_score']:.3f}")
            
            image_path = result['image_path']
            
            if not os.path.exists(image_path):
                print(f"   ❌ Image not found: {image_path}")
                continue
            
            try:
                image = cv2.imread(image_path)
                if image is not None:
                    # Resize if too large
                    height, width = image.shape[:2]
                    if width > 600:
                        scale = 600 / width
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        image = cv2.resize(image, (new_width, new_height))
                    
                    cv2.imshow(f"{result['name']} - {result['offender_id']}", image)
                    print("   Press any key for next image, 'q' to quit...")
                    key = cv2.waitKey(0)
                    cv2.destroyAllWindows()
                    
                    if key == ord('q'):
                        break
                else:
                    print(f"   ❌ Could not load image")
            except Exception as e:
                print(f"   ❌ Error displaying image: {e}")
    
    def run(self):
        """Run the interactive interface"""
        print("🚀 Starting OpenCV Face Search Interface...")
        
        while self.running:
            try:
                self.display_menu()
                choice = input("\nEnter your choice (1-9): ").strip()
                
                if choice == '1':
                    self.search_by_face()
                elif choice == '2':
                    self.search_by_name()
                elif choice == '3':
                    self.list_all_offenders()
                elif choice == '4':
                    self.show_database_stats()
                elif choice == '5':
                    self.reprocess_images()
                elif choice == '6':
                    self.export_database()
                elif choice == '7':
                    self.view_offender_image()
                elif choice == '8':
                    self.test_face_detection()
                elif choice == '9':
                    print("👋 Goodbye!")
                    self.running = False
                else:
                    print("❌ Invalid choice! Please enter 1-9.")
                
                if self.running:
                    input("\nPress Enter to continue...")
            
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                self.running = False
            except Exception as e:
                print(f"❌ Error: {e}")
                if self.running:
                    input("\nPress Enter to continue...")


def main():
    """Main function"""
    interface = OpenCVSearchInterface()
    interface.run()


if __name__ == "__main__":
    main()
