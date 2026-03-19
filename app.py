import glob as _glob
import logging
import mimetypes
import os
import re
import secrets
import sqlite3
import threading
import time
import types
import zipfile
from datetime import datetime, timedelta, timezone

import apprise
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

# Timezone helper — used by the `localtime` Jinja2 filter
def _get_localtz():
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    tz_name = os.environ.get('TZ', 'UTC')
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError):
        logger.warning("Unknown TZ value %r, falling back to UTC", tz_name)
        return ZoneInfo('UTC')

# Allow OAuth over HTTP
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# --- CONFIGURATION ---
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', "")
APPRISE_URLS = os.environ.get('APPRISE_URLS', "")
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', "")
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', "")
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', "")
PUBLIC_DOMAIN = os.environ.get('PUBLIC_DOMAIN', "http://localhost:5000")
BACKUP_DIR = os.environ.get('BACKUP_DIR', '/backups')
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

@app.template_filter('localtime')
def localtime_filter(dt):
    """Convert a UTC datetime to the server's local timezone for display."""
    if dt is None:
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_get_localtz())
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
    coins = db.Column(db.Integer, default=0)
    is_admin = db.Column(db.Boolean, default=False)
    force_password_change = db.Column(db.Boolean, default=False)
    last_penalty_check = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    theme = db.Column(db.String(50), default='dark')
    # Avatar
    avatar_body = db.Column(db.String(10), default='male')
    avatar_role = db.Column(db.String(20), default='knight')
    avatar_head_id = db.Column(db.Integer, db.ForeignKey('avatar_item.id'), nullable=True)
    avatar_chest_id = db.Column(db.Integer, db.ForeignKey('avatar_item.id'), nullable=True)
    avatar_weapon_id = db.Column(db.Integer, db.ForeignKey('avatar_item.id'), nullable=True)
    avatar_offhand_id = db.Column(db.Integer, db.ForeignKey('avatar_item.id'), nullable=True)
    avatar_spell_id = db.Column(db.Integer, db.ForeignKey('avatar_item.id'), nullable=True)
    completions = db.relationship('Completion', backref='user', lazy=True)
    avatar_items = db.relationship('AvatarItem', secondary='user_avatar_items', backref='owners')

habit_users = db.Table('habit_users',
    db.Column('habit_id', db.Integer, db.ForeignKey('habit.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    points_reward = db.Column(db.Integer, default=10)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # legacy, kept for migration
    schedule_type = db.Column(db.String(20), default='daily')
    schedule_days = db.Column(db.String(50))
    interval_days = db.Column(db.Integer)
    penalty_enabled = db.Column(db.Boolean, default=False)
    penalty_amount = db.Column(db.Integer, default=0)
    streak_enabled = db.Column(db.Boolean, default=False)
    streak_milestone = db.Column(db.Integer, default=5)
    streak_multiplier = db.Column(db.Float, default=2.0)
    coins_reward = db.Column(db.Integer, default=1)
    coins_streak_bonus = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    assigned_users = db.relationship('User', secondary=habit_users, backref='assigned_habits')

class Completion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    habit_name = db.Column(db.String(100))
    image_filename = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    action_token = db.Column(db.String(64))  # single-use token for webhook approve/reject links

class AppSetting(db.Model):
    """Key-value store for app-wide configuration set via the UI."""
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text)

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

user_avatar_items = db.Table('user_avatar_items',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('avatar_item_id', db.Integer, db.ForeignKey('avatar_item.id'), primary_key=True)
)

class AvatarItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300))
    item_type = db.Column(db.String(20), nullable=False)  # head/chest/weapon/offhand/spell
    svg_filename = db.Column(db.String(100), nullable=False)
    coin_cost = db.Column(db.Integer, default=0)
    is_starter = db.Column(db.Boolean, default=False)
    rarity = db.Column(db.String(20), default='common')  # common/rare/epic/legendary

# --- Helpers ---
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def get_setting(key, default=None):
    s = db.session.get(AppSetting, key)
    return s.value if s else default

def set_setting(key, value):
    s = db.session.get(AppSetting, key)
    if s:
        s.value = value
    else:
        db.session.add(AppSetting(key=key, value=value))
    db.session.commit()

def _build_apprise():
    """Build an Apprise instance from configured URLs, injecting icon URL where supported."""
    ap = apprise.Apprise()
    icon_url = get_setting('notification_icon_url', '')
    # DB setting overrides env var if set
    apprise_urls = get_setting('apprise_urls', '') or APPRISE_URLS
    discord_url = get_setting('discord_webhook_url', '') or DISCORD_WEBHOOK_URL
    if apprise_urls:
        for url in apprise_urls.split(','):
            url = url.strip()
            if url:
                ap.add(url)
    if discord_url:
        # Convert to Apprise Discord URL format so we can inject avatar_url
        m = re.match(r'https://discord(?:app)?\.com/api/webhooks/(\d+)/([^?]+)', discord_url)
        if m and icon_url:
            ap.add(f"discord://{m.group(1)}/{m.group(2)}?avatar_url={icon_url}")
        else:
            ap.add(discord_url)
    return ap

def send_notification(content, image_filename=None, completion_id=None, action_token=None):
    """Send a notification via Apprise. Appends approve/reject links when token info provided."""
    if completion_id and action_token and PUBLIC_DOMAIN:
        approve_url = f"{PUBLIC_DOMAIN}/quest/approve/{completion_id}/{action_token}"
        reject_url = f"{PUBLIC_DOMAIN}/quest/reject/{completion_id}/{action_token}"
        content += f"\n✅ **Approve:** {approve_url}\n❌ **Reject:** {reject_url}"
    ap = _build_apprise()
    if not len(ap):
        logger.warning("No notification services configured (set APPRISE_URLS or DISCORD_WEBHOOK_URL)")
        return
    attach = None
    if image_filename:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        if os.path.exists(file_path):
            attach = apprise.AppriseAttachment(file_path)
    try:
        result = ap.notify(body=content, attach=attach)
        if result:
            logger.info("Notification sent OK")
        else:
            logger.warning("Apprise notification failed (check your URLs and service config)")
    except Exception as e:
        logger.warning("Notification error: %s", e)

# --- Backup ---
_backup_lock = threading.Lock()
_last_backup_date = [None]  # per-worker mutable cell

def _perform_backup():
    """Create a timestamped zip of questlog.db; keep only the last 7 daily backups."""
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        today_str = datetime.now(_get_localtz()).strftime('%Y-%m-%d')
        # Skip if a backup already exists for today (prevents duplicate runs across workers)
        if _glob.glob(os.path.join(BACKUP_DIR, f'{today_str}*.zip')):
            return
        ts = datetime.now(_get_localtz()).strftime('%Y-%m-%d_%H-%M-%S')
        zip_path = os.path.join(BACKUP_DIR, f'{ts}.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(db_path, 'questlog.db')
        # Prune: keep newest 7
        all_backups = sorted(_glob.glob(os.path.join(BACKUP_DIR, '*.zip')))
        while len(all_backups) > 7:
            os.remove(all_backups.pop(0))
        logger.info("Daily backup written: %s", zip_path)
    except Exception as exc:
        logger.error("Backup failed: %s", exc)

@app.before_request
def _maybe_backup():
    """Trigger a daily backup on the first request of each calendar day (per worker)."""
    today = datetime.now(_get_localtz()).date()
    if _last_backup_date[0] != today:
        with _backup_lock:
            if _last_backup_date[0] != today:
                _last_backup_date[0] = today
                threading.Thread(target=_perform_backup, daemon=True,
                                 name='backup').start()

def is_habit_due_on_date(habit, check_date):
    local_tz = _get_localtz()
    if check_date.tzinfo is None:
        check_date = check_date.replace(tzinfo=timezone.utc)
    check_date = check_date.astimezone(local_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    created = habit.created_at if habit.created_at.tzinfo else habit.created_at.replace(tzinfo=timezone.utc)
    habit_start = created.astimezone(local_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    
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
    today = datetime.now(_get_localtz()).replace(hour=0, minute=0, second=0, microsecond=0)
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
    now = datetime.now(_get_localtz())
    check_date = last_check.astimezone(_get_localtz()).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    if check_date >= yesterday:
        user.last_penalty_check = now
        db.session.commit()
        return 
        
    habits = Habit.query.filter(
        Habit.assigned_users.any(User.id == user.id),
        Habit.penalty_enabled == True
    ).all()
    
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

def get_habit_streak(user_id, habit_id, exclude_id=None):
    """Count the current consecutive approved completion streak for a habit."""
    query = Completion.query.filter(
        Completion.user_id == user_id,
        Completion.habit_id == habit_id,
        Completion.status.in_(['approved', 'rejected', 'penalty'])
    )
    if exclude_id:
        query = query.filter(Completion.id != exclude_id)
    completions = query.order_by(Completion.timestamp.desc()).all()
    streak = 0
    for c in completions:
        if c.status == 'approved':
            streak += 1
        else:
            break
    return streak

@app.before_request
def check_setup_required():
    if current_user.is_authenticated and current_user.force_password_change:
        # Initial admin setup (default 'admin' account) → full setup page
        if current_user.email == 'admin':
            if request.endpoint in ['setup_account', 'static', 'logout']: return
            flash("Setup required: Please update your account details.", "warning")
            return redirect(url_for('setup_account'))
        # Password was reset by an admin → simple change-password page
        else:
            if request.endpoint in ['change_password', 'static', 'logout']: return
            flash("Your password has been reset. Please choose a new password.", "warning")
            return redirect(url_for('change_password'))

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
    # Avatar + coins columns
    for col_name, col_def in [
        ('coins', 'INTEGER DEFAULT 0'),
        ('avatar_body', "VARCHAR(10) DEFAULT 'male'"),
        ('avatar_role', "VARCHAR(20) DEFAULT 'knight'"),
        ('avatar_head_id', 'INTEGER'),
        ('avatar_chest_id', 'INTEGER'),
        ('avatar_weapon_id', 'INTEGER'),
        ('avatar_offhand_id', 'INTEGER'),
        ('avatar_spell_id', 'INTEGER'),
    ]:
        if col_name not in user_cols:
            cursor.execute(f"ALTER TABLE user ADD COLUMN {col_name} {col_def}")

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
        ('created_at', 'TIMESTAMP'),
        ('streak_enabled', 'BOOLEAN'),
        ('streak_milestone', 'INTEGER'),
        ('streak_multiplier', 'FLOAT'),
        ('coins_reward', 'INTEGER DEFAULT 1'),
        ('coins_streak_bonus', 'INTEGER DEFAULT 0'),
    ]
    for col_name, col_type in habit_updates:
        if col_name not in habit_cols:
            cursor.execute(f"ALTER TABLE habit ADD COLUMN {col_name} {col_type}")

    # habit_users junction table (many-to-many) — migrate from legacy assigned_user_id
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='habit_users'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE habit_users (
                habit_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (habit_id, user_id),
                FOREIGN KEY (habit_id) REFERENCES habit (id),
                FOREIGN KEY (user_id) REFERENCES user (id)
            )
        """)
    # Always migrate legacy assigned_user_id rows (idempotent via INSERT OR IGNORE)
    cursor.execute("""
        INSERT OR IGNORE INTO habit_users (habit_id, user_id)
        SELECT id, assigned_user_id FROM habit
        WHERE assigned_user_id IS NOT NULL
    """)

    # Completion Table
    cursor.execute("PRAGMA table_info(completion)")
    completion_cols = [col[1] for col in cursor.fetchall()]
    if completion_cols and 'action_token' not in completion_cols:
        cursor.execute("ALTER TABLE completion ADD COLUMN action_token VARCHAR(64)")

    # AvatarItem table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='avatar_item'")
    if not cursor.fetchone():
        cursor.execute("""CREATE TABLE avatar_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            description VARCHAR(300),
            item_type VARCHAR(20) NOT NULL,
            svg_filename VARCHAR(100) NOT NULL,
            coin_cost INTEGER DEFAULT 0,
            is_starter BOOLEAN DEFAULT 0,
            rarity VARCHAR(20) DEFAULT 'common'
        )""")

    # user_avatar_items junction table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_avatar_items'")
    if not cursor.fetchone():
        cursor.execute("""CREATE TABLE user_avatar_items (
            user_id INTEGER NOT NULL,
            avatar_item_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, avatar_item_id),
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
            FOREIGN KEY (avatar_item_id) REFERENCES avatar_item(id) ON DELETE CASCADE
        )""")

    # AppSetting Table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='app_setting'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE app_setting (
                key VARCHAR(100) NOT NULL PRIMARY KEY,
                value TEXT
            )
        """)

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
                    Habit(name="Morning Patrol (Walk the Dog)", description="Walk 15 mins", points_reward=15, assigned_users=[demo_user], schedule_type='daily'),
                    Habit(name="Potion Brewing (Drink Water)", description="8 Glasses", points_reward=10, assigned_users=[demo_user], schedule_type='daily'),
                    Habit(name="Clean the Armory (Dishes)", description="Empty sink", points_reward=25, assigned_users=[demo_user], schedule_type='weekly', schedule_days="0,2,4,6"),
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

        # Seed Avatar Items
        ALL_AVATAR_ITEMS = [
            # Head - starter
            dict(name="Iron Helm", description="A simple iron helmet. Trusty and reliable.", item_type="head", svg_filename="head_iron_helm.svg", coin_cost=0, is_starter=True, rarity="common"),
            # Head - shop
            dict(name="Royal Crown", description="A magnificent gold crown studded with gems.", item_type="head", svg_filename="head_crown.svg", coin_cost=80, is_starter=False, rarity="epic"),
            dict(name="Silver Tiara", description="An ornate silver tiara fit for royalty.", item_type="head", svg_filename="head_tiara.svg", coin_cost=60, is_starter=False, rarity="rare"),
            dict(name="Knight's Helm", description="A full-face great helm with a red plume.", item_type="head", svg_filename="head_knight_helm.svg", coin_cost=50, is_starter=False, rarity="rare"),
            dict(name="Wizard's Hat", description="A tall pointed hat adorned with stars and moons.", item_type="head", svg_filename="head_wizard_hat.svg", coin_cost=45, is_starter=False, rarity="rare"),
            dict(name="Ranger's Hood", description="A leather hood that blends into the forest.", item_type="head", svg_filename="head_ranger_hood.svg", coin_cost=35, is_starter=False, rarity="common"),
            dict(name="Dwarven Helm", description="A horned helmet with fierce glowing eye-slits.", item_type="head", svg_filename="head_dwarven_helm.svg", coin_cost=70, is_starter=False, rarity="epic"),
            # Chest - starter
            dict(name="Plain Tunic", description="A simple cloth tunic. Nothing fancy, but it'll do.", item_type="chest", svg_filename="chest_tunic.svg", coin_cost=0, is_starter=True, rarity="common"),
            # Chest - shop
            dict(name="Chainmail Hauberk", description="Interlocked iron rings offering solid protection.", item_type="chest", svg_filename="chest_chainmail.svg", coin_cost=40, is_starter=False, rarity="common"),
            dict(name="Shining Plate Armor", description="Gleaming steel plate armor with a golden emblem.", item_type="chest", svg_filename="chest_plate_armor.svg", coin_cost=100, is_starter=False, rarity="legendary"),
            dict(name="Wizard's Robe", description="A deep purple robe embroidered with arcane symbols.", item_type="chest", svg_filename="chest_robe.svg", coin_cost=55, is_starter=False, rarity="rare"),
            dict(name="Royal Tabard", description="A blue and gold tabard with a cape in royal crimson.", item_type="chest", svg_filename="chest_royal.svg", coin_cost=75, is_starter=False, rarity="epic"),
            dict(name="Leather Jerkin", description="Sturdy leather armor with buckled straps.", item_type="chest", svg_filename="chest_leather.svg", coin_cost=30, is_starter=False, rarity="common"),
            dict(name="Princess Dress", description="An elegant gown with puffed sleeves and a flowing skirt.", item_type="chest", svg_filename="chest_dress.svg", coin_cost=65, is_starter=False, rarity="rare"),
            dict(name="Dwarven Plate", description="Heavy bronze plate with a rune-engraved boss.", item_type="chest", svg_filename="chest_dwarven_armor.svg", coin_cost=90, is_starter=False, rarity="epic"),
            # Weapon - starter
            dict(name="Short Sword", description="A trusty adventurer's blade. Simple but effective.", item_type="weapon", svg_filename="weapon_sword.svg", coin_cost=0, is_starter=True, rarity="common"),
            # Weapon - shop
            dict(name="Longsword", description="A great two-handed sword for powerful strikes.", item_type="weapon", svg_filename="weapon_longsword.svg", coin_cost=60, is_starter=False, rarity="rare"),
            dict(name="Crystal Staff", description="A wooden staff topped with a glowing arcane crystal.", item_type="weapon", svg_filename="weapon_staff.svg", coin_cost=70, is_starter=False, rarity="epic"),
            dict(name="Recurve Bow", description="A nimble recurve bow with an arrow at the ready.", item_type="weapon", svg_filename="weapon_bow.svg", coin_cost=50, is_starter=False, rarity="rare"),
            dict(name="Battle Axe", description="A fearsome double-headed axe etched with runes.", item_type="weapon", svg_filename="weapon_battle_axe.svg", coin_cost=55, is_starter=False, rarity="rare"),
            dict(name="Curved Dagger", description="A quick curved dagger favored by rogues.", item_type="weapon", svg_filename="weapon_dagger.svg", coin_cost=35, is_starter=False, rarity="common"),
            dict(name="Enchanted Wand", description="A wand crackling with magical energy and sparks.", item_type="weapon", svg_filename="weapon_wand.svg", coin_cost=80, is_starter=False, rarity="epic"),
            # Offhand - starter
            dict(name="Wooden Shield", description="A sturdy round shield banded with iron.", item_type="offhand", svg_filename="offhand_wooden_shield.svg", coin_cost=0, is_starter=True, rarity="common"),
            # Offhand - shop
            dict(name="Kite Shield", description="A heraldic kite shield with a noble crest.", item_type="offhand", svg_filename="offhand_kite_shield.svg", coin_cost=65, is_starter=False, rarity="epic"),
            dict(name="Spellbook", description="An open tome filled with arcane diagrams.", item_type="offhand", svg_filename="offhand_spellbook.svg", coin_cost=55, is_starter=False, rarity="rare"),
            dict(name="Torch", description="A lit torch to light the way through dark dungeons.", item_type="offhand", svg_filename="offhand_torch.svg", coin_cost=20, is_starter=False, rarity="common"),
            dict(name="Steel Buckler", description="A small but sturdy spiked steel buckler.", item_type="offhand", svg_filename="offhand_buckler.svg", coin_cost=40, is_starter=False, rarity="common"),
            # Spell - starter
            dict(name="No Aura", description="No enchantment. Pure skill.", item_type="spell", svg_filename="spell_none.svg", coin_cost=0, is_starter=True, rarity="common"),
            # Spell - shop
            dict(name="Fire Aura", description="Wreathed in flames that lick at your feet.", item_type="spell", svg_filename="spell_fire.svg", coin_cost=75, is_starter=False, rarity="epic"),
            dict(name="Ice Aura", description="Surrounded by drifting ice crystals and frost.", item_type="spell", svg_filename="spell_ice.svg", coin_cost=75, is_starter=False, rarity="epic"),
            dict(name="Lightning Aura", description="Electric arcs crackle around your body.", item_type="spell", svg_filename="spell_lightning.svg", coin_cost=85, is_starter=False, rarity="legendary"),
            dict(name="Holy Light", description="A divine halo and golden motes of sacred light.", item_type="spell", svg_filename="spell_holy.svg", coin_cost=90, is_starter=False, rarity="legendary"),
            dict(name="Shadow Wraith", description="Dark purple wisps curl around you ominously.", item_type="spell", svg_filename="spell_shadow.svg", coin_cost=85, is_starter=False, rarity="legendary"),
        ]
        try:
            for item_data in ALL_AVATAR_ITEMS:
                if not AvatarItem.query.filter_by(svg_filename=item_data['svg_filename']).first():
                    db.session.add(AvatarItem(**item_data))
            db.session.commit()
            # Grant starters to all existing users (including demo)
            starters = AvatarItem.query.filter_by(is_starter=True).all()
            for u in User.query.all():
                for item in starters:
                    if item not in u.avatar_items:
                        u.avatar_items.append(item)
            db.session.commit()
            # Ensure demo user has default items equipped
            demo_user = User.query.filter_by(email=DEMO_EMAIL).first()
            if demo_user:
                _grant_starter_items(demo_user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

def _grant_starter_items(user):
    """Grant all is_starter AvatarItems to a user (idempotent)."""
    starters = AvatarItem.query.filter_by(is_starter=True).all()
    for item in starters:
        if item not in user.avatar_items:
            user.avatar_items.append(item)
    # Equip defaults if nothing equipped yet
    if not user.avatar_head_id:
        helm = AvatarItem.query.filter_by(svg_filename='head_iron_helm.svg').first()
        if helm:
            user.avatar_head_id = helm.id
    if not user.avatar_chest_id:
        tunic = AvatarItem.query.filter_by(svg_filename='chest_tunic.svg').first()
        if tunic:
            user.avatar_chest_id = tunic.id
    if not user.avatar_weapon_id:
        sword = AvatarItem.query.filter_by(svg_filename='weapon_sword.svg').first()
        if sword:
            user.avatar_weapon_id = sword.id
    if not user.avatar_offhand_id:
        shield = AvatarItem.query.filter_by(svg_filename='offhand_wooden_shield.svg').first()
        if shield:
            user.avatar_offhand_id = shield.id

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

@app.route('/settings/convert-to-local', methods=['POST'])
@login_required
def convert_to_local():
    if current_user.email == DEMO_EMAIL:
        flash("Settings are read-only for the Demo user.", "warning")
        return redirect(url_for('settings_profile'))
    if current_user.password_hash:
        flash("This account already has a password set.", "info")
        return redirect(url_for('settings_profile'))
    password = request.form.get('password', '').strip()
    confirm = request.form.get('confirm_password', '').strip()
    if len(password) < 4:
        flash("Password must be at least 4 characters.", "error")
        return redirect(url_for('settings_profile'))
    if password != confirm:
        flash("Passwords do not match.", "error")
        return redirect(url_for('settings_profile'))
    current_user.password_hash = generate_password_hash(password, method='scrypt')
    db.session.commit()
    flash("Password set! You can now log in with your email and password without Google.", "success")
    return redirect(url_for('settings_profile'))

@app.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def settings_profile():
    if current_user.email == DEMO_EMAIL and request.method == 'POST':
        flash("Settings are read-only for the Demo user.", "warning")
        return redirect(url_for('settings_profile'))

    if request.method == 'POST':
        name = request.form.get('name')
        theme = request.form.get('theme')
        
        if name:
            current_user.name = name
        valid_themes = {'dark', 'light', 'princess', 'forest', 'dragon', 'sorcerer', 'dwarven'}
        if theme in valid_themes:
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

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if not current_user.force_password_change: return redirect(url_for('index'))
    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()
        if len(password) < 4:
            flash('Password must be at least 4 characters.', 'error')
        elif password != confirm:
            flash('Passwords do not match.', 'error')
        else:
            current_user.password_hash = generate_password_hash(password, method='scrypt')
            current_user.force_password_change = False
            db.session.commit()
            flash('Password updated successfully.', 'success')
            return redirect(url_for('index'))
    return render_template('change_password.html')

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
        _grant_starter_items(new_user)
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
            _grant_starter_items(user)
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
    today = datetime.now(_get_localtz())
    todays_habits = []
    upcoming_habits = []

    demo_user = User.query.filter_by(email=DEMO_EMAIL).first()
    if current_user.is_admin:
        all_habits = Habit.query.all()
        completions_query = Completion.query.join(User, Completion.user_id == User.id).filter(User.email != DEMO_EMAIL)
        my_completions = completions_query.order_by(Completion.timestamp.desc()).limit(10).all()
    else:
        all_habits = Habit.query.filter(Habit.assigned_users.any(User.id == current_user.id)).all()
        my_completions = Completion.query.filter_by(user_id=current_user.id).order_by(Completion.timestamp.desc()).limit(10).all()

    is_due_today_cache = {}
    for h in all_habits:
        is_due_today_cache[h.id] = is_habit_due_on_date(h, today)
        # Determine users to show for this habit
        if current_user.is_admin:
            users_for_habit = [u for u in h.assigned_users if not demo_user or u.id != demo_user.id]
        else:
            users_for_habit = [current_user]

        for assigned_user in users_for_habit:
            entry = types.SimpleNamespace(
                id=h.id, name=h.name, description=h.description,
                points_reward=h.points_reward, assigned_user_id=assigned_user.id,
                assigned_user=assigned_user, schedule_type=h.schedule_type,
                schedule_days=h.schedule_days, interval_days=h.interval_days,
                created_at=h.created_at, penalty_enabled=h.penalty_enabled,
                penalty_amount=h.penalty_amount, streak_enabled=h.streak_enabled,
                streak_milestone=h.streak_milestone, streak_multiplier=h.streak_multiplier,
                current_streak=0, next_milestone=None,
                is_completed=False, completion_status=None, next_due_display=None,
            )
            if h.streak_enabled and h.streak_milestone:
                entry.current_streak = get_habit_streak(assigned_user.id, h.id)
                entry.next_milestone = h.streak_milestone - (entry.current_streak % h.streak_milestone)

            if is_due_today_cache[h.id]:
                start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = start_of_day + timedelta(days=1)
                done = Completion.query.filter(
                    Completion.habit_id == h.id,
                    Completion.user_id == assigned_user.id,
                    Completion.timestamp >= start_of_day,
                    Completion.timestamp < end_of_day,
                    Completion.status != 'rejected'
                ).first()
                entry.is_completed = bool(done)
                entry.completion_status = done.status if done else None
                todays_habits.append(entry)
            else:
                next_due = calculate_next_due_date(h)
                entry.next_due_display = next_due.strftime("%a, %b %d") if next_due else "Unknown"
                upcoming_habits.append(entry)

    return render_template('dashboard.html', todays_habits=todays_habits, upcoming_habits=upcoming_habits, completions=my_completions)

@app.route('/habit/<int:habit_id>/complete', methods=['POST'])
@login_required
def complete_habit(habit_id):
    if current_user.email == DEMO_EMAIL:
        flash("The Demo account is read-only. Proof upload is disabled.", "warning")
        return redirect(url_for('dashboard'))

    habit = Habit.query.get_or_404(habit_id)
    if current_user.id not in [u.id for u in habit.assigned_users]:
        flash('You are not assigned to this quest.', 'error')
        return redirect(url_for('dashboard'))
    if 'proof' not in request.files or request.files['proof'].filename == '':
        flash('Please select an image to upload.', 'warning')
        return redirect(url_for('dashboard'))
    file = request.files['proof']
    if not allowed_file(file.filename):
        flash('Invalid file type. Please upload an image (png, jpg, jpeg, gif, webp).', 'error')
        return redirect(url_for('dashboard'))
    filename = secure_filename(f"{current_user.id}_{datetime.now().timestamp()}_{file.filename}")
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    token = secrets.token_urlsafe(32)
    completion = Completion(user_id=current_user.id, habit_id=habit.id, habit_name=habit.name, image_filename=filename, status='pending', action_token=token)
    db.session.add(completion)
    db.session.commit()
    send_notification(f"📸 **{current_user.name}** quest update: **{habit.name}**! (Pending Review)", filename, completion_id=completion.id, action_token=token)
    flash('Quest submitted for review!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/calendar')
@login_required
def calendar():
    local_tz = _get_localtz()
    week_start = int(get_setting('week_start_day', '0'))  # 0=Monday, 6=Sunday
    today = datetime.now(local_tz).date()

    # Align calendar start to the configured week start day
    days_since_start = (today.weekday() - week_start) % 7
    grid_start = today - timedelta(days=days_since_start)

    # 5 weeks so today is always visible and there's plenty of look-ahead
    grid_days = [grid_start + timedelta(days=i) for i in range(35)]

    # Habits to show: admin sees all non-demo; others see their own
    demo_user = User.query.filter_by(email=DEMO_EMAIL).first()
    if current_user.is_admin:
        all_habits = Habit.query.all()
        if demo_user:
            all_habits = [h for h in all_habits
                          if not any(u.id == demo_user.id for u in h.assigned_users)]
    else:
        all_habits = Habit.query.filter(
            Habit.assigned_users.any(User.id == current_user.id)
        ).all()

    # Build {date: [habit, ...]} mapping
    calendar_data = {}
    for day in grid_days:
        day_dt = datetime.combine(day, datetime.min.time()).replace(tzinfo=local_tz)
        calendar_data[day] = [h for h in all_habits if is_habit_due_on_date(h, day_dt)]

    # Group into weeks for the template
    weeks = [grid_days[i:i + 7] for i in range(0, 35, 7)]

    # Day-of-week header labels starting from the configured week start
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    # week_start=0 → Mon first; week_start=6 → Sun first
    ordered = day_names[week_start:] + day_names[:week_start]

    return render_template('calendar.html',
                           weeks=weeks,
                           calendar_data=calendar_data,
                           today=today,
                           day_names=ordered)

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
    
    send_notification(f"💡 **{current_user.name}** requested a new reward: **{name}** ({cost} Gems).")
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
        send_notification(f"🎁 **{current_user.name}** claimed **{reward.name}**!")
        flash('Reward Claimed!', 'success')
    else: flash('Not enough Gems.', 'error')
    return redirect(url_for('rewards'))

# --- ADMIN ROUTES ---

@app.route('/admin/test-webhook', methods=['POST'])
@login_required
def test_webhook():
    if not current_user.is_admin: return redirect(url_for('index'))
    ap = _build_apprise()
    if not len(ap):
        flash('No notification services configured. Set APPRISE_URLS or DISCORD_WEBHOOK_URL.', 'error')
    else:
        send_notification("🔔 Quest Log test notification — working!")
        flash('Test notification sent. Check your configured channels.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    
    # Filter: Hide pending quests from the Demo User
    pending = Completion.query.join(User).filter(Completion.status == 'pending', User.email != DEMO_EMAIL).all()
    
    # Filter: Hide Demo User from assignment list
    users = User.query.filter(User.email != DEMO_EMAIL).all()
    
    # Filter: Hide Demo User's quests from admin panel
    demo_user = User.query.filter_by(email=DEMO_EMAIL).first()
    if demo_user:
        habits = Habit.query.filter(~Habit.assigned_users.any(User.id == demo_user.id)).all()
    else:
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
    
    notification_icon_url = get_setting('notification_icon_url', '')
    apprise_urls_setting = get_setting('apprise_urls', '')
    discord_webhook_setting = get_setting('discord_webhook_url', '')
    week_start_day = get_setting('week_start_day', '0')
    avatar_items = AvatarItem.query.order_by(AvatarItem.item_type, AvatarItem.coin_cost).all()
    return render_template('admin.html',
                         pending=pending,
                         users=users,
                         habits=habits,
                         pending_rewards=pending_rewards,
                         active_rewards=active_rewards,
                         notification_icon_url=notification_icon_url,
                         apprise_urls_setting=apprise_urls_setting,
                         discord_webhook_setting=discord_webhook_setting,
                         week_start_day=week_start_day,
                         avatar_items=avatar_items)

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

@app.route('/admin/user/delete', methods=['POST'])
@login_required
def delete_user():
    if not current_user.is_admin: return redirect(url_for('index'))
    user_id = request.form.get('user_id')
    user = db.session.get(User, int(user_id))
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin_panel'))
    if user.email == DEMO_EMAIL:
        flash('Cannot delete the Demo user.', 'error')
        return redirect(url_for('admin_panel'))
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin_panel'))
    # Delete completions, remove from habit assignments, then delete user
    Completion.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    user.assigned_habits.clear()
    db.session.delete(user)
    db.session.commit()
    flash(f'Adventurer "{user.name}" has been removed from the guild.', 'info')
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
        _grant_starter_items(new_user)
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

@app.route('/admin/user/reset-password', methods=['POST'])
@login_required
def reset_user_password():
    if not current_user.is_admin: return redirect(url_for('index'))
    user_id = request.form.get('user_id')
    new_password = request.form.get('new_password', '').strip()
    if len(new_password) < 4:
        flash('Password must be at least 4 characters.', 'error')
        return redirect(url_for('admin_panel'))
    user = db.session.get(User, int(user_id))
    if not user or user.email == DEMO_EMAIL:
        flash('User not found.', 'error')
        return redirect(url_for('admin_panel'))
    user.password_hash = generate_password_hash(new_password, method='scrypt')
    user.force_password_change = True
    db.session.commit()
    flash(f'Password reset for {user.name}. They will be prompted to change it on next login.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/user/adjust-gems', methods=['POST'])
@login_required
def adjust_gems():
    if not current_user.is_admin: return redirect(url_for('index'))
    user_id = request.form.get('user_id')
    try:
        amount = int(request.form.get('amount', 0))
    except (TypeError, ValueError):
        flash('Invalid gem amount.', 'error')
        return redirect(url_for('admin_panel'))
    if amount == 0:
        flash('Amount cannot be zero.', 'error')
        return redirect(url_for('admin_panel'))
    user = db.session.get(User, int(user_id))
    if not user or user.email == DEMO_EMAIL:
        flash('User not found.', 'error')
        return redirect(url_for('admin_panel'))
    user.points += amount
    if user.points < 0:
        user.points = 0
    db.session.commit()
    action = f"+{amount}" if amount > 0 else str(amount)
    flash(f'{action} gems applied to {user.name}. New total: {user.points} gems.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/habit/create', methods=['POST'])
@login_required
def create_habit():
    if not current_user.is_admin: return redirect(url_for('index'))
    name = request.form.get('name')
    description = request.form.get('description')
    points = int(request.form.get('points'))
    user_ids = request.form.getlist('assigned_user_ids')
    if not user_ids:
        flash('Please assign at least one adventurer.', 'error')
        return redirect(url_for('admin_panel'))
    assigned_users = User.query.filter(User.id.in_(user_ids)).all()
    schedule_type = request.form.get('schedule_type')
    schedule_days = ",".join(request.form.getlist('days')) if schedule_type in ['weekly', 'biweekly'] else None
    interval_days = int(request.form.get('interval_days')) if schedule_type == 'interval' else None
    penalty_enabled = 'penalty_enabled' in request.form
    penalty_amount = int(request.form.get('penalty_amount') or 0)
    streak_enabled = 'streak_enabled' in request.form
    streak_milestone = int(request.form.get('streak_milestone') or 5)
    streak_multiplier = float(request.form.get('streak_multiplier') or 2.0)
    coins_reward = int(request.form.get('coins_reward') or 1)
    coins_streak_bonus = int(request.form.get('coins_streak_bonus') or 0)

    new_habit = Habit(
        name=name, description=description, points_reward=points,
        schedule_type=schedule_type, schedule_days=schedule_days,
        interval_days=interval_days, penalty_enabled=penalty_enabled, penalty_amount=penalty_amount,
        streak_enabled=streak_enabled, streak_milestone=streak_milestone, streak_multiplier=streak_multiplier,
        coins_reward=coins_reward, coins_streak_bonus=coins_streak_bonus,
        assigned_users=assigned_users
    )
    db.session.add(new_habit)
    db.session.commit()
    flash('Quest assigned!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/habit/edit/<int:habit_id>', methods=['GET', 'POST'])
@login_required
def edit_habit(habit_id):
    if not current_user.is_admin: return redirect(url_for('index'))
    habit = Habit.query.get_or_404(habit_id)
    demo_user = User.query.filter_by(email=DEMO_EMAIL).first()
    users = User.query.filter(User.email != DEMO_EMAIL).all()

    if request.method == 'POST':
        user_ids = request.form.getlist('assigned_user_ids')
        if not user_ids:
            flash('Please assign at least one adventurer.', 'error')
            return render_template('edit_habit.html', habit=habit, users=users)
        habit.name = request.form.get('name')
        habit.description = request.form.get('description')
        habit.points_reward = int(request.form.get('points'))
        habit.assigned_users = User.query.filter(User.id.in_(user_ids)).all()
        schedule_type = request.form.get('schedule_type')
        habit.schedule_type = schedule_type
        habit.schedule_days = ",".join(request.form.getlist('days')) if schedule_type in ['weekly', 'biweekly'] else None
        habit.interval_days = int(request.form.get('interval_days')) if schedule_type == 'interval' else None
        habit.penalty_enabled = 'penalty_enabled' in request.form
        habit.penalty_amount = int(request.form.get('penalty_amount') or 0)
        habit.coins_reward = int(request.form.get('coins_reward') or 1)
        habit.coins_streak_bonus = int(request.form.get('coins_streak_bonus') or 0)
        db.session.commit()
        flash('Quest updated!', 'success')
        return redirect(url_for('admin_panel'))

    return render_template('edit_habit.html', habit=habit, users=users)

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
        if habit:
            points = habit.points_reward
            coins_earned = habit.coins_reward if habit.coins_reward else 1
            bonus_msg = ""
            if habit.streak_enabled and habit.streak_milestone:
                prev_streak = get_habit_streak(user.id, habit.id, exclude_id=completion.id)
                new_streak = prev_streak + 1
                if new_streak % habit.streak_milestone == 0:
                    points = int(points * habit.streak_multiplier)
                    coins_earned += habit.coins_streak_bonus if habit.coins_streak_bonus else 0
                    bonus_msg = f" 🔥 **{new_streak}-quest streak! {habit.streak_multiplier}x gem bonus!**"
            user.points += points
            user.coins += coins_earned
        db.session.commit()
        send_notification(f"✅ **{user.name}** completed **{completion.habit_name}**! (Approved){bonus_msg}", completion.image_filename)
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

@app.route('/quest/approve/<int:completion_id>/<token>')
def quick_approve(completion_id, token):
    """Token-based approval link — no login required (used in Discord/notification links)."""
    completion = Completion.query.get_or_404(completion_id)
    if not token or completion.action_token != token:
        return "Invalid or expired approval link.", 403
    if completion.status != 'pending':
        return f"Quest already {completion.status}.", 200
    user = db.session.get(User, completion.user_id)
    if not user or user.email == DEMO_EMAIL:
        return "Cannot approve this quest.", 403
    completion.status = 'approved'
    habit = db.session.get(Habit, completion.habit_id)
    bonus_msg = ""
    if habit:
        points = habit.points_reward
        coins_earned = habit.coins_reward if habit.coins_reward else 1
        if habit.streak_enabled and habit.streak_milestone:
            prev_streak = get_habit_streak(user.id, habit.id, exclude_id=completion.id)
            new_streak = prev_streak + 1
            if new_streak % habit.streak_milestone == 0:
                points = int(points * habit.streak_multiplier)
                coins_earned += habit.coins_streak_bonus if habit.coins_streak_bonus else 0
                bonus_msg = f" 🔥 {new_streak}-quest streak! {habit.streak_multiplier}x gem bonus!"
        user.points += points
        user.coins += coins_earned
    completion.action_token = None  # invalidate token
    db.session.commit()
    send_notification(f"✅ **{user.name}** completed **{completion.habit_name}**! (Approved via link){bonus_msg}", completion.image_filename)
    return f"<html><body style='font-family:sans-serif;text-align:center;padding:2rem'><h2>✅ Quest Approved!</h2><p><strong>{user.name}</strong> — <em>{completion.habit_name}</em></p><p>Gems awarded.{bonus_msg}</p></body></html>", 200

@app.route('/quest/reject/<int:completion_id>/<token>')
def quick_reject(completion_id, token):
    """Token-based rejection link — no login required (used in Discord/notification links)."""
    completion = Completion.query.get_or_404(completion_id)
    if not token or completion.action_token != token:
        return "Invalid or expired rejection link.", 403
    if completion.status != 'pending':
        return f"Quest already {completion.status}.", 200
    user = db.session.get(User, completion.user_id)
    if not user or user.email == DEMO_EMAIL:
        return "Cannot reject this quest.", 403
    completion.status = 'rejected'
    completion.action_token = None  # invalidate token
    db.session.commit()
    return f"<html><body style='font-family:sans-serif;text-align:center;padding:2rem'><h2>❌ Quest Rejected</h2><p><strong>{user.name}</strong> — <em>{completion.habit_name}</em></p></body></html>", 200

@app.route('/admin/settings/notification', methods=['POST'])
@login_required
def admin_notification_settings():
    if not current_user.is_admin: return redirect(url_for('index'))
    icon_url = request.form.get('notification_icon_url', '').strip()
    set_setting('notification_icon_url', icon_url)
    flash('Notification settings saved.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/settings/general', methods=['POST'])
@login_required
def admin_general_settings():
    if not current_user.is_admin: return redirect(url_for('index'))
    set_setting('apprise_urls', request.form.get('apprise_urls', '').strip())
    set_setting('discord_webhook_url', request.form.get('discord_webhook_url', '').strip())
    week_start = request.form.get('week_start_day', '0')
    if week_start not in ('0', '6'):
        week_start = '0'
    set_setting('week_start_day', week_start)
    flash('General settings saved.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/cleanup-rejected-images', methods=['POST'])
@login_required
def cleanup_rejected_images():
    if not current_user.is_admin: return redirect(url_for('index'))
    rejected = Completion.query.filter_by(status='rejected').all()
    file_count = 0
    entry_count = len(rejected)
    for c in rejected:
        if c.image_filename:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], c.image_filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    file_count += 1
                except OSError as e:
                    logger.warning("Could not delete %s: %s", file_path, e)
    Completion.query.filter_by(status='rejected').delete(synchronize_session=False)
    db.session.commit()
    flash(f'Removed {entry_count} rejected log entr{"y" if entry_count == 1 else "ies"} and {file_count} image file(s).', 'success')
    return redirect(url_for('admin_panel'))

AVATAR_ROLES = {
    'knight': 'Knight',
    'prince': 'Prince',
    'princess': 'Princess',
    'king': 'King',
    'queen': 'Queen',
    'ranger': 'Ranger',
    'wizard': 'Wizard',
}

RARITY_COLORS = {
    'common': 'text-gray-400',
    'rare': 'text-blue-400',
    'epic': 'text-purple-400',
    'legendary': 'text-yellow-400',
}

@app.route('/avatar')
@login_required
def avatar():
    owned_ids = {item.id for item in current_user.avatar_items}
    items_by_type = {}
    for slot in ['head', 'chest', 'weapon', 'offhand', 'spell']:
        items_by_type[slot] = AvatarItem.query.filter_by(item_type=slot).order_by(AvatarItem.coin_cost).all()
    equipped = {
        'head': db.session.get(AvatarItem, current_user.avatar_head_id),
        'chest': db.session.get(AvatarItem, current_user.avatar_chest_id),
        'weapon': db.session.get(AvatarItem, current_user.avatar_weapon_id),
        'offhand': db.session.get(AvatarItem, current_user.avatar_offhand_id),
        'spell': db.session.get(AvatarItem, current_user.avatar_spell_id),
    }
    return render_template('avatar.html', items_by_type=items_by_type, owned_ids=owned_ids,
                           equipped=equipped, roles=AVATAR_ROLES, rarity_colors=RARITY_COLORS)

@app.route('/avatar/save', methods=['POST'])
@login_required
def avatar_save():
    if current_user.email == DEMO_EMAIL:
        flash("The Demo account cannot save an avatar.", "warning")
        return redirect(url_for('avatar'))
    current_user.avatar_body = request.form.get('avatar_body', 'male')
    role = request.form.get('avatar_role', 'knight')
    if role in AVATAR_ROLES:
        current_user.avatar_role = role
    owned_ids = {item.id for item in current_user.avatar_items}
    for slot in ['head', 'chest', 'weapon', 'offhand', 'spell']:
        raw = request.form.get(f'avatar_{slot}_id', '')
        if raw.isdigit():
            item_id = int(raw)
            if item_id in owned_ids:
                setattr(current_user, f'avatar_{slot}_id', item_id)
            else:
                setattr(current_user, f'avatar_{slot}_id', None)
        else:
            setattr(current_user, f'avatar_{slot}_id', None)
    db.session.commit()
    flash("Avatar saved!", "success")
    return redirect(url_for('avatar'))

@app.route('/avatar/shop')
@login_required
def avatar_shop():
    owned_ids = {item.id for item in current_user.avatar_items}
    all_items = AvatarItem.query.order_by(AvatarItem.item_type, AvatarItem.coin_cost).all()
    return render_template('avatar_shop.html', items=all_items, owned_ids=owned_ids,
                           rarity_colors=RARITY_COLORS)

@app.route('/avatar/shop/buy/<int:item_id>', methods=['POST'])
@login_required
def avatar_shop_buy(item_id):
    if current_user.email == DEMO_EMAIL:
        flash("The Demo account cannot purchase items.", "warning")
        return redirect(url_for('avatar_shop'))
    item = AvatarItem.query.get_or_404(item_id)
    if item in current_user.avatar_items:
        flash(f"You already own {item.name}.", "info")
    elif current_user.coins < item.coin_cost:
        flash(f"Not enough coins. You need {item.coin_cost - current_user.coins} more.", "warning")
    else:
        current_user.coins -= item.coin_cost
        current_user.avatar_items.append(item)
        db.session.commit()
        flash(f"Purchased {item.name}! Head to your Avatar to equip it.", "success")
    return redirect(url_for('avatar_shop'))

@app.route('/admin/avatar/item/create', methods=['POST'])
@login_required
def admin_avatar_item_create():
    if not current_user.is_admin: return redirect(url_for('index'))
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    item_type = request.form.get('item_type', '')
    svg_filename = request.form.get('svg_filename', '').strip()
    coin_cost = int(request.form.get('coin_cost') or 0)
    rarity = request.form.get('rarity', 'common')
    is_starter = 'is_starter' in request.form
    if not name or item_type not in ['head', 'chest', 'weapon', 'offhand', 'spell'] or not svg_filename:
        flash('Name, type, and SVG filename are required.', 'error')
        return redirect(url_for('admin_panel'))
    db.session.add(AvatarItem(name=name, description=description, item_type=item_type,
                              svg_filename=svg_filename, coin_cost=coin_cost,
                              rarity=rarity, is_starter=is_starter))
    db.session.commit()
    flash(f'Avatar item "{name}" created.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/avatar/item/delete/<int:item_id>', methods=['POST'])
@login_required
def admin_avatar_item_delete(item_id):
    if not current_user.is_admin: return redirect(url_for('index'))
    item = AvatarItem.query.get_or_404(item_id)
    if item.is_starter:
        flash('Cannot delete a starter item.', 'error')
        return redirect(url_for('admin_panel'))
    db.session.delete(item)
    db.session.commit()
    flash(f'Avatar item "{item.name}" deleted.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/user/adjust-coins', methods=['POST'])
@login_required
def adjust_coins():
    if not current_user.is_admin: return redirect(url_for('index'))
    user_id = request.form.get('user_id')
    try:
        amount = int(request.form.get('amount', 0))
    except (TypeError, ValueError):
        flash('Invalid coin amount.', 'error')
        return redirect(url_for('admin_panel'))
    if amount == 0:
        flash('Amount cannot be zero.', 'error')
        return redirect(url_for('admin_panel'))
    user = db.session.get(User, int(user_id))
    if not user or user.email == DEMO_EMAIL:
        flash('User not found.', 'error')
        return redirect(url_for('admin_panel'))
    user.coins += amount
    if user.coins < 0:
        user.coins = 0
    db.session.commit()
    action = f"+{amount}" if amount > 0 else str(amount)
    flash(f'{action} coins applied to {user.name}. New total: {user.coins} coins.', 'success')
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
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)
