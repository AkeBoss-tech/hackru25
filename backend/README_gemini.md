# Gemini AI Integration

This module provides AI-powered image analysis using Google's Gemini 2.5 Flash model. It integrates with the timeline manager to analyze snapshots captured during object detection events.

## Features

- **Image Analysis**: Comprehensive analysis of surveillance images
- **Object Detection**: AI-powered object and subject identification
- **Activity Recognition**: Behavioral analysis and activity detection
- **Timeline Integration**: Seamless integration with timeline events
- **JSON Responses**: Structured, parseable analysis results
- **Batch Processing**: Analyze multiple images efficiently
- **Error Handling**: Robust error handling and validation

## Components

### 1. GeminiImageAnalyzer (`gemini_service.py`)

Core service for analyzing images with Gemini AI.

```python
from backend.gemini_service import GeminiImageAnalyzer

# Initialize analyzer
analyzer = GeminiImageAnalyzer()

# Analyze single image
result = analyzer.analyze_image("path/to/image.jpg", "comprehensive")

# Batch analysis
results = analyzer.batch_analyze_images(["image1.jpg", "image2.jpg"])
```

### 2. GeminiTimelineAnalyzer (`gemini_service.py`)

Specialized analyzer for timeline events and snapshots.

```python
from backend.gemini_service import GeminiTimelineAnalyzer
from backend.timeline_manager import TimelineManager

# Initialize timeline manager and analyzer
timeline_manager = TimelineManager()
analyzer = GeminiTimelineAnalyzer(timeline_manager)

# Analyze specific event
result = analyzer.analyze_event("event_123", "comprehensive")

# Analyze recent events
results = analyzer.analyze_recent_events(limit=5)
```

### 3. GeminiConfig (`gemini_config.py`)

Configuration management for Gemini API settings.

```python
from backend.gemini_config import GeminiConfig

# Load configuration
config = GeminiConfig()

# Check if valid
if config.is_valid():
    print(f"Using model: {config.model_name}")
```

### 4. GeminiResponseParser (`gemini_parser.py`)

JSON response parser with validation and formatting.

```python
from backend.gemini_parser import GeminiResponseParser

parser = GeminiResponseParser()

# Parse response
result = parser.parse_response(raw_response, "comprehensive")

# Create summary
summary = parser.format_analysis_summary(result)

# Extract insights
insights = parser.extract_key_insights(result)
```

## Setup

### 1. Install Dependencies

```bash
pip install google-generativeai python-dotenv
```

### 2. Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the API key

### 3. Configure Environment

Create a `.env` file in your project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL_NAME=gemini-2.0-flash-exp
GEMINI_ANALYSIS_TYPE=comprehensive
GEMINI_BATCH_SIZE=3
GEMINI_RATE_LIMIT_DELAY=0.5
GEMINI_SAVE_RESULTS=true
GEMINI_OUTPUT_DIR=analysis_results
```

Or use the provided example:

```bash
cp backend/gemini.env.example .env
# Edit .env with your API key
```

## Usage Examples

### Basic Image Analysis

```python
import os
from backend.gemini_service import GeminiImageAnalyzer

# Set API key
os.environ['GEMINI_API_KEY'] = 'your_api_key'

# Initialize analyzer
analyzer = GeminiImageAnalyzer()

# Analyze image
result = analyzer.analyze_image("snapshot.jpg", "comprehensive")

if result and 'error' not in result:
    print(f"Description: {result['image_description']}")
    print(f"Subjects: {len(result.get('subjects', []))}")
    print(f"Objects: {len(result.get('objects', []))}")
    print(f"Activities: {len(result.get('activities', []))}")
```

### Timeline Event Analysis

```python
from backend.gemini_service import GeminiTimelineAnalyzer
from backend.timeline_manager import TimelineManager

# Initialize services
timeline_manager = TimelineManager()
analyzer = GeminiTimelineAnalyzer(timeline_manager)

# Get recent events
events = timeline_manager.get_events(limit=5)

# Analyze each event
for event in events:
    event_id = event['event_id']
    result = analyzer.analyze_event(event_id, "comprehensive")
    
    if result:
        print(f"Event {event_id} analyzed successfully")
        # Process results...
```

### Batch Processing

```python
# Analyze multiple images
image_paths = ["image1.jpg", "image2.jpg", "image3.jpg"]
results = analyzer.batch_analyze_images(image_paths, "objects")

for i, result in enumerate(results):
    if result:
        items = result.get('detected_items', [])
        print(f"Image {i+1}: {len(items)} items detected")
```

## Analysis Types

### 1. Comprehensive Analysis
Complete analysis including subjects, objects, activities, and scene assessment.

```python
result = analyzer.analyze_image("image.jpg", "comprehensive")
```

Response structure:
```json
{
    "image_description": "Detailed scene description",
    "subjects": [...],
    "objects": [...],
    "activities": [...],
    "scene_analysis": {
        "overall_mood": "calm/active/concerning",
        "safety_assessment": "safe/potential_concern/requires_attention",
        "notable_events": [...],
        "recommendations": [...]
    },
    "technical_quality": {...}
}
```

### 2. Object Analysis
Focus on object detection and classification.

```python
result = analyzer.analyze_image("image.jpg", "objects")
```

Response structure:
```json
{
    "detected_items": [
        {
            "id": "unique_id",
            "type": "person/vehicle/object",
            "class": "specific_classification",
            "description": "detailed_description",
            "position": "approximate_location",
            "confidence": 0.0-1.0
        }
    ],
    "object_counts": {
        "people": 0,
        "vehicles": 0,
        "objects": 0
    }
}
```

### 3. Activity Analysis
Focus on behavioral analysis and activities.

```python
result = analyzer.analyze_image("image.jpg", "activities")
```

### 4. Description Analysis
Generate detailed scene descriptions.

```python
result = analyzer.analyze_image("image.jpg", "description")
```

## Response Parsing

The response parser provides validation and formatting:

```python
from backend.gemini_parser import GeminiResponseParser

parser = GeminiResponseParser()

# Parse and validate response
result = parser.parse_response(raw_response, "comprehensive")

# Check validation status
if result.get('_parser_metadata', {}).get('validation_status') == 'valid':
    print("Response is valid")
    
    # Create summary
    summary = parser.format_analysis_summary(result)
    print(f"Summary: {summary}")
    
    # Extract key insights
    insights = parser.extract_key_insights(result)
    print(f"Insights: {insights}")
```

## Error Handling

The service includes comprehensive error handling:

```python
try:
    result = analyzer.analyze_image("image.jpg")
    
    if result and 'error' not in result:
        # Process successful result
        process_result(result)
    else:
        # Handle analysis error
        error_msg = result.get('error_message', 'Unknown error')
        print(f"Analysis failed: {error_msg}")
        
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | Required | Your Gemini API key |
| `GEMINI_MODEL_NAME` | `gemini-2.0-flash-exp` | Gemini model to use |
| `GEMINI_ANALYSIS_TYPE` | `comprehensive` | Default analysis type |
| `GEMINI_BATCH_SIZE` | `3` | Batch processing size |
| `GEMINI_RATE_LIMIT_DELAY` | `0.5` | Delay between requests (seconds) |
| `GEMINI_SAVE_RESULTS` | `true` | Save results to files |
| `GEMINI_OUTPUT_DIR` | `analysis_results` | Output directory |
| `GEMINI_LOG_LEVEL` | `INFO` | Logging level |

### Model Options

- `gemini-2.0-flash-exp` (Recommended) - Latest experimental model
- `gemini-1.5-flash` - Fast model for quick analysis
- `gemini-1.5-pro` - High-quality model for detailed analysis
- `gemini-1.0-pro` - Stable production model

## Performance Considerations

### Rate Limits
- Gemini API has rate limits
- Use `GEMINI_RATE_LIMIT_DELAY` to control request frequency
- Batch processing includes automatic delays

### Memory Usage
- Large images are automatically resized
- Results are cached in memory
- Use `clear_analysis_results()` to free memory

### Cost Optimization
- Use appropriate analysis types for your needs
- Consider using `objects` or `description` for simpler analysis
- Batch processing reduces API overhead

## Troubleshooting

### Common Issues

1. **API Key Error**
   ```
   ValueError: Gemini API key not provided
   ```
   Solution: Set `GEMINI_API_KEY` environment variable

2. **Model Not Found**
   ```
   Failed to initialize Gemini model
   ```
   Solution: Check model name and API key validity

3. **JSON Parse Error**
   ```
   JSON parsing failed
   ```
   Solution: The parser includes error recovery and will return raw response

4. **Rate Limit Exceeded**
   ```
   Rate limit exceeded
   ```
   Solution: Increase `GEMINI_RATE_LIMIT_DELAY`

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('backend.gemini_service').setLevel(logging.DEBUG)
```

## Demo Script

Run the demo script to test the integration:

```bash
cd examples
python gemini_analysis_demo.py
```

The demo includes:
- Single image analysis
- Batch processing
- Timeline integration
- Response parsing
- Configuration validation

## Integration with Existing Code

The Gemini integration is designed to work alongside your existing video processing pipeline:

1. **Timeline Events**: Automatically analyze captured snapshots
2. **Web Interface**: Add analysis results to your web dashboard
3. **Alerts**: Use safety assessments for automated alerts
4. **Storage**: Save analysis results for historical review

## Future Enhancements

Potential future improvements:
- Real-time streaming analysis
- Custom model fine-tuning
- Multi-modal analysis (video + audio)
- Integration with other AI services
- Advanced filtering and search
- Automated alerting based on analysis results
