# Face Vector Database for Sex Offender Images

A local vector database system that uses face detection and recognition to create embeddings from sex offender images and enables similarity search functionality.

## 🎯 Features

- **Face Detection**: Automatically detects faces in offender images
- **Vector Embeddings**: Creates 128-dimensional face encodings using deep learning
- **Similarity Search**: Find similar faces using query images
- **Name Search**: Search offenders by name
- **SQLite Database**: Local storage for embeddings and metadata
- **Interactive Interface**: User-friendly command-line interface
- **Image Viewing**: Display images with face detection results

## 📋 Prerequisites

### System Requirements
- Python 3.7+
- macOS, Linux, or Windows
- At least 2GB RAM
- 1GB free disk space

### Dependencies
- `face-recognition` - Face detection and recognition
- `dlib` - Machine learning library
- `opencv-python` - Computer vision
- `numpy` - Numerical computing
- `sqlite3` - Database (built-in)

## 🚀 Installation

### 1. Install Face Recognition Dependencies

**Option A: Automatic Setup (Recommended)**
```bash
cd /Users/akashdubey/Documents/CodingProjects/hackru25
source venv/bin/activate
python scripts/setup_face_recognition.py
```

**Option B: Manual Installation**

**macOS:**
```bash
# Install CMake
brew install cmake

# Install dlib and face-recognition
pip install dlib
pip install face-recognition
```

**Linux:**
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y build-essential cmake
sudo apt-get install -y libopenblas-dev liblapack-dev
sudo apt-get install -y libx11-dev libgtk-3-dev
sudo apt-get install -y libboost-python-dev

# Install Python packages
pip install dlib
pip install face-recognition
```

**Windows:**
```bash
# Install Visual Studio Build Tools first
# Then install CMake
# Finally:
pip install dlib
pip install face-recognition
```

### 2. Verify Installation
```bash
python -c "import face_recognition; print('✅ Face recognition installed successfully!')"
```

## 📖 Usage

### 1. Initialize and Process Images

**Process all offender images:**
```bash
python scripts/face_vector_db.py
```

This will:
- Create the vector database
- Process all images in `sex-offenders/images/`
- Extract face encodings
- Store embeddings in SQLite database

### 2. Interactive Search Interface

**Launch the search interface:**
```bash
python scripts/face_search_interface.py
```

**Menu Options:**
1. **Search by Face Image** - Upload an image to find similar faces
2. **Search by Name** - Search offenders by name
3. **List All Offenders** - View all processed offenders
4. **Database Statistics** - View database stats
5. **Reprocess Images** - Rebuild the database
6. **Export Database** - Export to JSON
7. **View Offender Image** - Display specific offender image
8. **Exit**

### 3. Programmatic Usage

```python
from face_vector_db import FaceVectorDatabase

# Initialize database
db = FaceVectorDatabase()

# Process all images
results = db.process_all_images()

# Search by face
similar_faces = db.search_by_face('path/to/query_image.jpg', top_k=5)

# Search by name
offenders = db.search_by_name('John Doe')

# Get database stats
stats = db.get_database_stats()
```

## 🔍 Search Examples

### Face Similarity Search
```python
# Search for similar faces
results = db.search_by_face('query_photo.jpg', top_k=5, tolerance=0.6)

for result in results:
    print(f"Name: {result['name']}")
    print(f"Similarity: {result['similarity_score']:.3f}")
    print(f"Distance: {result['face_distance']:.3f}")
```

### Name Search
```python
# Search by name
results = db.search_by_name('Smith')

for result in results:
    print(f"Name: {result['name']}")
    print(f"ID: {result['offender_id']}")
    print(f"Faces: {result['face_count']}")
```

## 📊 Database Structure

### SQLite Tables

**face_embeddings:**
- `offender_id` - Unique offender identifier
- `name` - Offender name
- `image_path` - Path to original image
- `embedding_path` - Path to face encoding file
- `face_count` - Number of faces detected
- `face_locations` - Face bounding box coordinates
- `created_at` - Timestamp

**search_history:**
- `query_type` - Type of search performed
- `query_data` - Search parameters
- `results_count` - Number of results found
- `created_at` - Timestamp

### File Structure
```
face_embeddings/
├── 2311001.pkl    # Face encoding for offender 2311001
├── 2319666.pkl    # Face encoding for offender 2319666
└── ...

face_vector_db.db  # SQLite database
```

## ⚙️ Configuration

### Search Parameters

**Tolerance Levels:**
- `0.4` - Very strict (very similar faces only)
- `0.6` - Default (good balance)
- `0.8` - Loose (more matches, less accuracy)

**Top K Results:**
- `1-5` - Few, most relevant results
- `5-10` - More comprehensive results
- `10+` - Extensive search results

### Performance Tuning

**Face Detection Models:**
- `"hog"` - Faster, less accurate (default)
- `"cnn"` - Slower, more accurate (requires GPU)

**Image Processing:**
- Images are automatically resized for optimal processing
- Face locations are stored for visualization
- Multiple faces per image are supported

## 🛠️ Troubleshooting

### Common Issues

**1. "No module named 'face_recognition'"**
```bash
pip install face-recognition
```

**2. "dlib installation failed"**
- Install CMake first: `brew install cmake` (macOS) or `sudo apt-get install cmake` (Linux)
- Install system dependencies for dlib

**3. "No faces detected"**
- Check image quality and lighting
- Ensure faces are clearly visible
- Try different tolerance levels

**4. "Database locked"**
- Close any other processes using the database
- Restart the application

### Performance Issues

**Slow Processing:**
- Use HOG model instead of CNN
- Process images in smaller batches
- Ensure sufficient RAM available

**Memory Issues:**
- Process images one at a time
- Clear unused variables
- Restart application periodically

## 📈 Advanced Features

### Custom Face Detection
```python
# Use CNN model for better accuracy
face_locations = face_recognition.face_locations(image, model="cnn")

# Adjust face detection sensitivity
face_locations = face_recognition.face_locations(image, number_of_times_to_upsample=2)
```

### Batch Processing
```python
# Process multiple images
image_paths = ["image1.jpg", "image2.jpg", "image3.jpg"]
for path in image_paths:
    db.process_image(path)
```

### Export and Backup
```python
# Export database
export_path = db.export_database("backup.json")

# Get all offenders
offenders = db.get_all_offenders()
```

## 🔒 Security and Privacy

- All data is stored locally
- No external API calls for face recognition
- Images and embeddings remain on your system
- Database can be encrypted if needed

## 📝 Legal Notice

This system is for educational and research purposes only. Users must ensure compliance with:
- Local laws and regulations
- Data privacy requirements
- Website terms of service
- Respectful use of offender data

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section
2. Verify all dependencies are installed
3. Check system requirements
4. Review error messages and logs

## 📚 Additional Resources

- [face-recognition Documentation](https://face-recognition.readthedocs.io/)
- [dlib Documentation](http://dlib.net/)
- [OpenCV Documentation](https://docs.opencv.org/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
