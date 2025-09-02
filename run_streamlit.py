#!/usr/bin/env python3
"""
Streamlit UI Runner for AI Medical Scheduling Agent
Run this script to launch the web interface
"""

import subprocess
import sys
import os

def main():
    """Launch the Streamlit UI"""
    print("🏥 Starting AI Medical Scheduling Agent UI...")
    print("📱 Opening web interface at http://localhost:8501")
    print("🔄 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Run streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "app/streamlit_ui.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
