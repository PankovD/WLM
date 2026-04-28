"""Single source of truth for the application base directory."""
import sys
import os

if getattr(sys, 'frozen', False):
    # Running as compiled .exe (PyInstaller onedir)
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running as .py script — one level above this file (core/)
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
