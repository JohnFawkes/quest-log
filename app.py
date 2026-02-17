import logging
import mimetypes
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import requests as http_requests
from authlib.integrations.flask_client import OAuth
from flask import (
    Flask, flash, make_response, redirect, render_template, request,
    send_from_directory, session, url_for,
)
from flask_login import (
    LoginManager, UserMixin, current_user, login_required, login_user, logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# Allow OAuth over HTTP
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# --- CONFIGURATION ---
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', "")
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', "")
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', "")
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', "")
PUBLIC_DOMAIN = os.environ.get('PUBLIC_DOMAIN', "http://localhost:5000")
DEMO_EMAIL = "demo@questlog.app"

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database Setup
basedir = os.path.abspath(os.path.dirname(__file__))
data_dir = os.environ.get('DATA_DIR', basedir)
db_path = os.path.join(data_dir, 'questlog.db') 

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static/uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['DISCORD_WEBHOOK_URL'] = DISCORD_WEBHOOK_URL
app.config['GOOGLE_CLIENT_ID'] = GOOGLE_CLIENT_ID
app.config['GOOGLE_CLIENT_SECRET'] = GOOGLE_CLIENT_SECRET
app.config['ADMIN_EMAIL'] = ADMIN_EMAIL

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(data_dir, exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    name = db.Column(db.String(100))
    picture = db.Column(db.String(200))
    points = db.Column(db.Integer, default=0)
    is_admin = db.Column(db.Boolean, default=False)
    force_password_change = db.Column(db.Boolean, default=False)
    last_penalty_check = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    theme = db.Column(db.String(50), default='dark')
    completions = db.relationship('Completion', backref='user', lazy=True)

class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    points_reward = db.Column(db.Integer, default=10)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) 
    schedule_type = db.Column(db.String(20), default='daily') 
    schedule_days = db.Column(db.String(50)) 
    interval_days = db.Column(db.Integer)    
    penalty_enabled = db.Column(db.Boolean, default=False)
    penalty_amount = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    assigned_user = db.relationship('User', foreign_keys=[assigned_user_id])

class Completion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    habit_name = db.Column(db.String(100))
    image_filename = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending') 
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Reward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cost = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(200))
    icon = db.Column(db.String(50), default='fas fa-gift') # FontAwesome class
    is_approved = db.Column(db.Boolean, default=True) # False if requested by user
    is_demo = db.Column(db.Boolean, default=False) # True if for demo account only
    requested_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    requested_by = db.relationship('User', foreign_keys=[requested_by_id])

class Redemption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reward_name = db.Column(db.String(100))
    cost = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# --- Helpers ---
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def send_discord_webhook(content, image_filename=None):
    url = app.config['DISCORD_WEBHOOK_URL']
    if not url:
        return
    try:
        files = {}
        file_handle = None
        if image_filename:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            if os.path.exists(file_path):
                file_handle = open(file_path, 'rb')
                files = {'file': file_handle}
        http_requests.post(url, data={'content': content}, files=files, timeout=10)
    except Exception as e:
        logger.warning("Discord Webhook Error: %s", e)
    finally:
        if file_handle:
            file_handle.close()

def is_habit_due_on_date(habit, check_date):
    check_date = check_date.replace(hour=0, minute=0, second=0, microsecond=0)
    created = habit.created_at if habit.created_at.tzinfo else habit.created_at.replace(tzinfo=timezone.utc)
    habit_start = created.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if habit.schedule_type == 'daily':
        return True
    elif habit.schedule_type == 'weekly':
        if not habit.schedule_days: return False
        due_days = [int(d) for d in habit.schedule_days.split(',')]
        return check_date.weekday() in due_days
    elif habit.schedule_type == 'interval':
        if not habit.interval_days: return False
        delta = (check_date - habit_start).days
        return delta % habit.interval_days == 0
    elif habit.schedule_type == 'biweekly':
        if not habit.schedule_days: return False
        due_days = [int(d) for d in habit.schedule_days.split(',')]
        if check_date.weekday() not in due_days:
            return False
        weeks_diff = (check_date - habit_start).days // 7
        return weeks_diff % 2 == 0
    return False

def calculate_next_due_date(habit):
    """Finds the next due date for a habit starting from tomorrow."""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    check_date = today + timedelta(days=1)
    
    # Limit search to 30 days to prevent infinite loops on broken schedules
    for _ in range(30):
        if is_habit_due_on_date(habit, check_date):
            return check_date
        check_date += timedelta(days=1)
    return None

def check_missed_habits(user):
    if not user.last_penalty_check:
        user.last_penalty_check = datetime.now(timezone.utc) - timedelta(days=1)
    
    last_check = user.last_penalty_check
    if last_check.tzinfo is None:
        last_check = last_check.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    check_date = last_check.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    if check_date >= yesterday:
        user.last_penalty_check = now
        db.session.commit()
        return 
        
    habits = Habit.query.filter_by(assigned_user_id=user.id, penalty_enabled=True).all()
    
    current_check = check_date
    while current_check <= yesterday:
        for habit in habits:
            created = habit.created_at if habit.created_at.tzinfo else habit.created_at.replace(tzinfo=timezone.utc)
            if created > current_check: continue
            if is_habit_due_on_date(habit, current_check):
                start_of_day = current_check
                end_of_day = current_check + timedelta(days=1)
                completion = Completion.query.filter(
                    Completion.habit_id == habit.id,
                    Completion.user_id == user.id,
                    Completion.timestamp >= start_of_day,
                    Completion.timestamp < end_of_day,
                    Completion.status.in_(['pending', 'approved'])
                ).first()
                
                if not completion:
                    user.points -= habit.penalty_amount
                    penalty_record = Completion(
                        user_id=user.id,
                        habit_id=habit.id,
                        habit_name=habit.name,
                        status='penalty',
                        timestamp=current_check + timedelta(hours=12)
                    )
                    db.session.add(penalty_record)
        current_check += timedelta(days=1)
    user.last_penalty_check = now
    db.session.commit()

@app.before_request
def check_setup_required():
    if current_user.is_authenticated and current_user.force_password_change:
        if request.endpoint in ['setup_account', 'static', 'logout']: return
        flash("Setup required: Please update your account details.", "warning")
        return redirect(url_for('setup_account'))

# --- Initialization Function ---
def perform_db_migration():
    """Checks for missing columns and adds them if necessary."""
    if not os.path.exists(db_path): return # DB not created yet

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # User Table
    cursor.execute("PRAGMA table_info(user)")
    user_cols = [col[1] for col in cursor.fetchall()]
    if 'last_penalty_check' not in user_cols:
        cursor.execute("ALTER TABLE user ADD COLUMN last_penalty_check TIMESTAMP")
    if 'password_hash' not in user_cols:
        cursor.execute("ALTER TABLE user ADD COLUMN password_hash VARCHAR(200)")
    if 'force_password_change' not in user_cols:
        cursor.execute("ALTER TABLE user ADD COLUMN force_password_change BOOLEAN DEFAULT 0")
    if 'theme' not in user_cols:
        cursor.execute("ALTER TABLE user ADD COLUMN theme VARCHAR(50) DEFAULT 'dark'")

    # Habit Table
    cursor.execute("PRAGMA table_info(habit)")
    habit_cols = [col[1] for col in cursor.fetchall()]
    habit_updates = [
        ('assigned_user_id', 'INTEGER'),
        ('schedule_type', 'VARCHAR(20)'),
        ('schedule_days', 'VARCHAR(50)'),
        ('interval_days', 'INTEGER'),
        ('penalty_enabled', 'BOOLEAN'),
        ('penalty_amount', 'INTEGER'),
        ('created_at', 'TIMESTAMP')
    ]
    for col_name, col_type in habit_updates:
        if col_name not in habit_cols:
            cursor.execute(f"ALTER TABLE habit ADD COLUMN {col_name} {col_type}")

    # Reward Table
    cursor.execute("PRAGMA table_info(reward)")
    reward_cols = [col[1] for col in cursor.fetchall()]
    reward_updates = [
        ('icon', 'VARCHAR(50)'),
        ('is_approved', 'BOOLEAN'),
        ('is_demo', 'BOOLEAN'),
        ('requested_by_id', 'INTEGER')
    ]
    for col_name, col_type in reward_updates:
        if col_name not in reward_cols:
            cursor.execute(f"ALTER TABLE reward ADD COLUMN {col_name} {col_type}")
            if col_name == 'is_approved':
                cursor.execute("UPDATE reward SET is_approved = 1 WHERE is_approved IS NULL")
            if col_name == 'is_demo':
                cursor.execute("UPDATE reward SET is_demo = 0 WHERE is_demo IS NULL")
            if col_name == 'icon':
                cursor.execute("UPDATE reward SET icon = 'fas fa-gift' WHERE icon IS NULL")

    conn.commit()
    conn.close()

def initialize_database():
    """Create DB tables, default admin, and Demo User content."""
    with app.app_context():
        # 1. Create tables if they don't exist
        db.create_all()
        
        # 2. Run manual migration checks to add columns to existing tables
        perform_db_migration() 
        
        # 3. Seed Data
        # Wrap attempts in try-except IntegrityError to handle race conditions with Gunicorn workers
        try:
            if User.query.filter_by(is_admin=True).count() == 0:
                print("Creating default 'admin' account...")
                default_admin = User(
                    email="admin", name="Guild Master",
                    password_hash=generate_password_hash("admin", method='scrypt'),
                    is_admin=True, force_password_change=True, theme='dark'
                )
                db.session.add(default_admin)
                db.session.commit()
        except IntegrityError:
            db.session.rollback()
            print("Admin account already exists (race condition handled).")
            
        try:
            demo_user = User.query.filter_by(email=DEMO_EMAIL).first()
            if not demo_user:
                print("Creating Demo User and content...")
                demo_user = User(
                    email=DEMO_EMAIL, name="Demo Adventurer",
                    password_hash=generate_password_hash("demo", method='scrypt'),
                    points=50, is_admin=False, force_password_change=False, theme='dark'
                )
                db.session.add(demo_user)
                db.session.commit()
                
                # Fallback download
                demo_img_1 = os.path.join(app.config['UPLOAD_FOLDER'], 'demo.webp')
                if not os.path.exists(demo_img_1):
                    try:
                        resp = http_requests.get("https://placehold.co/600x400/100150/FFF.webp?text=Walked+the+Dog", timeout=5)
                        if resp.status_code == 200:
                            with open(demo_img_1, 'wb') as f: f.write(resp.content)
                    except Exception as e:
                        logger.warning("Failed to download demo image 1: %s", e)

                demo_img_2 = os.path.join(app.config['UPLOAD_FOLDER'], 'demo2.jpg')
                if not os.path.exists(demo_img_2):
                    try:
                        resp = http_requests.get("https://placehold.co/600x400/501002/FFF.jpg?text=Hydration+Check", timeout=5)
                        if resp.status_code == 200:
                            with open(demo_img_2, 'wb') as f: f.write(resp.content)
                    except Exception as e:
                        logger.warning("Failed to download demo image 2: %s", e)

                habits = [
                    Habit(name="Morning Patrol (Walk the Dog)", description="Walk 15 mins", points_reward=15, assigned_user_id=demo_user.id, schedule_type='daily'),
                    Habit(name="Potion Brewing (Drink Water)", description="8 Glasses", points_reward=10, assigned_user_id=demo_user.id, schedule_type='daily'),
                    Habit(name="Clean the Armory (Dishes)", description="Empty sink", points_reward=25, assigned_user_id=demo_user.id, schedule_type='weekly', schedule_days="0,2,4,6"),
                ]
                db.session.add_all(habits)
                db.session.commit()
                
                completions = [
                    Completion(user_id=demo_user.id, habit_id=habits[0].id, habit_name=habits[0].name, image_filename="demo.webp", status="pending", timestamp=datetime.now(timezone.utc) - timedelta(minutes=30)),
                    Completion(user_id=demo_user.id, habit_id=habits[1].id, habit_name=habits[1].name, image_filename="demo2.jpg", status="pending", timestamp=datetime.now(timezone.utc) - timedelta(hours=2))
                ]
                db.session.add_all(completions)
                
                rewards = [
                    Reward(name="Scroll of Knowledge (Book)", cost=100, description="Buy a new book", is_demo=True, icon="fas fa-book"),
                    Reward(name="Elixir of Energy (Coffee)", cost=50, description="Fancy coffee", is_demo=True, icon="fas fa-coffee"),
                    Reward(name="Feast (Pizza Night)", cost=500, description="Order pizza", is_demo=True, icon="fas fa-pizza-slice")
                ]
                if Reward.query.filter_by(is_demo=True).count() == 0:
                    db.session.add_all(rewards)
                
                db.session.commit()
        except IntegrityError:
            db.session.rollback()
            print("Demo user already exists (race condition handled).")

# Call initialization
initialize_database()

# --- Routes ---
@app.route('/health')
def health():
    return {'status': 'ok'}, 200

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin: return redirect(url_for('admin_panel'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.password_hash and check_password_hash(user.password_hash, password):
            login_user(user)
            if user.is_admin: return redirect(url_for('admin_panel'))
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/login/demo')
def login_demo():
    user = User.query.filter_by(email=DEMO_EMAIL).first()
    if user:
        login_user(user)
        flash("Welcome to the Demo! Actions here are read-only/simulated.", "success")
        return redirect(url_for('dashboard'))
    flash("Demo user not found.", "error")
    return redirect(url_for('login'))

@app.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def settings_profile():
    if current_user.email == DEMO_EMAIL:
        flash("Settings are read-only for the Demo user.", "warning")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        theme = request.form.get('theme')
        
        if name:
            current_user.name = name
        if theme:
            current_user.theme = theme
            
        db.session.commit()
        flash('Profile updated!', 'success')
        return redirect(url_for('settings_profile'))
        
    return render_template('settings.html')

@app.route('/setup', methods=['GET', 'POST'])
@login_required
def setup_account():
    if not current_user.force_password_change: return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        if User.query.filter(User.email == email, User.id != current_user.id).first():
            flash("Email taken.", "error")
        else:
            current_user.email = email
            current_user.name = name
            current_user.password_hash = generate_password_hash(password, method='scrypt')
            current_user.force_password_change = False
            db.session.commit()
            return redirect(url_for('admin_panel'))
    return render_template('setup_account.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Email exists', 'error')
            return redirect(url_for('register'))
        new_user = User(email=email, name=name, password_hash=generate_password_hash(password, method='scrypt'))
        if User.query.count() == 0: new_user.is_admin = True
        if app.config['ADMIN_EMAIL'] and email == app.config['ADMIN_EMAIL']: new_user.is_admin = True
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login/google')
def google_login():
    if not app.config['GOOGLE_CLIENT_ID']: return redirect(url_for('login'))
    redirect_uri = f"{PUBLIC_DOMAIN.rstrip('/')}/authorize" if PUBLIC_DOMAIN else url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    try:
        token = google.authorize_access_token()
        user_info = google.userinfo()
        email = user_info['email']
        user = User.query.filter_by(email=email).first()
        should_be_admin = (app.config['ADMIN_EMAIL'] and email == app.config['ADMIN_EMAIL'])
        if not user:
            user = User(email=email, name=user_info['name'], picture=user_info['picture'], is_admin=should_be_admin)
            db.session.add(user)
            db.session.commit()
        elif should_be_admin and not user.is_admin:
            user.is_admin = True
            db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
    except Exception as e:
        logger.error("Google OAuth error: %s", e)
        flash("Login failed. Please try again.", 'error')
        return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    check_missed_habits(current_user)
    all_assigned = Habit.query.filter_by(assigned_user_id=current_user.id).all()
    today = datetime.now(timezone.utc)
    todays_habits = []
    upcoming_habits = []
    
    for h in all_assigned:
        if is_habit_due_on_date(h, today):
            start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            done = Completion.query.filter(
                Completion.habit_id == h.id, 
                Completion.user_id == current_user.id,
                Completion.timestamp >= start_of_day,
                Completion.timestamp < end_of_day,
                Completion.status != 'rejected'
            ).first()
            h.is_completed = bool(done)
            h.completion_status = done.status if done else None
            todays_habits.append(h)
        else:
            # Calculate next due date
            next_due = calculate_next_due_date(h)
            if next_due:
                h.next_due_display = next_due.strftime("%a, %b %d")
            else:
                h.next_due_display = "Unknown"
            upcoming_habits.append(h)

    my_completions = Completion.query.filter_by(user_id=current_user.id).order_by(Completion.timestamp.desc()).limit(10).all()
    
    return render_template('dashboard.html', todays_habits=todays_habits, upcoming_habits=upcoming_habits, completions=my_completions)

@app.route('/habit/<int:habit_id>/complete', methods=['POST'])
@login_required
def complete_habit(habit_id):
    if current_user.email == DEMO_EMAIL:
        flash("The Demo account is read-only. Proof upload is disabled.", "warning")
        return redirect(url_for('dashboard'))

    habit = Habit.query.get_or_404(habit_id)
    if 'proof' not in request.files or request.files['proof'].filename == '':
        flash('Please select an image to upload.', 'warning')
        return redirect(url_for('dashboard'))
    file = request.files['proof']
    if not allowed_file(file.filename):
        flash('Invalid file type. Please upload an image (png, jpg, jpeg, gif, webp).', 'error')
        return redirect(url_for('dashboard'))
    filename = secure_filename(f"{current_user.id}_{datetime.now().timestamp()}_{file.filename}")
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    completion = Completion(user_id=current_user.id, habit_id=habit.id, habit_name=habit.name, image_filename=filename, status='pending')
    db.session.add(completion)
    db.session.commit()
    send_discord_webhook(f"📸 **{current_user.name}** quest update: **{habit.name}**! (Pending Review)", filename)
    flash('Quest submitted for review!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/rewards')
@login_required
def rewards():
    # Filter Logic:
    # 1. Demo User -> ONLY demo rewards
    # 2. Others -> ONLY approved rewards that are NOT demo
    
    if current_user.email == DEMO_EMAIL:
        # Explicitly filter for is_demo=True/1
        rewards_list = Reward.query.filter_by(is_demo=True).all()
    else:
        # Explicitly filter for is_demo=False/0 AND is_approved=True/1
        # Use simple != True check which works for SQLite 0/1 and True/False
        rewards_list = Reward.query.filter(
            (Reward.is_demo == False) | (Reward.is_demo == None),
            Reward.is_approved == True
        ).all()
        
    return render_template('rewards.html', rewards=rewards_list)

@app.route('/rewards/request', methods=['POST'])
@login_required
def request_reward():
    if current_user.email == DEMO_EMAIL:
        flash("The Demo account is read-only. Reward requests are disabled.", "warning")
        return redirect(url_for('rewards'))

    name = request.form.get('name')
    try:
        cost = int(request.form.get('cost'))
    except (TypeError, ValueError):
        flash('Invalid cost value.', 'error')
        return redirect(url_for('rewards'))
    if cost <= 0:
        flash('Cost must be a positive number.', 'error')
        return redirect(url_for('rewards'))
    description = request.form.get('description')
    icon = "fas fa-gift"

    new_reward = Reward(
        name=name, cost=cost, description=description, icon=icon,
        is_approved=False, is_demo=False, requested_by_id=current_user.id
    )
    db.session.add(new_reward)
    db.session.commit()
    
    send_discord_webhook(f"💡 **{current_user.name}** requested a new reward: **{name}** ({cost} Gems).")
    flash('Reward requested! Waiting for Guild Master approval.', 'success')
    return redirect(url_for('rewards'))

@app.route('/rewards/redeem/<int:reward_id>', methods=['POST'])
@login_required
def redeem_reward(reward_id):
    reward = Reward.query.get_or_404(reward_id)
    
    if current_user.email == DEMO_EMAIL and not reward.is_demo:
        flash("Demo users can only redeem demo rewards.", "error")
        return redirect(url_for('rewards'))

    if current_user.points >= reward.cost:
        current_user.points -= reward.cost
        db.session.add(Redemption(user_id=current_user.id, reward_name=reward.name, cost=reward.cost))
        db.session.commit()
        send_discord_webhook(f"🎁 **{current_user.name}** claimed **{reward.name}**!")
        flash('Reward Claimed!', 'success')
    else: flash('Not enough Gems.', 'error')
    return redirect(url_for('rewards'))

# --- ADMIN ROUTES ---

@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    
    # Filter: Hide pending quests from the Demo User
    pending = Completion.query.join(User).filter(Completion.status == 'pending', User.email != DEMO_EMAIL).all()
    
    # Filter: Hide Demo User from assignment list
    users = User.query.filter(User.email != DEMO_EMAIL).all()
    
    habits = Habit.query.all()
    
    # Filter: Hide demo rewards from management list
    # Use explicit NULL checks for safety with SQLite
    pending_rewards = Reward.query.filter(
        Reward.is_approved == False, 
        (Reward.is_demo == False) | (Reward.is_demo == None)
    ).all()
    
    active_rewards = Reward.query.filter(
        Reward.is_approved == True, 
        (Reward.is_demo == False) | (Reward.is_demo == None)
    ).all()
    
    return render_template('admin.html', 
                         pending=pending, 
                         users=users, 
                         habits=habits,
                         pending_rewards=pending_rewards,
                         active_rewards=active_rewards)

@app.route('/admin/reward/create', methods=['POST'])
@login_required
def create_reward_admin():
    if not current_user.is_admin: return redirect(url_for('index'))
    name = request.form.get('name')
    cost = int(request.form.get('cost'))
    description = request.form.get('description')
    icon = request.form.get('icon')
    new_reward = Reward(name=name, cost=cost, description=description, icon=icon, is_approved=True, is_demo=False)
    db.session.add(new_reward)
    db.session.commit()
    flash('Reward added to shop.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/reward/approve/<int:reward_id>', methods=['POST'])
@login_required
def approve_reward(reward_id):
    if not current_user.is_admin: return redirect(url_for('index'))
    reward = Reward.query.get_or_404(reward_id)
    reward.is_approved = True
    db.session.commit()
    flash('Reward approved.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/reward/delete/<int:reward_id>', methods=['POST'])
@login_required
def delete_reward(reward_id):
    if not current_user.is_admin: return redirect(url_for('index'))
    reward = Reward.query.get_or_404(reward_id)
    db.session.delete(reward)
    db.session.commit()
    flash('Reward deleted.', 'info')
    return redirect(url_for('admin_panel'))

@app.route('/admin/habit/delete/<int:habit_id>', methods=['POST'])
@login_required
def delete_habit(habit_id):
    if not current_user.is_admin: return redirect(url_for('index'))
    habit = Habit.query.get_or_404(habit_id)
    Completion.query.filter_by(habit_id=habit.id).delete()
    db.session.delete(habit)
    db.session.commit()
    flash('Quest deleted.', 'info')
    return redirect(url_for('admin_panel'))

@app.route('/admin/user/create', methods=['POST'])
@login_required
def create_user_admin():
    if not current_user.is_admin: return redirect(url_for('index'))
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')
    if User.query.filter_by(email=email).first(): flash('User exists', 'error')
    else:
        new_user = User(email=email, name=name, password_hash=generate_password_hash(password, method='scrypt'))
        db.session.add(new_user)
        db.session.commit()
        flash('Adventurer recruited!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/user/promote', methods=['POST'])
@login_required
def promote_user():
    if not current_user.is_admin: return redirect(url_for('index'))
    user_id = request.form.get('user_id')
    user = db.session.get(User, int(user_id))
    if user:
        user.is_admin = True
        db.session.commit()
        flash(f'{user.name} promoted to Admin.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/habit/create', methods=['POST'])
@login_required
def create_habit():
    if not current_user.is_admin: return redirect(url_for('index'))
    name = request.form.get('name')
    points = int(request.form.get('points'))
    assigned_user_id = request.form.get('assigned_user_id')
    schedule_type = request.form.get('schedule_type')
    schedule_days = ",".join(request.form.getlist('days')) if schedule_type in ['weekly', 'biweekly'] else None
    interval_days = int(request.form.get('interval_days')) if schedule_type == 'interval' else None
    penalty_enabled = 'penalty_enabled' in request.form
    penalty_amount = int(request.form.get('penalty_amount') or 0)

    new_habit = Habit(
        name=name, points_reward=points, assigned_user_id=assigned_user_id,
        schedule_type=schedule_type, schedule_days=schedule_days,
        interval_days=interval_days, penalty_enabled=penalty_enabled, penalty_amount=penalty_amount
    )
    db.session.add(new_habit)
    db.session.commit()
    flash('Quest assigned!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/approve/<int:completion_id>', methods=['POST'])
@login_required
def approve_completion(completion_id):
    if not current_user.is_admin: return redirect(url_for('index'))
    completion = Completion.query.get_or_404(completion_id)
    user = db.session.get(User, completion.user_id)
    if user.email == DEMO_EMAIL:
        flash("Cannot approve quests for the Demo user.", "warning")
        return redirect(url_for('admin_panel'))
    if completion.status == 'pending':
        completion.status = 'approved'
        habit = db.session.get(Habit, completion.habit_id)
        if habit: user.points += habit.points_reward
        db.session.commit()
        send_discord_webhook(f"✅ **{user.name}** completed **{completion.habit_name}**! (Approved)", completion.image_filename)
    return redirect(url_for('admin_panel'))

@app.route('/admin/reject/<int:completion_id>', methods=['POST'])
@login_required
def reject_completion(completion_id):
    if not current_user.is_admin: return redirect(url_for('index'))
    completion = Completion.query.get_or_404(completion_id)
    user = db.session.get(User, completion.user_id)
    if user.email == DEMO_EMAIL:
        flash("Cannot reject quests for the Demo user.", "warning")
        return redirect(url_for('admin_panel'))
    completion.status = 'rejected'
    db.session.commit()
    return redirect(url_for('admin_panel'))

# UPDATED: Add header for inline image display and guess MIME type
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # Guess mime type based on extension
    mime_type, _ = mimetypes.guess_type(filename)
    
    # Fallback if guess fails
    if not mime_type:
        if filename.lower().endswith('.webp'):
            mime_type = 'image/webp'
        elif filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
            mime_type = 'image/jpeg'
        elif filename.lower().endswith('.png'):
            mime_type = 'image/png'
        else:
            mime_type = 'application/octet-stream'

    response = make_response(send_from_directory(app.config['UPLOAD_FOLDER'], filename))
    response.headers['Content-Type'] = mime_type
    response.headers['Content-Disposition'] = 'inline'
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
