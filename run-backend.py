#!/usr/bin/env python3
import os
import sys
import subprocess

def main():
    # Change to backend directory
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    os.chdir(backend_dir)
    
    # Install Python dependencies if requirements.txt exists
    if os.path.exists('requirements.txt'):
        print("Installing Python dependencies...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
    
    # Run the FastAPI server
    print("Starting FastAPI server...")
    subprocess.run([sys.executable, '-m', 'uvicorn', 'main:app', '--reload', '--host', '0.0.0.0', '--port', '8000'], check=True)

if __name__ == '__main__':
    main()