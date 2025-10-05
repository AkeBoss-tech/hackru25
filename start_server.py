#!/usr/bin/env python3
"""
Simple script to start the central processing server
"""

import subprocess
import sys
import os

print("🚀 Starting Central Processing Server...")

# Change to web_app directory and start the server
os.chdir('web_app')
subprocess.run([sys.executable, 'app.py'])
