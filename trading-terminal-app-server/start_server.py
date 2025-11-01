#!/usr/bin/env python3
"""
Unified server startup script
This script can start the application in either development or production mode
with automatic dependency management for production deployment
"""
import eventlet
eventlet.monkey_patch()

import os
import sys
import argparse
import subprocess

def start_development():
    """Start the Flask development server"""
    os.environ['FLASK_ENV'] = 'development'

    from main import flask_app
    from shared.utils.websocket_utils import socketio
    
    print("🚀 Starting Flask development server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("⚠️  This is a development server. For production, use: python start_server.py --mode production")
    print("Starting Flask app with socketio initialized")
    socketio.run(
        flask_app,
        host='0.0.0.0',
        port=8000,
        debug=True
    )

def start_production():
    """Start the production server using Gunicorn with automatic dependency management"""
    os.environ['FLASK_ENV'] = 'production'
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to gunicorn config
    gunicorn_config = os.path.join(script_dir, 'shared', 'config', 'gunicorn.conf.py')
    
    # Check if gunicorn is installed and install if needed
    try:
        import gunicorn
        print("✅ Gunicorn found")
    except ImportError:
        print("📦 Gunicorn not found. Installing automatically...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'gunicorn'])
            print("✅ Gunicorn installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install Gunicorn: {e}")
            print("Please install it manually with: pip install gunicorn")
            sys.exit(1)
    
    # Start the server with Gunicorn
    cmd = [
        sys.executable, '-m', 'gunicorn',
        '-c', gunicorn_config,
        'main:application'
    ]
    
    print("🏭 Starting production server with Gunicorn...")
    print(f"🔧 Command: {' '.join(cmd)}")
    print(f"📁 Working directory: {script_dir}")
    print(f"⚙️  Config file: {gunicorn_config}")
    
    try:
        subprocess.run(cmd, cwd=script_dir)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Start the trading terminal server in development or production mode',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_server.py                    # Start in development mode
  python start_server.py --mode development # Start in development mode
  python start_server.py --mode production  # Start in production mode with Gunicorn
        """
    )
    parser.add_argument(
        '--mode', 
        choices=['development', 'production'], 
        default='development',
        help='Server mode (default: development)'
    )
    
    args = parser.parse_args()
    
    print(f"🎯 Starting server in {args.mode} mode...")
    
    if args.mode == 'development':
        start_development()
    else:
        start_production()

if __name__ == '__main__':
    main() 