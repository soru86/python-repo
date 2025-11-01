from flask_socketio import SocketIO
from app import flask_app

socketio = SocketIO(flask_app, cors_allowed_origins="*", async_mode='eventlet')

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')
