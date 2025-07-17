from flask import Flask, render_template, request, jsonify
import uuid
from flask_cors import CORS
import jwt
from functools import wraps
import datetime

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["https://zindaki-edu.ru", "https://conf.zindaki-edu.ru"]}})

# Конфигурация
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Замените на реальный секретный ключ
app.config['JWT_ALGORITHM'] = 'HS256'
app.config['JWT_EXPIRATION_DELTA'] = datetime.timedelta(hours=2)

# Хранилище для пар ID пользователей и их PeerJS ID
peer_mapping = {}
# Хранилище комнат и участников
rooms = {}

# Декоратор для проверки JWT токена
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split()[1]
            
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
            
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])
            current_user = data['username']
        except:
            return jsonify({'error': 'Token is invalid'}), 401
            
        return f(current_user, *args, **kwargs)
        
    return decorated

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate_token', methods=['POST'])
def generate_token():
    auth = request.json
    
    if not auth or not auth.get('username') or not auth.get('role'):
        return jsonify({'error': 'Invalid credentials'}), 401
        
    # В реальном приложении здесь должна быть проверка учетных данных
    token = jwt.encode({
        'username': auth['username'],
        'role': auth['role'],
        'exp': datetime.datetime.utcnow() + app.config['JWT_EXPIRATION_DELTA']
    }, app.config['SECRET_KEY'], algorithm=app.config['JWT_ALGORITHM'])
    
    return jsonify({'token': token})

@app.route('/api/get_peer_id', methods=['POST'])
@token_required
def get_peer_id(current_user):
    room_name = request.json.get('room_name')
    
    if not room_name:
        return jsonify({'error': 'Room name is required'}), 400
        
    # Генерируем уникальный PeerJS ID
    peer_id = str(uuid.uuid4())
    peer_mapping[current_user] = peer_id
    
    # Добавляем пользователя в комнату
    if room_name not in rooms:
        rooms[room_name] = {
            'participants': {},
            'created_at': datetime.datetime.utcnow().isoformat()
        }
        
    rooms[room_name]['participants'][current_user] = {
        'peer_id': peer_id,
        'joined_at': datetime.datetime.utcnow().isoformat()
    }
    
    return jsonify({
        'success': True,
        'peer_id': peer_id,
        'room': room_name
    })

@app.route('/api/get_peer_ids', methods=['POST'])
@token_required
def get_peer_ids(current_user):
    room_name = request.json.get('room_name')
    
    if not room_name:
        return jsonify({'error': 'Room name is required'}), 400
        
    if room_name not in rooms:
        return jsonify({'error': 'Room not found'}), 404
        
    # Проверяем, есть ли пользователь в комнате
    if current_user not in rooms[room_name]['participants']:
        return jsonify({'error': 'User not in room'}), 403
        
    # Для простоты возвращаем всех, кроме текущего пользователя
    other_peers = {
        user: data['peer_id'] 
        for user, data in rooms[room_name]['participants'].items() 
        if user != current_user
    }
    
    return jsonify({
        'success': True,
        'peers': other_peers,
        'room': room_name,
        'participant_count': len(rooms[room_name]['participants'])
    })

@app.route('/api/leave_room', methods=['POST'])
@token_required
def leave_room(current_user):
    room_name = request.json.get('room_name')
    
    if not room_name:
        return jsonify({'error': 'Room name is required'}), 400
        
    if room_name in rooms and current_user in rooms[room_name]['participants']:
        del rooms[room_name]['participants'][current_user]
        
        # Если комната пуста, удаляем ее
        if not rooms[room_name]['participants']:
            del rooms[room_name]
            
    if current_user in peer_mapping:
        del peer_mapping[current_user]
        
    return jsonify({'success': True})

@app.route('/api/room_status', methods=['POST'])
@token_required
def room_status(current_user):
    room_name = request.json.get('room_name')
    
    if not room_name:
        return jsonify({'error': 'Room name is required'}), 400
        
    if room_name not in rooms:
        return jsonify({'error': 'Room not found'}), 404
        
    return jsonify({
        'success': True,
        'room': room_name,
        'participants': list(rooms[room_name]['participants'].keys()),
        'participant_count': len(rooms[room_name]['participants']),
        'created_at': rooms[room_name]['created_at']
    })

@app.route('/api/end_room', methods=['POST'])
@token_required
def end_room(current_user):
    room_name = request.json.get('room_name')
    
    if not room_name:
        return jsonify({'error': 'Room name is required'}), 400
        
    if room_name in rooms:
        # В реальном приложении здесь должна быть проверка прав
        del rooms[room_name]
        
    return jsonify({'success': True})

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)