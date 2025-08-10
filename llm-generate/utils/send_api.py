#!/usr/bin/env python3
"""
API sender for uploading bot files to HuskyHoldem API
Handles file uploads via the /submission/upload endpoint
"""

import os
import requests
from typing import List, Tuple
from pathlib import Path

class APISender:
    """
    Handles uploading bot files to the HuskyHoldem API
    """
    
    def __init__(self, api_url: str):
        """
        Initialize the API sender
        
        Args:
            api_url: The full URL to the upload endpoint
        """
        self.api_url = api_url
        self.required_files = ['player.py', 'requirements.txt']
    
    def verify_directory_files(self, directory: str) -> bool:
        """
        Verify that a directory contains all required files
        
        Args:
            directory: Path to the directory to check
            
        Returns:
            True if all required files exist, False otherwise
        """
        for required_file in self.required_files:
            file_path = os.path.join(directory, required_file)
            if not os.path.isfile(file_path):
                print(f"❌ Missing {required_file} in {directory}")
                return False
        return True
    
    def upload_directory(self, directory: str) -> bool:
        """
        Upload the bot files from a single directory to the API
        
        Args:
            directory: Path to the directory containing player.py and requirements.txt
            
        Returns:
            True if upload successful, False otherwise
        """
        if not self.verify_directory_files(directory):
            return False
        
        directory_name = os.path.basename(directory)
        
        try:
            # Prepare files for upload
            files_to_upload = []
            
            # Read player.py
            player_path = os.path.join(directory, 'player.py')
            with open(player_path, 'rb') as f:
                player_content = f.read()
            files_to_upload.append(('files', ('player.py', player_content, 'text/x-python')))
            
            # Read requirements.txt
            requirements_path = os.path.join(directory, 'requirements.txt')
            with open(requirements_path, 'rb') as f:
                requirements_content = f.read()
            files_to_upload.append(('files', ('requirements.txt', requirements_content, 'text/plain')))
            
            # Additional form data (if needed by API)
            form_data = {
                'bot_name': directory_name,
                'description': f'Bot generated from {directory_name}'
            }
            
            print(f"📤 Uploading files from: {directory_name}")
            
            # Make the API request
            response = requests.post(
                self.api_url,
                files=files_to_upload,
                data=form_data,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"✅ Successfully uploaded: {directory_name}")
                return True
            else:
                print(f"❌ Upload failed for {directory_name}")
                print(f"   Status Code: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error uploading {directory_name}: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error uploading {directory_name}: {e}")
            return False
    
    def upload_all_directories(self, directories: List[str]) -> bool:
        """
        Upload bot files from all directories to the API
        
        Args:
            directories: List of directory paths to upload
            
        Returns:
            True if all uploads successful, False if any failed
        """
        if not directories:
            print("⚠️  No directories to upload")
            return True
        
        print(f"📤 Starting upload of {len(directories)} bot directories...")
        
        successful_uploads = 0
        failed_uploads = 0
        
        for i, directory in enumerate(directories, 1):
            print(f"\n📤 [{i}/{len(directories)}] Processing: {os.path.basename(directory)}")
            
            if self.upload_directory(directory):
                successful_uploads += 1
            else:
                failed_uploads += 1
                print(f"❌ Upload failed for {directory}. Stopping upload process.")
                break
        
        print(f"\n📊 UPLOAD SUMMARY:")
        print(f"   ✅ Successful: {successful_uploads}")
        print(f"   ❌ Failed: {failed_uploads}")
        print(f"   📁 Total: {len(directories)}")
        
        if failed_uploads > 0:
            print(f"❌ Upload process failed due to {failed_uploads} failed upload(s)")
            return False
        
        print(f"🎉 All uploads completed successfully!")
        return True
    
    def test_api_connection(self) -> bool:
        """
        Test if the API endpoint is reachable
        
        Returns:
            True if API is reachable, False otherwise
        """
        try:
            # Try a simple GET request to test connectivity
            test_url = self.api_url.replace('/upload', '')  # Remove /upload for testing
            response = requests.get(test_url, timeout=10)
            print(f"✅ API endpoint is reachable (Status: {response.status_code})")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ API endpoint not reachable: {e}")
            return False