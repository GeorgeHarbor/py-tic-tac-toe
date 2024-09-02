from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, join_room, leave_room, emit
import sqlite3
import random

app = Flask(__name__)
app.secret_key = 'mojkljuc'
socketio = SocketIO(app)

def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute(
            '''CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                wins INTEGER DEFAULT 0 
            )'''
        )
        conn.commit()

@app.before_request
def before_request():
    init_db()

@app.route('/')
def home():
    if 'username' in session:
        users = []
        with get_db_connection() as conn:
            users = conn.execute("SELECT * FROM user ORDER BY wins DESC").fetchall()
        return render_template('home.html', username=session['username'], users=users)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        with get_db_connection() as conn:
            try:
                conn.execute("INSERT INTO user (username, password) VALUES (?, ?)", (username, hashed_password))
                conn.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('Username already exists. Try a different one.', 'danger')
                return render_template('register.html')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with get_db_connection() as conn:
            user = conn.execute("SELECT * FROM user WHERE username = ?", (username,)).fetchone()
            if user and check_password_hash(user['password'], password):
                session['username'] = user['username']
                return redirect(url_for('home'))
            else:
                flash('Invalid username or password.', 'danger')
                return render_template('login.html')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)  
    session.pop('room', None)  
    session.pop('player_marker', None)  
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/create_room')
def create_room():
    if 'username' not in session:
        flash('You must be logged in to create a room.', 'danger')
        return redirect(url_for('login'))
    
    room_number = str(random.randint(1000, 9999))
    session['room'] = room_number
    session['player_marker'] = 'X'
    
    return redirect(url_for('game', room=room_number))

@app.route('/join_room', methods=['POST'])
def player_join_room():
    if 'username' not in session:
        flash('You must be logged in to join a room.', 'danger')
        return redirect(url_for('login'))
    
    room_number = request.form.get('room_number')
    session['room'] = room_number
    session['player_marker'] = 'O'
    
    return redirect(url_for('game', room=room_number))

@app.route('/game')
def game():
    if 'username' not in session or 'room' not in session or 'player_marker' not in session:
        flash('You must be logged in and in a room to play the game.', 'danger')
        return redirect(url_for('login'))
    
    room = session['room']
    return render_template('game.html', room=room, player=session['username'], player_marker=session['player_marker'])

@socketio.on('join')
def on_join(data):
    username = session.get('username')
    room = data['room']
    join_room(room)
    emit('start_game', {'currentPlayer': 'X', 'username': username}, to=room)  

@socketio.on('move')
def on_move(data):
    room = session.get('room')
    current_player = session.get('player_marker')
    next_player = 'O' if current_player == 'X' else 'X'
    
    emit('move', {'index': data['index'], 'player_marker': current_player, 'next_player': next_player}, to=room)
@socketio.on('win')
def on_win(data):
        with get_db_connection() as conn:
            conn.execute("UPDATE user SET wins = wins + 1 WHERE username = ?", (data['winnerUsername'],))
            conn.commit()

@socketio.on('reset')
def on_reset(data):
    room = data['room']
    emit('reset', to=room)  

@socketio.on('leave')
def on_leave(data):
    username = session.get('username')
    room = data['room']
    leave_room(room)
    emit('log', {'msg': f"{username} has left the room."}, to=room)
    emit('player_left', {'username': username}, to=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)
