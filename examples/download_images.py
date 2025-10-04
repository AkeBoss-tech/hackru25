#!/usr/bin/env python3
"""
Temporary script to download offender images from the extracted URLs
"""

import json
import requests
import os
from pathlib import Path
import logging
from typing import Dict, List, Optional
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_image(image_url: str, offender_id: str, name: str = "") -> Optional[str]:
    """Download offender image with multiple strategies"""
    try:
        logger.info(f"Downloading image for {name} (ID: {offender_id}): {image_url}")
        
        # Try different headers to bypass protection
        headers_list = [
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site',
                'Referer': 'https://www.icrimewatch.net/'
            },
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.icrimewatch.net/'
            },
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        ]
        
        for i, headers in enumerate(headers_list):
            try:
                logger.info(f"Trying download method {i+1} for {offender_id}")
                response = requests.get(image_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    # Determine file extension
                    content_type = response.headers.get('content-type', '')
                    if 'jpeg' in content_type or 'jpg' in content_type:
                        ext = '.jpg'
                    elif 'png' in content_type:
                        ext = '.png'
                    else:
                        ext = '.jpg'  # Default
                    
                    filename = f"{offender_id}{ext}"
                    filepath = Path("sex-offenders/images") / filename
                    
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    logger.info(f"Successfully downloaded image: {filename}")
                    return str(filepath)
                else:
                    logger.warning(f"Method {i+1} failed with status {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"Method {i+1} failed: {e}")
                continue
        
        logger.error(f"All download methods failed for {offender_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error downloading image {image_url}: {e}")
        return None

def load_offender_data(json_file: str) -> List[Dict]:
    """Load offender data from JSON file"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} offenders from {json_file}")
        return data
    except Exception as e:
        logger.error(f"Error loading JSON file: {e}")
        return []

def main():
    """Main function to download images"""
    # Load the offender data
    json_file = "sex-offenders/data/offenders_with_images.json"
    offenders = load_offender_data(json_file)
    
    if not offenders:
        print("No offender data found!")
        return
    
    # Create images directory if it doesn't exist
    images_dir = Path("sex-offenders/images")
    images_dir.mkdir(exist_ok=True)
    
    downloaded_count = 0
    failed_count = 0
    
    print(f"Starting image download for {len(offenders)} offenders...")
    
    for i, offender in enumerate(offenders, 1):
        offender_id = offender.get('offender_id', f'offender_{i}')
        name = offender.get('name', 'Unknown')
        image_url = offender.get('detail_image_url')
        
        if not image_url:
            logger.warning(f"No image URL found for {name} (ID: {offender_id})")
            failed_count += 1
            continue
        
        # Check if image already exists
        existing_files = list(images_dir.glob(f"{offender_id}.*"))
        if existing_files:
            logger.info(f"Image already exists for {name} (ID: {offender_id})")
            downloaded_count += 1
            continue
        
        # Download the image
        result = download_image(image_url, offender_id, name)
        if result:
            downloaded_count += 1
        else:
            failed_count += 1
        
        # Add delay to be respectful
        time.sleep(1)
        
        # Progress update
        if i % 5 == 0:
            print(f"Progress: {i}/{len(offenders)} offenders processed")
    
    print(f"\nDownload completed!")
    print(f"Successfully downloaded: {downloaded_count} images")
    print(f"Failed downloads: {failed_count} images")
    print(f"Images saved to: {images_dir}")
    
    # List downloaded files
    image_files = list(images_dir.glob("*"))
    if image_files:
        print(f"\nDownloaded files:")
        for file in sorted(image_files):
            print(f"  {file.name}")

if __name__ == "__main__":
    main()
