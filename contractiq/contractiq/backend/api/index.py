import sys
import os

# Add the parent directory (backend) to the Python path.
# This is required because Vercel runs this script from the 'api/' folder,
# but main.py and core.py live in the folder above it.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the FastAPI app instance from your main.py file
from main import app

# Vercel's Python serverless runtime expects the ASGI app to be exposed 
# as either 'app' or 'handler'. We provide both to be completely safe.
handler = app
