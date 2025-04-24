# app.py
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import base64
import cv2
import mediapipe as mp
import numpy as np
from scipy.spatial import distance as dist
import os
import uuid
import time
from threading import Lock
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image
import io


app = Flask(__name__)
app.config['SECRET_KEY'] = 'proctoringsystemsecretkey'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active users and their room IDs
active_users = {}
thread = None
thread_lock = Lock()

# Admin credentials (in a real app, you would use a database)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = generate_password_hash('admin123')


@app.route('/')
def index():
    return render_template('index.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_type = request.form.get('user_type')

        if user_type == 'admin':
            if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD, password):
                session['username'] = username
                session['user_type'] = 'admin'
                return redirect(url_for('admin_dashboard'))
            else:
                return render_template('login.html', error='Invalid admin credentials')
        else:
            # For regular users, just use the username (no password required for simplicity)
            session['username'] = username
            session['user_type'] = 'user'
            return redirect(url_for('user_dashboard'))

    return render_template('login.html')


@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('username') or session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html', username=session['username'])


@app.route('/user_dashboard')
def user_dashboard():
    if not session.get('username') or session.get('user_type') != 'user':
        return redirect(url_for('login'))
    return render_template('user_dashboard.html', username=session['username'])


@app.route('/logout')
def logout():
    username = session.get('username')
    if username in active_users:
        del active_users[username]
    session.clear()
    return redirect(url_for('index'))


@socketio.on('connect')
def handle_connect():
    if 'username' not in session:
        return False

    username = session['username']
    user_type = session.get('user_type')

    if user_type == 'user':
        # Generate a unique room ID for this user
        if username not in active_users:
            room_id = str(uuid.uuid4())
            active_users[username] = room_id
            join_room(room_id)
            # Notify admin that a new user has connected
            socketio.emit('user_connected', {
                        'username': username, 'room_id': room_id } , room='admin_room')

    elif user_type == 'admin':
        # Admin joins a special admin room
        join_room('admin_room')
        # Send the admin the list of all active users
        for user, room in active_users.items():
            emit('user_connected', {'username': user, 'room_id': room})


@socketio.on('disconnect')
def handle_disconnect():
    username = session.get('username')
    user_type = session.get('user_type')

    if username and user_type == 'user' and username in active_users:
        room_id = active_users[username]
        del active_users[username]
        # Notify admin that a user has disconnected
        socketio.emit('user_disconnected', {
                    'username': username}, room='admin_room')

    elif user_type == 'admin':
        leave_room('admin_room')


@socketio.on('video_frame')
def handle_video_frame(data):
    if 'username' not in session or session.get('user_type') != 'user':
        return

    username = session['username']
    if username in active_users:
        room_id = active_users[username]
        # Forward the video frame to the admin with the username
        data['username'] = username
        socketio.emit('video_frame', data, room='admin_room')


@socketio.on('join_monitoring')
def handle_join_monitoring(data):
    if 'username' not in session or session.get('user_type') != 'admin':
        return

    user = data.get('username')
    if user in active_users:
        room_id = active_users[user]
        # Tell the user to start sending their video
        socketio.emit('start_video_stream', room=room_id)


@socketio.on('stop_monitoring')
def handle_stop_monitoring(data):
    if 'username' not in session or session.get('user_type') != 'admin':
        return

    user = data.get('username')
    if user in active_users:
        room_id = active_users[user]
        # Tell the user to stop sending their video
        socketio.emit('stop_video_stream', room=room_id)

# Route for checking suspicious behavior (for admin)


@socketio.on('report_suspicious')
def handle_report_suspicious(data):
    if 'username' not in session or session.get('user_type') != 'admin':
        return

    user = data.get('username')
    reason = data.get('reason')

    if user in active_users:
        room_id = active_users[user]
        # Notify the user they're being flagged
        socketio.emit('suspicious_behavior_detected', {
            'reason': reason}, room=room_id)
        # Log this event (in a real app, you would save to database)
        print(f"SUSPICIOUS BEHAVIOR: User {user} flagged for {reason}")


# Mediapipe setup
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    min_detection_confidence=0.5, min_tracking_confidence=0.5
)
THRESHOLD = 20  # Pixels for head movement


def detect_head_movement(face_landmarks, frame_shape):
    nose_x = face_landmarks[4][0]
    chin_x = face_landmarks[152][0]

    # Calculate horizontal difference
    horizontal_diff = abs(nose_x - chin_x)

    if horizontal_diff > THRESHOLD:
        return True
    return False


def process_image(image_data):

    if ',' in image_data:
        image_data = image_data.split(',')[1]

    # Decode base64 image
    image_bytes = base64.b64decode(image_data)
    image = Image.open(io.BytesIO(image_bytes))

    # Convert PIL Image to OpenCV format
    frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    # Process with mediapipe
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    alerts = []

    if results.multi_face_landmarks:
        # Multiple people detection
        if len(results.multi_face_landmarks) > 1:
            alerts.append("Multiple people detected")

        for face_landmarks in results.multi_face_landmarks:
            # Extract landmarks
            face_landmarks_list = []
            for landmark in face_landmarks.landmark:
                x = int(landmark.x * frame.shape[1])
                y = int(landmark.y * frame.shape[0])
                face_landmarks_list.append((x, y))

            if detect_head_movement(face_landmarks_list, frame.shape):
                alerts.append("Head movement detected")

    return alerts

# Modify your handle_video_frame function


@socketio.on('video_frame')
def handle_video_frame(data):
    if 'username' not in session or session.get('user_type') != 'user':
        return

    username = session['username']
    if username in active_users:
        room_id = active_users[username]

        # Process image for suspicious behavior
        if 'image' in data:
            alerts = process_image(data['image'])
            if alerts:
                data['alerts'] = ', '.join(alerts)
                # Send alerts back to the user
                socketio.emit('video_frame_response', {
                              'alerts': data['alerts']}, room=room_id)

        # Forward the video frame to the admin with the username
        data['username'] = username
        socketio.emit('video_frame', data, room='admin_room')


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0')
