const socket = io();
const localVideo = document.getElementById('localVideo');
const remoteVideos = document.getElementById('remoteVideos');
const roomIdInput = document.getElementById('roomId');
const joinBtn = document.getElementById('joinBtn');

let localStream;
let peers = {};

// Get user media
navigator.mediaDevices.getUserMedia({ video: true, audio: true })
  .then(stream => {
    localVideo.srcObject = stream;
    localStream = stream;
  });

// Join room
joinBtn.addEventListener('click', () => {
  const roomId = roomIdInput.value || 'default';
  socket.emit('join', roomId);
});

// WebRTC setup
socket.on('user-connected', userId => {
  if (userId === socket.id) return;
  
  const peer = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
  });
  
  localStream.getTracks().forEach(track => {
    peer.addTrack(track, localStream);
  });
  
  peer.onicecandidate = e => {
    if (e.candidate) {
      socket.emit('signal', {
        to: userId,
        signal: {
          candidate: e.candidate,
          from: socket.id
        }
      });
    }
  };
  
  peer.ontrack = e => {
    const remoteVideo = document.createElement('video');
    remoteVideo.autoplay = true;
    remoteVideo.srcObject = e.streams[0];
    remoteVideos.appendChild(remoteVideo);
  };
  
  peers[userId] = peer;
  
  peer.createOffer()
    .then(offer => peer.setLocalDescription(offer))
    .then(() => {
      socket.emit('signal', {
        to: userId,
        signal: {
          sdp: peer.localDescription,
          from: socket.id
        }
      });
    });
});

socket.on('signal', data => {
  const peer = peers[data.from] || new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
  });
  
  if (data.signal.sdp) {
    peer.setRemoteDescription(new RTCSessionDescription(data.signal.sdp))
      .then(() => {
        if (data.signal.sdp.type === 'offer') {
          return peer.createAnswer()
            .then(answer => peer.setLocalDescription(answer))
            .then(() => {
              socket.emit('signal', {
                to: data.from,
                signal: {
                  sdp: peer.localDescription,
                  from: socket.id
                }
              });
            });
        }
      });
  } else if (data.signal.candidate) {
    peer.addIceCandidate(new RTCIceCandidate(data.signal.candidate));
  }
  
  peers[data.from] = peer;
});

socket.on('user-disconnected', userId => {
  if (peers[userId]) {
    peers[userId].close();
    delete peers[userId];
  }
});
