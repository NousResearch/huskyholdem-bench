#!/usr/bin/env python3
"""
Test script to verify the continuous game system works correctly.
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import threading
from server import PokerEngineServer

def test_continuous_games():
    """Test the continuous game system"""
    print("Testing continuous game system...")
    
    # Create a server with 2 players
    server = PokerEngineServer(host='localhost', port=5001, num_players=2, debug=True, sim=False)
    
    # Start server in a separate thread
    server_thread = threading.Thread(target=server.start_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Give server time to start
    time.sleep(1)
    
    print("Server started. You can now connect 2 clients to test continuous games.")
    print("The server will run multiple games with the same connections.")
    print("Press Ctrl+C to stop the test.")
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.stop_server()
        print("Test completed.")

if __name__ == "__main__":
    test_continuous_games() 