#!/usr/bin/env python3
"""
Setup script for face recognition dependencies
Installs face-recognition and dlib with proper system dependencies
"""

import subprocess
import sys
import os
import platform

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return False

def install_face_recognition():
    """Install face recognition dependencies"""
    print("🚀 Setting up Face Recognition Dependencies")
    print("=" * 50)
    
    system = platform.system().lower()
    
    if system == "darwin":  # macOS
        print("🍎 Detected macOS")
        
        # Install CMake if not present
        if not run_command("which cmake", "Checking for CMake"):
            print("📦 Installing CMake via Homebrew...")
            if not run_command("brew install cmake", "Installing CMake"):
                print("❌ Failed to install CMake. Please install it manually:")
                print("   brew install cmake")
                return False
        
        # Install dlib
        print("📦 Installing dlib...")
        if not run_command("pip install dlib", "Installing dlib"):
            print("❌ Failed to install dlib")
            return False
        
        # Install face-recognition
        print("📦 Installing face-recognition...")
        if not run_command("pip install face-recognition", "Installing face-recognition"):
            print("❌ Failed to install face-recognition")
            return False
    
    elif system == "linux":
        print("🐧 Detected Linux")
        
        # Install system dependencies
        print("📦 Installing system dependencies...")
        system_deps = [
            "sudo apt-get update",
            "sudo apt-get install -y build-essential cmake",
            "sudo apt-get install -y libopenblas-dev liblapack-dev",
            "sudo apt-get install -y libx11-dev libgtk-3-dev",
            "sudo apt-get install -y libboost-python-dev"
        ]
        
        for cmd in system_deps:
            if not run_command(cmd, f"Running: {cmd}"):
                print("❌ Failed to install system dependencies")
                return False
        
        # Install dlib
        print("📦 Installing dlib...")
        if not run_command("pip install dlib", "Installing dlib"):
            print("❌ Failed to install dlib")
            return False
        
        # Install face-recognition
        print("📦 Installing face-recognition...")
        if not run_command("pip install face-recognition", "Installing face-recognition"):
            print("❌ Failed to install face-recognition")
            return False
    
    elif system == "windows":
        print("🪟 Detected Windows")
        print("⚠️  Windows installation can be complex. Please follow these steps:")
        print("1. Install Visual Studio Build Tools")
        print("2. Install CMake")
        print("3. Run: pip install dlib")
        print("4. Run: pip install face-recognition")
        return False
    
    else:
        print(f"❌ Unsupported system: {system}")
        return False
    
    print("\n✅ Face recognition setup completed!")
    return True

def test_installation():
    """Test if face recognition is working"""
    print("\n🧪 Testing installation...")
    
    try:
        import face_recognition
        import dlib
        print("✅ face-recognition imported successfully")
        print("✅ dlib imported successfully")
        
        # Test basic functionality
        import numpy as np
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        face_locations = face_recognition.face_locations(test_image)
        print("✅ face_recognition.face_locations() working")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def main():
    """Main setup function"""
    print("🔍 Face Recognition Setup for Sex Offender Database")
    print("=" * 60)
    
    # Check if already installed
    try:
        import face_recognition
        import dlib
        print("✅ Face recognition already installed!")
        if test_installation():
            print("🎉 Everything is working correctly!")
            return
    except ImportError:
        pass
    
    # Install dependencies
    if install_face_recognition():
        if test_installation():
            print("\n🎉 Face recognition setup completed successfully!")
            print("You can now run the face vector database:")
            print("   python scripts/face_vector_db.py")
            print("   python scripts/face_search_interface.py")
        else:
            print("\n❌ Installation completed but tests failed")
            print("Please check the error messages above")
    else:
        print("\n❌ Setup failed")
        print("Please install dependencies manually")

if __name__ == "__main__":
    main()
