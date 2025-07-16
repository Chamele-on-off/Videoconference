const express = require('express');
const app = express();
const http = require('http').createServer(app);
const io = require('socket.io')(http);
const port = process.env.PORT || 3000;

app.use(express.static('public'));

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

http.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
