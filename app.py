from flask import Flask, render_template, request, jsonify
import uuid

app = Flask(__name__)

# Хранилище для пар ID пользователей и их PeerJS ID
peer_mapping = {}

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
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    # Генерируем уникальный PeerJS ID
    peer_id = str(uuid.uuid4())
    peer_mapping[user_id] = peer_id
    
    return jsonify({
        'success': True,
        'peer_id': peer_id
    })

@app.route('/api/get_peer_ids', methods=['POST'])
def get_peer_ids():
    room_name = request.json.get('room_name')
    current_user = request.json.get('current_user')
    
    if not room_name or not current_user:
        return jsonify({'error': 'Room name and current user are required'}), 400
    
    # В реальном приложении здесь должна быть логика комнат
    # Для простоты возвращаем всех, кроме текущего пользователя
    other_peers = {
        user: peer_id 
        for user, peer_id in peer_mapping.items() 
        if user != current_user
    }
    
    return jsonify({
        'success': True,
        'peers': other_peers
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)