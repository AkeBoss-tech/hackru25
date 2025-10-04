# OpenCV Face Vector Database for Sex Offender Images

A local vector database system that uses OpenCV's built-in face detection and custom feature extraction to create embeddings from sex offender images and enables similarity search functionality.

## 🎯 Features

- **OpenCV Face Detection**: Uses Haar cascades for reliable face detection
- **Custom Feature Extraction**: Combines histogram, LBP, gradient, and Gabor features
- **Vector Embeddings**: Creates high-dimensional feature vectors for similarity search
- **Similarity Search**: Find similar faces using query images
- **Name Search**: Search offenders by name
- **SQLite Database**: Local storage for embeddings and metadata
- **Interactive Interface**: User-friendly command-line interface
- **Image Viewing**: Display images with face detection results
- **No External Dependencies**: Works with standard OpenCV installation

## 📋 Prerequisites

### System Requirements
- Python 3.7+
- macOS, Linux, or Windows
- At least 1GB RAM
- 500MB free disk space

### Dependencies
- `opencv-python` - Computer vision and face detection
- `numpy` - Numerical computing
- `sqlite3` - Database (built-in)
- `pickle` - Serialization (built-in)

## 🚀 Installation

### 1. Install Dependencies

**All platforms:**
```bash
cd /Users/akashdubey/Documents/CodingProjects/hackru25
source venv/bin/activate
pip install opencv-python numpy
```

**Verify Installation:**
```bash
python -c "import cv2; print('✅ OpenCV installed successfully!')"
```

## 📖 Usage

### 1. Initialize and Process Images

**Process all offender images:**
```bash
python scripts/opencv_face_db.py
```

This will:
- Create the vector database
- Process all images in `sex-offenders/images/`
- Extract face features using multiple methods
- Store embeddings in SQLite database

### 2. Interactive Search Interface

**Launch the search interface:**
```bash
python scripts/opencv_search_interface.py
```

**Menu Options:**
1. **Search by Face Image** - Upload an image to find similar faces
2. **Search by Name** - Search offenders by name
3. **List All Offenders** - View all processed offenders
4. **Database Statistics** - View database stats
5. **Reprocess Images** - Rebuild the database
6. **Export Database** - Export to JSON
7. **View Offender Image** - Display specific offender image
8. **Test Face Detection** - Test face detection on any image
9. **Exit**

### 3. Programmatic Usage

```python
from opencv_face_db import OpenCVFaceDatabase

# Initialize database
db = OpenCVFaceDatabase()

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
results = db.search_by_face('query_photo.jpg', top_k=5, min_similarity=0.3)

for result in results:
    print(f"Name: {result['name']}")
    print(f"Similarity: {result['similarity_score']:.3f}")
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
- `face_features` - Extracted feature vectors
- `image_hash` - MD5 hash of image file
- `created_at` - Timestamp

**search_history:**
- `query_type` - Type of search performed
- `query_data` - Search parameters
- `results_count` - Number of results found
- `created_at` - Timestamp

### File Structure
```
opencv_embeddings/
├── 2311001.pkl    # Face features for offender 2311001
├── 2319666.pkl    # Face features for offender 2319666
└── ...

opencv_face_db.db  # SQLite database
```

## ⚙️ Feature Extraction Methods

### 1. Histogram Features
- 32-bin histogram of pixel intensities
- Captures overall brightness distribution

### 2. LBP (Local Binary Pattern) Features
- 16-bin histogram of local texture patterns
- Captures local texture information

### 3. Gradient Features
- Sobel edge detection in X and Y directions
- Captures edge and shape information

### 4. Gabor Filter Features
- 4 orientations (0°, 45°, 90°, 135°)
- Captures texture and orientation information

### Combined Feature Vector
- Total dimension: ~2000+ features
- Normalized for similarity calculation
- Cosine similarity for matching

## 🔍 Search Parameters

### Similarity Thresholds
- `0.1-0.2` - Very loose (many matches, low accuracy)
- `0.3-0.4` - Default (good balance)
- `0.5-0.6` - Strict (few matches, high accuracy)
- `0.7+` - Very strict (very similar faces only)

### Top K Results
- `1-5` - Few, most relevant results
- `5-10` - More comprehensive results
- `10+` - Extensive search results

## 🛠️ Troubleshooting

### Common Issues

**1. "No module named 'cv2'"**
```bash
pip install opencv-python
```

**2. "No faces detected"**
- Check image quality and lighting
- Ensure faces are clearly visible
- Try different similarity thresholds
- Use the "Test Face Detection" feature

**3. "Database locked"**
- Close any other processes using the database
- Restart the application

**4. "Low similarity scores"**
- Try lower similarity thresholds
- Check if query image has good face visibility
- Ensure faces are front-facing

### Performance Issues

**Slow Processing:**
- Process images in smaller batches
- Ensure sufficient RAM available
- Close other applications

**Memory Issues:**
- Process images one at a time
- Clear unused variables
- Restart application periodically

## 📈 Advanced Features

### Custom Face Detection
```python
# Adjust face detection parameters
faces = db.face_cascade.detectMultiScale(
    gray,
    scaleFactor=1.05,  # More sensitive
    minNeighbors=3,    # Less strict
    minSize=(50, 50)   # Larger minimum face size
)
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
- No external API calls
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

- [OpenCV Documentation](https://docs.opencv.org/)
- [Haar Cascade Classifiers](https://docs.opencv.org/3.4/d1/d5c/tutorial_py_face_detection.html)
- [Local Binary Patterns](https://en.wikipedia.org/wiki/Local_binary_patterns)
- [Gabor Filters](https://en.wikipedia.org/wiki/Gabor_filter)
- [SQLite Documentation](https://www.sqlite.org/docs.html)

## 🆚 Comparison with face-recognition

| Feature | OpenCV Face DB | face-recognition |
|---------|----------------|------------------|
| Installation | Easy (pip install) | Complex (requires dlib) |
| Dependencies | Minimal | Heavy (dlib, CMake) |
| Accuracy | Good | Excellent |
| Speed | Fast | Moderate |
| Face Detection | Haar Cascades | HOG/CNN |
| Feature Extraction | Custom (4 methods) | Deep Learning |
| Similarity | Cosine | Euclidean Distance |
| Platform Support | Universal | Limited (compilation issues) |

## 🎯 Use Cases

1. **Educational Research** - Study face recognition algorithms
2. **Security Applications** - Local face matching systems
3. **Data Analysis** - Analyze face patterns in datasets
4. **Prototype Development** - Quick face recognition prototypes
5. **Offline Systems** - No internet required
