#!/usr/bin/env python3
"""
Test script to verify the client can handle multiple games correctly.
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runner import Runner
from player import SimplePlayer

def test_continuous_client():
    """Test the continuous client functionality"""
    print("Testing continuous client...")
    
    # Create a test bot
    bot = SimplePlayer()
    
    # Create a runner
    runner = Runner(host='localhost', port=5001, result_path='test_results.log', sim=True)
    runner.set_bot(bot)
    
    print("Starting client. Connect to a server running on localhost:5001")
    print("The client will play multiple games with the same connection.")
    print("Press Ctrl+C to stop the test.")
    
    try:
        runner.run()
    except KeyboardInterrupt:
        print("\nStopping client...")
        runner.close()
        print(f"Test completed. Total games played: {runner.get_game_count()}")
        print(f"Total score: {runner.get_total_score()}")

if __name__ == "__main__":
    test_continuous_client() 