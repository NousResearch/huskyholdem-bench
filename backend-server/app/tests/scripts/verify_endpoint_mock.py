#!/usr/bin/env python3
"""
Test script for the /verify endpoint
Usage: python test_verify_endpoint.py
"""

import asyncio
import aiohttp
import os
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Global Variables - Modify these to test different files
# ──────────────────────────────────────────────────────────────────────────────

# Path to your player.py file (relative or absolute)
PLAYER_PY_PATH = "C:/Users/nguye/Desktop/code/poker-all/poker-client/player.py"

# Path to your requirements.txt file (relative or absolute)
REQUIREMENTS_TXT_PATH = "C:/Users/nguye/Desktop/code/poker-all/poker-client/requirements.txt"

# API base URL
API_BASE_URL = "http://localhost:8002"
TOKEN = "64d29958-45e5-4842-a430-b046bccdb168"

# ──────────────────────────────────────────────────────────────────────────────

async def test_verify_endpoint():
    """Test the /verify endpoint with the specified files."""
    
    # Check if files exist
    player_py_path = Path(PLAYER_PY_PATH)
    requirements_path = Path(REQUIREMENTS_TXT_PATH)
    
    if not player_py_path.exists():
        print(f"❌ Error: player.py file not found at {player_py_path}")
        print(f"   Current working directory: {os.getcwd()}")
        return
    
    if not requirements_path.exists():
        print(f"❌ Error: requirements.txt file not found at {requirements_path}")
        print(f"   Current working directory: {os.getcwd()}")
        return
    
    print(f"✅ Found player.py at: {player_py_path.absolute()}")
    print(f"✅ Found requirements.txt at: {requirements_path.absolute()}")
    print()
    
    # Prepare the files for upload using FormData
    data = aiohttp.FormData()
    
    # Add the python file
    with open(player_py_path, 'rb') as f:
        data.add_field('python_file', 
                      f.read(),
                      filename='player.py',
                      content_type='text/x-python')
    
    # Add the requirements file
    with open(requirements_path, 'rb') as f:
        data.add_field('packages_file', 
                      f.read(),
                      filename='requirements.txt',
                      content_type='text/plain')
    
    # You'll need to add authentication here
    headers = {
        'Authorization': f'Bearer {TOKEN}'
    }
    
    url = f"{API_BASE_URL}/sim/verify"
    
    print(f"🚀 Testing endpoint: {url}")
    print(f"📁 Files being uploaded:")
    print(f"   - player.py: {player_py_path.name}")
    print(f"   - requirements.txt: {requirements_path.name}")
    print()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, headers=headers) as response:
                print(f"📊 Response Status: {response.status}")
                print(f"📊 Response Headers: {dict(response.headers)}")
                print()
                
                response_text = await response.text()
                print(f"📄 Response Body:")
                print(response_text)
                print()
                
                if response.status == 200:
                    print("✅ Success! Files were verified successfully.")
                elif response.status == 401:
                    print("❌ Authentication required. You need to add a valid auth token.")
                elif response.status == 400:
                    print("❌ Bad request. Check the error message above.")
                else:
                    print(f"❌ Unexpected status code: {response.status}")
                    
    except aiohttp.ClientConnectorError:
        print(f"❌ Connection error: Could not connect to {API_BASE_URL}")
        print("   Make sure your server is running with: docker-compose up")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def create_sample_files():
    """Create sample test files if they don't exist."""
    test_dir = Path("test_files")
    test_dir.mkdir(exist_ok=True)
    
    # Create sample player.py
    player_py_content = '''"""
Sample player implementation for testing
"""
import random

def play_move(game_state):
    """
    Sample player function that makes random moves
    """
    # This is just a sample - replace with your actual implementation
    available_moves = game_state.get('available_moves', [])
    if available_moves:
        return random.choice(available_moves)
    return None

if __name__ == "__main__":
    print("Player module loaded successfully")
'''
    
    # Create sample requirements.txt
    requirements_content = '''# Sample requirements for testing
# Add your actual dependencies here
requests>=2.25.0
numpy>=1.20.0
'''
    
    player_py_path = test_dir / "player.py"
    requirements_path = test_dir / "requirements.txt"
    
    if not player_py_path.exists():
        with open(player_py_path, 'w') as f:
            f.write(player_py_content)
        print(f"✅ Created sample player.py at {player_py_path}")
    
    if not requirements_path.exists():
        with open(requirements_path, 'w') as f:
            f.write(requirements_content)
        print(f"✅ Created sample requirements.txt at {requirements_path}")
    
    return player_py_path, requirements_path

def main():
    """Main function to run the test."""
    print("🧪 Testing /verify endpoint")
    print("=" * 50)
    
    # Check if sample files need to be created
    player_py_path = Path(PLAYER_PY_PATH)
    requirements_path = Path(REQUIREMENTS_TXT_PATH)
    
    if not player_py_path.exists() or not requirements_path.exists():
        print("📝 Sample files not found. Creating them...")
        create_sample_files()
        print()
    
    # Run the test
    asyncio.run(test_verify_endpoint())

if __name__ == "__main__":
    main() 