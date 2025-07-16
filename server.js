const fs = require('fs');
const spdy = require('spdy'); // или const https = require('https');
const express = require('express');
const socketIo = require('socket.io');

const app = express();
app.use(express.static('public'));

// HTTPS-конфиг
const options = {
  key: fs.readFileSync('./ssl/meet.zindaki-edu.ru.key'),
  cert: fs.readFileSync('./ssl/meet.zindaki-edu.ru.crt')
};

// Запуск сервера
const server = spdy.createServer(options, app); // или https.createServer(options, app)
const io = socketIo(server);

// WebSocket-логика (из вашего оригинального server.js)
io.on('connection', (socket) => {
  socket.on('join', (roomId) => {
    socket.join(roomId);
    socket.to(roomId).emit('user-connected', socket.id);
    
    socket.on('disconnect', () => {
      socket.to(roomId).emit('user-disconnected', socket.id);
    });
    
    socket.on('signal', (data) => {
      socket.to(data.to).emit('signal', {
        from: socket.id,
        signal: data.signal
      });
    });
  });
});

// Запуск на порту 443 (HTTPS) или 3000 (если нет прав на 443)
const PORT = process.env.PORT || 443;
server.listen(PORT, '0.0.0.0', () => {
  console.log(`Server running on port ${PORT} (HTTPS)`);
});