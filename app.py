from flask import Flask, render_template, request, jsonify
import uuid
from collections import defaultdict

app = Flask(__name__)

# Хранилище для комнат: {room_name: {user_id: peer_id}}
rooms = defaultdict(dict)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get_peer_id', methods=['POST'])
def get_peer_id():
    user_id = request.json.get('user_id')
    room_name = request.json.get('room_name')
    
    if not user_id or not room_name:
        return jsonify({'error': 'User ID and room name are required'}), 400
    
    # Генерируем уникальный PeerJS ID
    peer_id = str(uuid.uuid4())
    rooms[room_name][user_id] = peer_id
    
    return jsonify({
        'success': True,
        'peer_id': peer_id
    })

@app.route('/api/get_peer_ids', methods=['POST'])
def get_peer_ids():
    room_name = request.json.get('room_name')
    current_user = request.json.get('current_user')
    action = request.json.get('action')
    
    if not room_name or not current_user:
        return jsonify({'error': 'Room name and current user are required'}), 400
    
    # Обработка выхода пользователя
    if action == 'leave':
        if room_name in rooms and current_user in rooms[room_name]:
            del rooms[room_name][current_user]
            # Если комната пуста, удаляем ее
            if not rooms[room_name]:
                del rooms[room_name]
        return jsonify({'success': True})
    
    # Получаем участников комнаты, кроме текущего пользователя
    if room_name not in rooms:
        return jsonify({'success': True, 'peers': {}})
    
    other_peers = {
        user: peer_id 
        for user, peer_id in rooms[room_name].items() 
        if user != current_user
    }
    
    return jsonify({
        'success': True,
        'peers': other_peers
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)