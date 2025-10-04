#!/usr/bin/env python3
"""
Quick test script to verify Gemini API functionality.
Tests basic image analysis and report generation.
"""

import os
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_gemini_config():
    """Test if Gemini configuration loads correctly."""
    print("Testing Gemini Configuration...")
    
    try:
        from backend.gemini_config import GeminiConfig
        
        config = GeminiConfig()
        print(f"[OK] Config loaded: {config}")
        print(f"   - API Key: {'Set' if config.api_key else 'Missing'}")
        print(f"   - Model: {config.model_name}")
        print(f"   - Valid: {config.is_valid()}")
        
        if not config.is_valid():
            print("[ERROR] Configuration is invalid!")
            return False
            
        return True
        
    except Exception as e:
        print(f"[ERROR] Config test failed: {e}")
        return False

def test_gemini_service():
    """Test if Gemini service can be initialized."""
    print("\nTesting Gemini Service...")
    
    try:
        from backend.gemini_service import GeminiImageAnalyzer
        
        # Try to initialize the analyzer
        analyzer = GeminiImageAnalyzer()
        print(f"[OK] GeminiImageAnalyzer initialized: {analyzer}")
        print(f"   - Model: {analyzer.model_name}")
        print(f"   - API configured: {analyzer.api_key is not None}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Service test failed: {e}")
        return False

def test_gemini_with_sample_image():
    """Test Gemini with a sample image."""
    print("\nTesting Gemini with Sample Image...")
    
    try:
        from backend.gemini_service import GeminiImageAnalyzer
        import cv2
        import numpy as np
        
        # Create a simple test image (a red rectangle)
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        test_image[100:200, 100:300] = [0, 0, 255]  # Red rectangle
        
        # Save test image
        test_image_path = "test_image.jpg"
        cv2.imwrite(test_image_path, test_image)
        print(f"[OK] Created test image: {test_image_path}")
        
        # Initialize analyzer
        analyzer = GeminiImageAnalyzer()
        
        # Create a simple prompt
        prompt = """Analyze this image and provide a brief report. 
        Format as JSON with fields: summary, objects_detected, activity, confidence.
        Keep it very brief (1-2 sentences)."""
        
        print("Sending request to Gemini...")
        
        # Analyze the image
        result = analyzer.analyze_image(test_image_path, prompt)
        
        if result:
            print("[OK] Gemini analysis successful!")
            print(f"   - Result type: {type(result)}")
            print(f"   - Result: {json.dumps(result, indent=2)}")
            
            # Clean up test image
            os.remove(test_image_path)
            return True
        else:
            print("[ERROR] Gemini returned no result")
            os.remove(test_image_path)
            return False
            
    except Exception as e:
        print(f"[ERROR] Image analysis test failed: {e}")
        # Clean up test image if it exists
        if os.path.exists("test_image.jpg"):
            os.remove("test_image.jpg")
        return False

def test_auto_reporter():
    """Test if auto reporter can be initialized."""
    print("\nTesting Auto Reporter...")
    
    try:
        from backend.auto_gemini_reporter import AutoGeminiReporter
        
        # Create reporter instance
        reporter = AutoGeminiReporter()
        print(f"[OK] AutoGeminiReporter initialized: {reporter}")
        print(f"   - Enabled: {reporter.enabled}")
        print(f"   - Has analyzer: {reporter.gemini_analyzer is not None}")
        
        # Try to enable it
        try:
            reporter.enable()
            print(f"   - After enable: {reporter.enabled}")
            print(f"   - Stats: {reporter.get_stats()}")
            
            # Disable it
            reporter.disable()
            print(f"   - After disable: {reporter.enabled}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Auto reporter enable failed: {e}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Auto reporter test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Gemini API Test Suite")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"[OK] Found .env file: {env_file}")
    else:
        print(f"[WARNING] No .env file found. Make sure GEMINI_API_KEY is set in environment.")
    
    # Run tests
    tests = [
        test_gemini_config,
        test_gemini_service,
        test_gemini_with_sample_image,
        test_auto_reporter
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"[ERROR] Test {test.__name__} crashed: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    
    passed = sum(results)
    total = len(results)
    
    print(f"[OK] Passed: {passed}/{total}")
    print(f"[ERROR] Failed: {total - passed}/{total}")
    
    if passed == total:
        print("[SUCCESS] All tests passed! Gemini should be working.")
    else:
        print("[WARNING] Some tests failed. Check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
