#!/usr/bin/env python3
"""
Batch runner
"""

import sys
import os
import subprocess
import re
import signal
import atexit
from typing import List

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

from utils.send_api import APISender

# Global configuration
BATCHES = 5
EXPECTED_DIRECTORIES_PER_BATCH = 12

# Global variable to track current subprocess
current_process = None

def cleanup_subprocess():
    """Cleanup function to terminate subprocess on exit"""
    global current_process
    if current_process and current_process.poll() is None:
        print(f"\n🧹 Cleaning up subprocess (PID: {current_process.pid})...")
        try:
            # Kill the entire process group
            os.killpg(os.getpgid(current_process.pid), signal.SIGTERM)
            current_process.wait(timeout=5)
            print("✅ Subprocess terminated successfully")
        except (OSError, subprocess.TimeoutExpired):
            # Force kill if SIGTERM doesn't work
            try:
                os.killpg(os.getpgid(current_process.pid), signal.SIGKILL)
                print("✅ Subprocess force-killed")
            except OSError:
                pass

def signal_handler(signum, frame):
    """Handle termination signals and cleanup subprocess"""
    print(f"\n🛑 Received signal {signum}, terminating...")
    cleanup_subprocess()
    sys.exit(0)

def setup_signal_handlers():
    """Setup signal handlers for proper cleanup"""
    # Register cleanup function to run on normal exit
    atexit.register(cleanup_subprocess)
    
    # Register signal handlers for termination signals
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    # On Unix systems, also handle SIGHUP
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, signal_handler)

def parse_created_directories(output_text: str) -> List[str]:
    """Parse the output from main.py to extract created directory paths"""
    pattern = r"📁 Created new directory: (.+)"
    directories = re.findall(pattern, output_text)
    return directories

def verify_required_files(directories: List[str]) -> bool:
    """Verify that each directory contains the required player.py and requirements.txt files"""
    required_files = ['player.py', 'requirements.txt']
    
    for directory in directories:
        for required_file in required_files:
            file_path = os.path.join(directory, required_file)
            if not os.path.isfile(file_path):
                print(f"❌ Missing required file '{required_file}' in directory '{directory}'")
                return False
        print(f"✅ Verified required files in: {directory}")
    
    return True

def run_single_batch(batch_num: int) -> List[str]:
    """Run a single batch of main.py with proper subprocess management"""
    global current_process
    
    print(f"\n{'='*60}")
    print(f"🚀 STARTING BATCH {batch_num}/{BATCHES}")
    print(f"{'='*60}")
    
    try:
        # FIXED: Create subprocess in its own process group for proper termination
        current_process = subprocess.Popen(
            ["python", "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            universal_newlines=True,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None  # Unix only
        )
        
        output_lines = []
        
        # Stream output in real-time while capturing it
        while True:
            output = current_process.stdout.readline()
            if output == '' and current_process.poll() is not None:
                break
            if output:
                print(output, end='')  # Display in real-time
                output_lines.append(output)
        
        return_code = current_process.wait()
        
        if return_code != 0:
            print(f"❌ main.py exited with return code {return_code}")
            return []
        
        # Parse the captured output
        full_output = ''.join(output_lines)
        created_directories = parse_created_directories(full_output)
        
        print(f"\n📊 BATCH {batch_num} RESULTS:")
        print(f"   Expected directories: {EXPECTED_DIRECTORIES_PER_BATCH}")
        print(f"   Created directories: {len(created_directories)}")
        
        if len(created_directories) != EXPECTED_DIRECTORIES_PER_BATCH:
            print(f"⚠️  Warning: Expected {EXPECTED_DIRECTORIES_PER_BATCH} directories but found {len(created_directories)}")
        
        # Clear the current process reference after successful completion
        current_process = None
        
        return created_directories
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Batch {batch_num} interrupted by user")
        cleanup_subprocess()
        raise
    except Exception as e:
        print(f"❌ Error running batch {batch_num}: {e}")
        cleanup_subprocess()
        return []

def main():
    """Main function to run all batches and upload results"""
    print(f"🤖 Batch OpenRouter Prompt Processor (with proper subprocess management)")
    print(f"{'='*70}")
    print(f"🎯 Total Batches: {BATCHES}")
    print(f"📁 Expected Directories per Batch: {EXPECTED_DIRECTORIES_PER_BATCH}")
    print(f"📊 Total Expected Directories: {BATCHES * EXPECTED_DIRECTORIES_PER_BATCH}")
    print(f"{'='*70}")
    
    # FIXED: Setup signal handlers for proper subprocess cleanup
    setup_signal_handlers()
    
    all_created_directories = []
    
    try:
        # Run all batches
        for batch_num in range(1, BATCHES + 1):
            batch_directories = run_single_batch(batch_num)
            
            if not batch_directories:
                print(f"❌ Batch {batch_num} failed to create any directories. Stopping.")
                sys.exit(1)
            
            all_created_directories.extend(batch_directories)
            print(f"✅ Batch {batch_num} completed successfully")
        
        print(f"\n{'='*60}")
        print(f"🎉 ALL BATCHES COMPLETED")
        print(f"{'='*60}")
        print(f"📁 Total directories created: {len(all_created_directories)}")
        
        # Verify all directories have required files
        print(f"\n🔍 Verifying required files in all directories...")
        if not verify_required_files(all_created_directories):
            print(f"❌ Some directories are missing required files. Exiting program.")
            sys.exit(1)
        
        print(f"✅ All directories have required files!")
        
        # Upload files to API
        print(f"\n📤 Starting API uploads...")
        api_sender = APISender("https://api-huskyholdem.atcuw.org/submission/upload")
        
        success = api_sender.upload_all_directories(all_created_directories)
        
        if success:
            print(f"\n🎉 SUCCESS: All {len(all_created_directories)} bot directories uploaded successfully!")
        else:
            print(f"\n❌ FAILED: API upload process failed. Check logs above.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n\n👋 Operation cancelled by user.")
        cleanup_subprocess()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        cleanup_subprocess()
        sys.exit(1)

if __name__ == "__main__":
    main()
