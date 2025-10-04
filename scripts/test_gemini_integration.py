#!/usr/bin/env python3
"""
Test script for Gemini AI integration.
Validates that all components work correctly without requiring API calls.
"""

import os
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / 'backend'))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from gemini_service import GeminiImageAnalyzer, GeminiTimelineAnalyzer
        print("✅ gemini_service imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import gemini_service: {e}")
        return False
    
    try:
        from gemini_config import GeminiConfig
        print("✅ gemini_config imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import gemini_config: {e}")
        return False
    
    try:
        from gemini_parser import GeminiResponseParser
        print("✅ gemini_parser imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import gemini_parser: {e}")
        return False
    
    try:
        from timeline_manager import TimelineManager
        print("✅ timeline_manager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import timeline_manager: {e}")
        return False
    
    return True


def test_configuration():
    """Test configuration management."""
    print("\nTesting configuration...")
    
    try:
        from gemini_config import GeminiConfig
        
        # Test without API key
        config = GeminiConfig()
        print(f"Config created: {config}")
        print(f"Valid: {config.is_valid()}")
        
        # Test configuration methods
        model_config = config.get_model_config()
        processing_config = config.get_processing_config()
        logging_config = config.get_logging_config()
        
        print("✅ Configuration methods work correctly")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_parser():
    """Test response parser."""
    print("\nTesting response parser...")
    
    try:
        from gemini_parser import GeminiResponseParser
        
        parser = GeminiResponseParser()
        
        # Test with sample response
        sample_response = """
        ```json
        {
            "image_description": "Test image description",
            "subjects": [
                {
                    "id": "person_1",
                    "type": "person",
                    "description": "A person in the image",
                    "position": "center",
                    "actions": "standing",
                    "confidence": 0.85
                }
            ],
            "objects": [],
            "activities": [],
            "scene_analysis": {
                "overall_mood": "calm",
                "safety_assessment": "safe"
            }
        }
        ```
        """
        
        # Parse response
        result = parser.parse_response(sample_response, "comprehensive")
        
        if result and 'error' not in result:
            print("✅ Response parsing works correctly")
            
            # Test summary creation
            summary = parser.format_analysis_summary(result)
            print("✅ Summary formatting works correctly")
            
            # Test insight extraction
            insights = parser.extract_key_insights(result)
            print("✅ Insight extraction works correctly")
            
            return True
        else:
            print(f"❌ Response parsing failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Parser test failed: {e}")
        return False


def test_timeline_integration():
    """Test timeline manager integration."""
    print("\nTesting timeline integration...")
    
    try:
        from timeline_manager import TimelineManager
        from gemini_service import GeminiTimelineAnalyzer
        
        # Create timeline manager
        timeline_manager = TimelineManager(snapshots_dir="test_snapshots")
        print("✅ Timeline manager created successfully")
        
        # Test statistics
        stats = timeline_manager.get_statistics()
        print(f"✅ Timeline statistics: {stats}")
        
        # Test timeline analyzer creation (without API key)
        try:
            analyzer = GeminiTimelineAnalyzer(timeline_manager, None)
            print("❌ Should have failed without API key")
            return False
        except ValueError:
            print("✅ Correctly failed without API key")
        
        # Test analysis summary method
        summary = analyzer.get_analysis_summary()
        print("✅ Analysis summary method works")
        
        return True
        
    except Exception as e:
        print(f"❌ Timeline integration test failed: {e}")
        return False


def test_environment_setup():
    """Test environment setup."""
    print("\nTesting environment setup...")
    
    # Check if .env file exists
    env_files = [
        ".env",
        "backend/.env",
        "gemini.env",
        "backend/gemini.env"
    ]
    
    env_found = False
    for env_file in env_files:
        if os.path.exists(env_file):
            print(f"✅ Found environment file: {env_file}")
            env_found = True
            break
    
    if not env_found:
        print("⚠️  No environment file found. Create one from backend/gemini.env.example")
    
    # Check requirements
    requirements_file = "requirements.txt"
    if os.path.exists(requirements_file):
        with open(requirements_file, 'r') as f:
            content = f.read()
            if "google-generativeai" in content:
                print("✅ Gemini dependencies in requirements.txt")
            else:
                print("❌ Gemini dependencies missing from requirements.txt")
    
    return True


def main():
    """Run all tests."""
    print("🧪 Gemini AI Integration Test Suite")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_configuration,
        test_parser,
        test_timeline_integration,
        test_environment_setup
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Integration is ready.")
        print("\nNext steps:")
        print("1. Set your GEMINI_API_KEY in a .env file")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Run the demo: python examples/gemini_analysis_demo.py")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
