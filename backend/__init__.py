# Backend module initialization
# backend/__init__.py
import os
import sys

__version__ = "3.1.6"
# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))