from flask import Flask, render_template, request, jsonify
import uuid
from collections import defaultdict
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Хранилище для комнат: {room_name: {user_id: peer_id}}
rooms = defaultdict(dict)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get_peer_id', methods=['POST'])
def get_peer_id():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        user_id = data.get('user_id')
        room_name = data.get('room_name')
        peer_id = data.get('peer_id')
        
        if not user_id or not room_name:
            return jsonify({'error': 'User ID and room name are required'}), 400
        
        # Если peer_id не предоставлен, генерируем его
        if not peer_id:
            peer_id = f"peer-{str(uuid.uuid4())[:8]}"
        
        # Сохраняем в комнате
        rooms[room_name][user_id] = peer_id
        print(f"User {user_id} joined room {room_name} with peer ID {peer_id}")
        print(f"Current room state: {dict(rooms[room_name])}")
        
        return jsonify({
            'success': True,
            'peer_id': peer_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_peer_ids', methods=['POST'])
def get_peer_ids():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        room_name = data.get('room_name')
        current_user = data.get('current_user')
        action = data.get('action')
        
        if not room_name or not current_user:
            return jsonify({'error': 'Room name and current user are required'}), 400
        
        # Обработка выхода пользователя
        if action == 'leave':
            if room_name in rooms and current_user in rooms[room_name]:
                del rooms[room_name][current_user]
                print(f"User {current_user} left room {room_name}")
                # Если комната пуста, удаляем ее
                if not rooms[room_name]:
                    del rooms[room_name]
                    print(f"Room {room_name} deleted (empty)")
            return jsonify({'success': True})
        
        # Получаем участников комнаты, кроме текущего пользователя
        if room_name not in rooms:
            print(f"Room {room_name} not found")
            return jsonify({'success': True, 'peers': {}})
        
        other_peers = {
            user: peer_id 
            for user, peer_id in rooms[room_name].items() 
            if user != current_user
        }
        
        print(f"Returning peers for room {room_name}: {other_peers}")
        
        return jsonify({
            'success': True,
            'peers': other_peers
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'ok', 'rooms_count': len(rooms)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)