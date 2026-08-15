import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_secreta_omnichat'
socketio = SocketIO(app, cors_allowed_origins="*") # Permitir conexiones abiertas

def get_db():
    conn = sqlite3.connect('omnichat.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS contacts (username TEXT, friend TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS friend_requests (sender TEXT, receiver TEXT, status TEXT)')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    if 'username' not in session: return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form['username']
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/search_user', methods=['POST'])
def search_user():
    query = request.json.get('query', '')
    conn = get_db()
    users = conn.execute("SELECT username FROM users WHERE username LIKE ? AND username != ?", 
                         ('%'+query+'%', session['username'])).fetchall()
    conn.close()
    return {'success': True, 'users': [u['username'] for u in users]}

@app.route('/get_friends', methods=['GET'])
def get_friends():
    conn = get_db()
    friends = conn.execute("SELECT friend FROM contacts WHERE username = ?", (session['username'],)).fetchall()
    conn.close()
    return {'success': True, 'friends': [f['friend'] for f in friends]}

@app.route('/send_friend_request', methods=['POST'])
def send_friend_request():
    receiver = request.json.get('receiver')
    conn = get_db()
    conn.execute("INSERT INTO friend_requests (sender, receiver, status) VALUES (?, ?, 'pending')", (session['username'], receiver))
    conn.commit()
    conn.close()
    return {'success': True}

@app.route('/get_notifications', methods=['GET'])
def get_notifications():
    conn = get_db()
    reqs = conn.execute("SELECT sender FROM friend_requests WHERE receiver = ? AND status = 'pending'", (session['username'],)).fetchall()
    conn.close()
    return {'success': True, 'requests': [r['sender'] for r in reqs]}

@app.route('/accept_friend_request', methods=['POST'])
def accept_friend_request():
    sender = request.json.get('sender')
    conn = get_db()
    conn.execute("UPDATE friend_requests SET status = 'accepted' WHERE sender = ? AND receiver = ?", (sender, session['username']))
    conn.execute("INSERT INTO contacts (username, friend) VALUES (?, ?), (?, ?)", (session['username'], sender, sender, session['username']))
    conn.commit()
    conn.close()
    return {'success': True}

@socketio.on('message')
def handle_message(data):
    print(f"Mensaje recibido del servidor: {data}")
    emit('message', data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))