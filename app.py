# app.py
from flask import Flask, render_template, request, jsonify, Response
import json
import os
import time
import base64
from collections import defaultdict, deque
from threading import Lock
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Конфигурация
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Глобальные переменные для видеоконференций
participants = defaultdict(set)
frame_buffers = defaultdict(lambda: defaultdict(deque))
frame_timestamps = defaultdict(dict)
audio_buffers = defaultdict(lambda: defaultdict(deque))
audio_timestamps = defaultdict(dict)
data_lock = Lock()

# Ограничения
MAX_FRAMES_PER_USER = 3
MAX_FRAME_AGE = 1.0
MAX_AUDIO_PER_USER = 10
MAX_AUDIO_AGE = 0.5

def cleanup_old_data():
    current_time = time.time()
    
    with data_lock:
        # Очистка старых кадров
        for room in list(frame_buffers.keys()):
            for user in list(frame_buffers[room].keys()):
                while (frame_buffers[room][user] and 
                       current_time - frame_timestamps.get(room, {}).get(user, 0) > MAX_FRAME_AGE):
                    frame_buffers[room][user].popleft()
                
                if not frame_buffers[room][user] and user not in participants.get(room, set()):
                    if user in frame_buffers[room]:
                        del frame_buffers[room][user]
                    if room in frame_timestamps and user in frame_timestamps[room]:
                        del frame_timestamps[room][user]
            
            if not frame_buffers[room] and room not in participants:
                del frame_buffers[room]
                if room in frame_timestamps:
                    del frame_timestamps[room]
        
        # Очистка старых аудио данных
        for room in list(audio_buffers.keys()):
            for user in list(audio_buffers[room].keys()):
                while (audio_buffers[room][user] and 
                       current_time - audio_timestamps.get(room, {}).get(user, 0) > MAX_AUDIO_AGE):
                    audio_buffers[room][user].popleft()
                
                if not audio_buffers[room][user] and user not in participants.get(room, set()):
                    if user in audio_buffers[room]:
                        del audio_buffers[room][user]
                    if room in audio_timestamps and user in audio_timestamps[room]:
                        del audio_timestamps[room][user]
            
            if not audio_buffers[room] and room not in participants:
                del audio_buffers[room]
                if room in audio_timestamps:
                    del audio_timestamps[room]
        
        # Очистка участников без активности
        for room in list(participants.keys()):
            if not participants[room]:
                if room in frame_buffers:
                    del frame_buffers[room]
                if room in frame_timestamps:
                    del frame_timestamps[room]
                if room in audio_buffers:
                    del audio_buffers[room]
                if room in audio_timestamps:
                    del audio_timestamps[room]
                del participants[room]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/conference/<room_name>/join', methods=['POST'])
def join_conference(room_name):
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    with data_lock:
        participants[room_name].add(user_id)
    
    return jsonify({
        'success': True,
        'room_name': room_name,
        'participants': list(participants[room_name])
    })

@app.route('/api/conference/<room_name>/leave', methods=['POST'])
def leave_conference(room_name):
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    with data_lock:
        if room_name in participants and user_id in participants[room_name]:
            participants[room_name].remove(user_id)
            
            if room_name in frame_buffers and user_id in frame_buffers[room_name]:
                del frame_buffers[room_name][user_id]
            if room_name in frame_timestamps and user_id in frame_timestamps[room_name]:
                del frame_timestamps[room_name][user_id]
            if room_name in audio_buffers and user_id in audio_buffers[room_name]:
                del audio_buffers[room_name][user_id]
            if room_name in audio_timestamps and user_id in audio_timestamps[room_name]:
                del audio_timestamps[room_name][user_id]
            
            if not participants[room_name]:
                if room_name in frame_buffers:
                    del frame_buffers[room_name]
                if room_name in frame_timestamps:
                    del frame_timestamps[room_name]
                if room_name in audio_buffers:
                    del audio_buffers[room_name]
                if room_name in audio_timestamps:
                    del audio_timestamps[room_name]
    
    return jsonify({'success': True})

@app.route('/api/conference/<room_name>/video', methods=['POST'])
def receive_video_frame(room_name):
    data = request.json
    user_id = data.get('user_id')
    frame_data = data.get('frame')
    
    if not user_id or not frame_data:
        return jsonify({'error': 'User ID and frame data are required'}), 400
    
    cleanup_old_data()
    
    with data_lock:
        if len(frame_buffers[room_name][user_id]) >= MAX_FRAMES_PER_USER:
            frame_buffers[room_name][user_id].popleft()
        
        frame_buffers[room_name][user_id].append(frame_data)
        frame_timestamps[room_name][user_id] = time.time()
    
    return jsonify({'success': True})

@app.route('/video_feed/<room_name>/<user_id>')
def video_feed(room_name, user_id):
    def generate():
        last_frame_time = 0
        frame_interval = 1.0 / 15  # 15 FPS
        
        while True:
            try:
                current_time = time.time()
                
                with data_lock:
                    if (room_name in frame_buffers and 
                        user_id in frame_buffers[room_name] and 
                        frame_buffers[room_name][user_id]):
                        
                        frame_data = frame_buffers[room_name][user_id][-1]
                        
                        elapsed = current_time - last_frame_time
                        if elapsed < frame_interval:
                            time.sleep(frame_interval - elapsed)
                        
                        frame = base64.b64decode(frame_data.split(',')[1])
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                        
                        last_frame_time = time.time()
                    else:
                        time.sleep(0.1)
            except Exception as e:
                print(f"Error in video feed generation: {e}")
                time.sleep(0.1)
    
    return Response(generate(),
                  mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/conference/<room_name>/audio', methods=['POST'])
def receive_audio_data(room_name):
    data = request.json
    user_id = data.get('user_id')
    audio_data = data.get('audio')
    
    if not user_id or not audio_data:
        return jsonify({'error': 'User ID and audio data are required'}), 400
    
    cleanup_old_data()
    
    with data_lock:
        if len(audio_buffers[room_name][user_id]) >= MAX_AUDIO_PER_USER:
            audio_buffers[room_name][user_id].popleft()
        
        audio_buffers[room_name][user_id].append(audio_data)
        audio_timestamps[room_name][user_id] = time.time()
    
    return jsonify({'success': True})

@app.route('/api/conference/<room_name>/audio/<user_id>', methods=['GET'])
def get_audio_data(room_name, user_id):
    try:
        cleanup_old_data()
        
        with data_lock:
            if (room_name in audio_buffers and 
                user_id in audio_buffers[room_name] and 
                audio_buffers[room_name][user_id]):
                
                audio_data = audio_buffers[room_name][user_id][-1]
                
                return jsonify({
                    'success': True,
                    'audio': audio_data,
                    'timestamp': audio_timestamps[room_name][user_id]
                })
        
        return jsonify({'success': False, 'error': 'No audio data available'})
    except Exception as e:
        print(f"Error getting audio data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
