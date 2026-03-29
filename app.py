
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data.db')
KEY_PATH = os.path.join(BASE_DIR, 'secret.key')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET') or os.urandom(24)

db = SQLAlchemy(app)

def get_fernet():
    if not os.path.exists(KEY_PATH):
        key = Fernet.generate_key()
        with open(KEY_PATH, 'wb') as f:
            f.write(key)
    else:
        with open(KEY_PATH, 'rb') as f:
            key = f.read()
    return Fernet(key)

fernet = get_fernet()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(80), nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Memory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.Integer, unique=True, nullable=False)
    encrypted_data = db.Column(db.Text, nullable=True)
    owner_role = db.Column(db.String(20), nullable=False)
    owner_username = db.Column(db.String(80), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    previous_encrypted_data = db.Column(db.Text, nullable=True)
    previous_timestamp = db.Column(db.DateTime, nullable=True)

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text, nullable=False)

def init_db():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', display_name='System Admin', password_hash=generate_password_hash('adminpass'), role='admin')
        user = User(username='user', display_name='Test User', password_hash=generate_password_hash('userpass'), role='user')
        db.session.add_all([admin, user])
        db.session.add_all([admin, user])
        db.session.commit()

with app.app_context():
    init_db()

def log_event(event_type, details):
    l = Log(event_type=event_type, details=details)
    db.session.add(l)
    db.session.commit()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            log_event('failed_login', f'Failed login for username={username}')
            return render_template('login.html', error='UNAUTHORIZED ACCESS DETECTED')
        session['username'] = user.username
        session['display_name'] = user.display_name or user.username
        session['role'] = user.role
        session.permanent = True
        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        display_name = request.form.get('display_name')
        password = request.form.get('password')
        role = 'user' # default role
        if User.query.filter_by(username=username).first():
            return render_template('login.html', error='Username already exists', register=True)
        
        user = User(username=username, display_name=display_name, password_hash=generate_password_hash(password), role=role)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('login.html', register=True)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    old_pwd = request.json.get('old_password')
    new_pwd = request.json.get('new_password')
    
    user = User.query.filter_by(username=session.get('username')).first()
    if not user or not check_password_hash(user.password_hash, old_pwd):
        return jsonify({'success': False, 'error': 'Incorrect current password'}), 401
        
    user.password_hash = generate_password_hash(new_pwd)
    db.session.commit()
    log_event('password_change', f"{session.get('username')} updated their password")
    return jsonify({'success': True})

@app.route('/admin')
@login_required
def admin_dashboard():
    if session.get('role') != 'admin':
        log_event('role_violation', f"{session.get('username')} tried to access admin dashboard")
        return render_template('error.html', message='Access Denied')
    
    stats = {
        'mem_cells': Memory.query.count(),
        'access_logs': Log.query.count(),
        'critical_events': Log.query.filter(Log.event_type.in_(['failed_login', 'role_violation', 'unauthorized_memory_access', 'invalid_address'])).count(),
        'secure_ops': Log.query.filter(Log.event_type == 'memory_write').count() # we don't have this yet, but for the UI
    }
    logs = Log.query.order_by(Log.timestamp.desc()).limit(10).all()
    return render_template('admin_dashboard.html', stats=stats, logs=logs)

@app.route('/user')
@login_required
def user_dashboard():
    if session.get('role') != 'user':
        log_event('role_violation', f"{session.get('username')} tried to access user dashboard")
        return render_template('error.html', message='Access Denied')
    
    user = session.get('username')
    mems = Memory.query.filter_by(owner_username=user).all()
    stats = {
        'mem_cells': len(mems),
        'access_logs': Log.query.filter(Log.details.contains(user)).count(),
        'critical_events': Log.query.filter(Log.details.contains(user), Log.event_type.in_(['role_violation', 'unauthorized_memory_access', 'invalid_address'])).count(),
        'secure_ops': Log.query.filter(Log.details.contains(user), Log.event_type.in_(['memory_write', 'memory_read', 'memory_erased'])).count()
    }
    logs = Log.query.filter(Log.details.contains(user)).order_by(Log.timestamp.desc()).limit(10).all()
    return render_template('user_dashboard.html', mems=mems, stats=stats, logs=logs)

@app.route('/memory', methods=['GET'])
@login_required
def memory_page():
    if session.get('role') == 'admin':
        mems = Memory.query.all()
    else:
        mems = Memory.query.filter_by(owner_username=session.get('username')).all()
    return render_template('memory.html', mems=mems)

@app.route('/api/memory/read', methods=['POST'])
@login_required
def api_memory_read():
    # Check if locked
    if session.get('read_locked'):
        lockout_time = session.get('lockout_time', 0)
        time_passed = datetime.utcnow().timestamp() - lockout_time
        if time_passed < 60:
            remaining = int(60 - time_passed)
            return jsonify({
                'success': False, 
                'error': f'Security lockout: Try again in {remaining}s.',
                'remaining': remaining,
                'status': 423
            }), 423
        else:
            # Cooldown expired
            session['read_locked'] = False
            session['failed_reads'] = 0

    addr = request.json.get('address')
    mem = Memory.query.filter_by(address=addr).first()
    
    # Initialize failed attempts if not present
    if 'failed_reads' not in session:
        session['failed_reads'] = 0

    if not mem:
        session['failed_reads'] += 1
        log_event('invalid_address', f"{session.get('username')} attempted read invalid address {addr} (Fail {session['failed_reads']}/3)")
        if session['failed_reads'] >= 3:
            session['read_locked'] = True
            session['lockout_time'] = datetime.utcnow().timestamp()
            return jsonify({'success': False, 'error': 'Security lockout: Try again in 60s.', 'remaining': 60, 'status': 423}), 423
        return jsonify({'success': False, 'error': f'Invalid address. Attempt {session["failed_reads"]}/3'}), 400

    # access control
    if session.get('role') != 'admin' and mem.owner_username != session.get('username'):
        session['failed_reads'] += 1
        log_event('unauthorized_memory_access', f"{session.get('username')} unauthorized read address {addr} (Fail {session['failed_reads']}/3)")
        if session['failed_reads'] >= 3:
            session['read_locked'] = True
            session['lockout_time'] = datetime.utcnow().timestamp()
            return jsonify({'success': False, 'error': 'Security lockout: Try again in 60s.', 'remaining': 60, 'status': 423}), 423
        return jsonify({'success': False, 'error': f'Unauthorized access to address. Attempt {session["failed_reads"]}/3'}), 403

    # Reset on success
    session['failed_reads'] = 0
    data = None
    prev_data = None
    
    if mem.encrypted_data:
        try:
            data = fernet.decrypt(mem.encrypted_data.encode()).decode()
        except Exception:
            data = '[decryption error]'
            
    if mem.previous_encrypted_data:
        try:
            prev_data = fernet.decrypt(mem.previous_encrypted_data.encode()).decode()
        except Exception:
            prev_data = '[decryption error]'

    return jsonify({
        'success': True, 
        'address': addr, 
        'data': data, 
        'previous_data': prev_data,
        'encrypted_data': mem.encrypted_data,
        'previous_timestamp': mem.previous_timestamp.strftime('%m/%d/%Y, %H:%M') if mem.previous_timestamp else None,
        'owner': mem.owner_username
    })

@app.route('/api/memory/write', methods=['POST'])
@login_required
def api_memory_write():
    addr = request.json.get('address')
    raw = request.json.get('data')
    mem = Memory.query.filter_by(address=addr).first()
    if not mem:
        # Dynamically create memory record if writing to new address
        mem = Memory(address=addr, owner_role=session.get('role'), owner_username=session.get('username'))
        db.session.add(mem)
    if session.get('role') != 'admin' and mem.owner_username != session.get('username'):
        log_event('unauthorized_memory_access', f"{session.get('username')} unauthorized write address {addr}")
        return jsonify({'success': False, 'error': 'Unauthorized access to address'}), 403
    token = fernet.encrypt(raw.encode()).decode()
    
    # Store history before updating
    if mem.encrypted_data:
        mem.previous_encrypted_data = mem.encrypted_data
        mem.previous_timestamp = mem.timestamp
        
    mem.encrypted_data = token
    mem.timestamp = datetime.utcnow()
    db.session.commit()
    log_event('memory_write', f"{session.get('username')} wrote to address {addr}")
    return jsonify({'success': True, 'address': addr})

@app.route('/logs')
@login_required
def logs_page():
    if session.get('role') != 'admin':
        log_event('role_violation', f"{session.get('username')} tried to access logs")
        return render_template('error.html', message='Access Denied')
    logs = Log.query.order_by(Log.timestamp.desc()).all()
    return render_template('logs.html', logs=logs)

@app.route('/architecture')
@login_required
def architecture():
    return render_template('architecture.html')

@app.route('/api/memory/delete', methods=['POST'])
@login_required
def api_memory_delete():
    data = request.get_json()
    addr = data.get('address')
    
    mem = Memory.query.filter_by(address=addr).first()
    if not mem:
        return jsonify({'success': False, 'error': 'Address not found'}), 404
        
    if mem.owner_username != session.get('username') and session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    db.session.delete(mem)
    db.session.commit()
    
    # Log the deletion using the correct function
    log_event('memory_erased', f"Memory address 0x{int(addr):04X} was manually purged by {session.get('username')}")
    
    return jsonify({'success': True})

@app.route('/api/log/delete', methods=['POST'])
@login_required
def api_log_delete():
    try:
        data = request.get_json()
        log_id = data.get('id')
        user = session.get('username', '')
        
        with open('debug.log', 'a') as f:
            f.write(f"[{datetime.now()}] Attempt: user={user}, id={log_id}\n")

        if log_id is None:
            return jsonify({'success': False, 'error': 'Missing ID'}), 400

        # Try to find the log entry
        log_entry = Log.query.get(int(log_id))
        if not log_entry:
            with open('debug.log', 'a') as f:
                f.write(f"[{datetime.now()}] Error: Log ID {log_id} not found in database.\n")
            return jsonify({'success': False, 'error': f'Log entry {log_id} not found'}), 404
            
        # Verify ownership
        details = log_entry.details.lower()
        username_lower = user.lower()
        if username_lower not in details and session.get('role') != 'admin':
            with open('debug.log', 'a') as f:
                f.write(f"[{datetime.now()}] Auth Fail: '{username_lower}' not in '{details}'\n")
            return jsonify({'success': False, 'error': 'You do not have permission to delete this log.'}), 403
            
        db.session.delete(log_entry)
        db.session.commit()
        
        with open('debug.log', 'a') as f:
            f.write(f"[{datetime.now()}] Success: Log {log_id} deleted.\n")
            
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        with open('debug.log', 'a') as f:
            f.write(f"[{datetime.now()}] System Error: {str(e)}\n")
        return jsonify({'success': False, 'error': f"System error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
