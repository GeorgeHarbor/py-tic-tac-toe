var socket = io.connect('http://' + document.domain + ':' + location.port);
var room = "{{ room }}";

socket.on('connect', function() {
    socket.emit('join', {'room': room});
});

socket.on('move', function(data) {
    document.querySelectorAll('.cell')[data.index].innerHTML = data.player;
});

socket.on('message', function(data) {
    console.log(data.msg);
});

socket.on('notification', function(data) {
    document.getElementById('notification').innerHTML = data.msg;
});

function makeMove(index) {
    var cells = document.querySelectorAll('.cell');
    if (cells[index].innerHTML === '') {
        socket.emit('move', {'index': index, 'player': 'X', 'room': room});
    }
}

function resetGame() {
    var cells = document.querySelectorAll('.cell');
    cells.forEach(cell => cell.innerHTML = '');
    socket.emit('reset', {'room': room});
}
