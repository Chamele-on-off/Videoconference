from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
from collections import defaultdict
from flask_cors import CORS
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Хранилище для комнат: {room_name: {user_id: user_data}}
rooms = defaultdict(dict)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    emit('connected', {'message': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')
    # Удаляем пользователя из всех комнат при отключении
    for room_name, users in list(rooms.items()):
        for user_id, user_data in list(users.items()):
            if user_data.get('socket_id') == request.sid:
                leave_room_handler({'room_name': room_name, 'user_id': user_id})
                break

@socketio.on('join_room')
def join_room_handler(data):
    try:
        room_name = data.get('room_name')
        user_id = data.get('user_id')
        user_name = data.get('user_name')
        
        if not all([room_name, user_id, user_name]):
            emit('error', {'message': 'Missing required fields'})
            return
        
        # Сохраняем информацию о пользователе
        rooms[room_name][user_id] = {
            'socket_id': request.sid,
            'user_name': user_name,
            'user_id': user_id
        }
        
        join_room(room_name)
        print(f'User {user_name} ({user_id}) joined room {room_name}')
        
        # Отправляем текущему пользователю список всех участников комнаты
        participants = {
            uid: {'user_name': data['user_name'], 'user_id': uid}
            for uid, data in rooms[room_name].items()
            if uid != user_id
        }
        
        emit('room_joined', {
            'room_name': room_name,
            'user_id': user_id,
            'participants': participants
        }, room=request.sid)
        
        # Уведомляем других участников о новом пользователе
        emit('user_joined', {
            'user_id': user_id,
            'user_name': user_name,
            'socket_id': request.sid
        }, room=room_name, include_self=False)
        
    except Exception as e:
        print(f'Error in join_room: {e}')
        emit('error', {'message': str(e)})

@socketio.on('leave_room')
def leave_room_handler(data):
    try:
        room_name = data.get('room_name')
        user_id = data.get('user_id')
        
        if room_name in rooms and user_id in rooms[room_name]:
            # Удаляем пользователя из комнаты
            del rooms[room_name][user_id]
            leave_room(room_name)
            
            print(f'User {user_id} left room {room_name}')
            
            # Если комната пуста, удаляем ее
            if not rooms[room_name]:
                del rooms[room_name]
                print(f'Room {room_name} deleted (empty)')
            
            # Уведомляем других участников
            emit('user_left', {
                'user_id': user_id
            }, room=room_name)
            
    except Exception as e:
        print(f'Error in leave_room: {e}')

@socketio.on('webrtc_offer')
def handle_webrtc_offer(data):
    try:
        offer = data.get('offer')
        target_user_id = data.get('target_user_id')
        caller_user_id = data.get('caller_user_id')
        room_name = data.get('room_name')
        
        if not all([offer, target_user_id, caller_user_id, room_name]):
            emit('error', {'message': 'Missing required fields for offer'})
            return
        
        # Находим socket_id целевого пользователя
        target_user = rooms[room_name].get(target_user_id)
        if not target_user:
            emit('error', {'message': f'Target user {target_user_id} not found'})
            return
        
        # Пересылаем offer целевому пользователю
        emit('webrtc_offer', {
            'offer': offer,
            'caller_user_id': caller_user_id,
            'target_user_id': target_user_id
        }, room=target_user['socket_id'])
        
        print(f'Forwarded WebRTC offer from {caller_user_id} to {target_user_id}')
        
    except Exception as e:
        print(f'Error handling WebRTC offer: {e}')
        emit('error', {'message': str(e)})

@socketio.on('webrtc_answer')
def handle_webrtc_answer(data):
    try:
        answer = data.get('answer')
        target_user_id = data.get('target_user_id')
        answerer_user_id = data.get('answerer_user_id')
        room_name = data.get('room_name')
        
        if not all([answer, target_user_id, answerer_user_id, room_name]):
            emit('error', {'message': 'Missing required fields for answer'})
            return
        
        # Находим socket_id целевого пользователя
        target_user = rooms[room_name].get(target_user_id)
        if not target_user:
            emit('error', {'message': f'Target user {target_user_id} not found'})
            return
        
        # Пересылаем answer целевому пользователю
        emit('webrtc_answer', {
            'answer': answer,
            'answerer_user_id': answerer_user_id,
            'target_user_id': target_user_id
        }, room=target_user['socket_id'])
        
        print(f'Forwarded WebRTC answer from {answerer_user_id} to {target_user_id}')
        
    except Exception as e:
        print(f'Error handling WebRTC answer: {e}')
        emit('error', {'message': str(e)})

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    try:
        candidate = data.get('candidate')
        target_user_id = data.get('target_user_id')
        sender_user_id = data.get('sender_user_id')
        room_name = data.get('room_name')
        
        if not all([candidate, target_user_id, sender_user_id, room_name]):
            emit('error', {'message': 'Missing required fields for ICE candidate'})
            return
        
        # Находим socket_id целевого пользователя
        target_user = rooms[room_name].get(target_user_id)
        if not target_user:
            emit('error', {'message': f'Target user {target_user_id} not found'})
            return
        
        # Пересылаем ICE candidate целевому пользователю
        emit('ice_candidate', {
            'candidate': candidate,
            'sender_user_id': sender_user_id,
            'target_user_id': target_user_id
        }, room=target_user['socket_id'])
        
        print(f'Forwarded ICE candidate from {sender_user_id} to {target_user_id}')
        
    except Exception as e:
        print(f'Error handling ICE candidate: {e}')
        emit('error', {'message': str(e)})

@socketio.on('screen_share_status')
def handle_screen_share_status(data):
    try:
        is_sharing = data.get('is_sharing')
        user_id = data.get('user_id')
        room_name = data.get('room_name')
        
        if not all([is_sharing is not None, user_id, room_name]):
            emit('error', {'message': 'Missing required fields for screen share status'})
            return
        
        # Обновляем статус демонстрации экрана
        if room_name in rooms and user_id in rooms[room_name]:
            rooms[room_name][user_id]['is_screen_sharing'] = is_sharing
            
            # Уведомляем других участников
            emit('screen_share_status', {
                'user_id': user_id,
                'is_sharing': is_sharing
            }, room=room_name, include_self=False)
            
            print(f'User {user_id} screen share status: {is_sharing}')
            
    except Exception as e:
        print(f'Error handling screen share status: {e}')
        emit('error', {'message': str(e)})

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'ok', 
        'rooms_count': len(rooms),
        'total_users': sum(len(users) for users in rooms.values())
    })

if __name__ == '__main__':
    print('Starting server on http://localhost:5000')
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)