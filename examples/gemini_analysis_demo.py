"""
Demo script for Gemini AI image analysis integration.
Shows how to use the Gemini service to analyze snapshots and timeline events.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / 'backend'))

from gemini_service import GeminiImageAnalyzer, GeminiTimelineAnalyzer
from gemini_config import GeminiConfig
from gemini_parser import GeminiResponseParser
from timeline_manager import TimelineManager


def setup_logging():
    """Setup logging for the demo."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def demo_single_image_analysis():
    """Demo analyzing a single image."""
    print("\n=== Single Image Analysis Demo ===")
    
    try:
        # Initialize analyzer
        analyzer = GeminiImageAnalyzer()
        
        # Find a test image
        test_image_path = None
        possible_paths = [
            "bus.jpg",
            "../bus.jpg", 
            "sex-offenders/images/10712834.jpg",
            "../sex-offenders/images/10712834.jpg"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                test_image_path = path
                break
        
        if not test_image_path:
            print("No test image found. Please add a test image to run this demo.")
            return
        
        print(f"Analyzing image: {test_image_path}")
        
        # Perform comprehensive analysis
        result = analyzer.analyze_image(test_image_path, "comprehensive")
        
        if result and 'error' not in result:
            print("✅ Analysis completed successfully!")
            print(f"Description: {result.get('image_description', 'N/A')[:100]}...")
            
            subjects = result.get('subjects', [])
            print(f"Subjects detected: {len(subjects)}")
            
            objects = result.get('objects', [])
            print(f"Objects detected: {len(objects)}")
            
            activities = result.get('activities', [])
            print(f"Activities detected: {len(activities)}")
            
            # Save result
            output_path = "single_image_analysis.json"
            analyzer.save_analysis_result(result, output_path)
            print(f"Results saved to: {output_path}")
            
        else:
            print("❌ Analysis failed")
            if result:
                print(f"Error: {result.get('error_message', 'Unknown error')}")
    
    except Exception as e:
        print(f"❌ Demo failed: {e}")


def demo_batch_analysis():
    """Demo batch analysis of multiple images."""
    print("\n=== Batch Analysis Demo ===")
    
    try:
        # Initialize analyzer
        analyzer = GeminiImageAnalyzer()
        
        # Find test images
        image_paths = []
        sex_offenders_dir = Path("../sex-offenders/images")
        if sex_offenders_dir.exists():
            image_paths = list(sex_offenders_dir.glob("*.jpg"))[:3]  # Limit to 3 images
        
        if not image_paths:
            print("No test images found for batch analysis.")
            return
        
        print(f"Analyzing {len(image_paths)} images...")
        
        # Perform batch analysis
        results = analyzer.batch_analyze_images(
            [str(path) for path in image_paths],
            analysis_type="objects"
        )
        
        # Process results
        successful_analyses = 0
        for i, result in enumerate(results):
            if result and 'error' not in result:
                successful_analyses += 1
                detected_items = result.get('detected_items', [])
                print(f"Image {i+1}: {len(detected_items)} items detected")
            else:
                print(f"Image {i+1}: Analysis failed")
        
        print(f"✅ Batch analysis completed: {successful_analyses}/{len(image_paths)} successful")
        
    except Exception as e:
        print(f"❌ Batch demo failed: {e}")


def demo_timeline_integration():
    """Demo integration with timeline manager."""
    print("\n=== Timeline Integration Demo ===")
    
    try:
        # Initialize timeline manager
        timeline_manager = TimelineManager(snapshots_dir="../web_app/timeline_snapshots")
        
        # Get recent events
        recent_events = timeline_manager.get_events(limit=3)
        
        if not recent_events:
            print("No timeline events found. Run the video processing first to generate events.")
            return
        
        print(f"Found {len(recent_events)} recent events")
        
        # Initialize timeline analyzer
        timeline_analyzer = GeminiTimelineAnalyzer(timeline_manager)
        
        # Analyze events
        for i, event in enumerate(recent_events):
            event_id = event['event_id']
            print(f"Analyzing event {i+1}: {event_id}")
            
            result = timeline_analyzer.analyze_event(event_id, "comprehensive")
            
            if result and 'error' not in result:
                print(f"✅ Event {i+1} analyzed successfully")
                
                # Extract key insights
                parser = GeminiResponseParser()
                insights = parser.extract_key_insights(result)
                if insights:
                    print(f"Key insights: {insights[0]}")
            else:
                print(f"❌ Event {i+1} analysis failed")
        
        # Get analysis summary
        summary = timeline_analyzer.get_analysis_summary()
        print(f"\nAnalysis Summary: {summary}")
        
    except Exception as e:
        print(f"❌ Timeline demo failed: {e}")


def demo_parser_validation():
    """Demo JSON response parsing and validation."""
    print("\n=== Response Parser Demo ===")
    
    try:
        parser = GeminiResponseParser()
        
        # Test with sample response
        sample_response = """
        ```json
        {
            "image_description": "A surveillance camera view showing a parking lot with several cars",
            "subjects": [
                {
                    "id": "person_1",
                    "type": "person",
                    "description": "A person walking near a car",
                    "position": "center-right",
                    "actions": "walking",
                    "attributes": ["wearing dark clothing"],
                    "confidence": 0.85
                }
            ],
            "objects": [
                {
                    "id": "car_1",
                    "type": "vehicle",
                    "description": "A white sedan parked in the lot",
                    "position": "center",
                    "purpose": "transportation",
                    "confidence": 0.92
                }
            ],
            "activities": [
                {
                    "description": "Person walking in parking lot",
                    "participants": ["person_1"],
                    "objects_involved": [],
                    "significance": "normal",
                    "confidence": 0.78
                }
            ],
            "scene_analysis": {
                "overall_mood": "calm",
                "safety_assessment": "safe",
                "notable_events": ["person walking"],
                "recommendations": []
            }
        }
        ```
        """
        
        # Parse response
        parsed_result = parser.parse_response(sample_response, "comprehensive")
        
        if parsed_result and 'error' not in parsed_result:
            print("✅ Response parsed successfully!")
            
            # Create summary
            summary = parser.format_analysis_summary(parsed_result)
            print(f"Summary: {summary}")
            
            # Extract insights
            insights = parser.extract_key_insights(parsed_result)
            print(f"Insights: {insights}")
            
        else:
            print("❌ Response parsing failed")
            if parsed_result:
                print(f"Error: {parsed_result.get('error_message', 'Unknown error')}")
    
    except Exception as e:
        print(f"❌ Parser demo failed: {e}")


def demo_configuration():
    """Demo configuration management."""
    print("\n=== Configuration Demo ===")
    
    try:
        # Load configuration
        config = GeminiConfig()
        
        print(f"Configuration: {config}")
        print(f"Valid: {config.is_valid()}")
        print(f"Model: {config.model_name}")
        print(f"Analysis type: {config.analysis_type}")
        
        if config.is_valid():
            print("✅ Configuration is valid")
            
            model_config = config.get_model_config()
            print(f"Model config: {model_config}")
            
            processing_config = config.get_processing_config()
            print(f"Processing config: {processing_config}")
        else:
            print("❌ Configuration is invalid")
            print("Please set GEMINI_API_KEY environment variable")
    
    except Exception as e:
        print(f"❌ Configuration demo failed: {e}")


def main():
    """Run all demos."""
    print("🤖 Gemini AI Analysis Integration Demo")
    print("=" * 50)
    
    setup_logging()
    
    # Check if API key is configured
    if not os.getenv('GEMINI_API_KEY'):
        print("⚠️  GEMINI_API_KEY not found in environment variables")
        print("Please set your Gemini API key to run the demos:")
        print("export GEMINI_API_KEY='your_api_key_here'")
        print("\nRunning configuration demo only...")
        demo_configuration()
        return
    
    # Run demos
    demo_configuration()
    demo_single_image_analysis()
    demo_batch_analysis()
    demo_timeline_integration()
    demo_parser_validation()
    
    print("\n🎉 All demos completed!")
    print("\nNext steps:")
    print("1. Set up your GEMINI_API_KEY in a .env file")
    print("2. Run video processing to generate timeline events")
    print("3. Use the Gemini services in your application")


if __name__ == "__main__":
    main()
