#!/usr/bin/env python
"""
Wrapper script to run the main application from the root directory.
This allows running 'python main.py' from the project root.
"""
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Import and run the main module
from src import main as main_module

if __name__ == "__main__":
    # Execute the main script
    main_module.main()
