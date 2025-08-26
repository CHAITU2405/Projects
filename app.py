from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
import os
import json
import csv
from io import StringIO
from sqlalchemy import text

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///exam.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)  # For students only
    role = db.Column(db.String(20), nullable=False)  # Only 'student' is used
    domain = db.Column(db.String(20), nullable=True)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(20), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_answer = db.Column(db.String(10), nullable=True)  # e.g., 'A' or 'A,B' for multi
    question_type = db.Column(db.String(20), default='mcq_single')  # mcq_single, mcq_multi, short_text
    correct_answer_text = db.Column(db.Text, nullable=True)  # for short_text, pipe-separated acceptable answers
    points = db.Column(db.Float, default=1.0)
    partial_credit = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    domain = db.Column(db.String(20), nullable=False)
    is_visible = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExamQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    display_order = db.Column(db.Integer, default=0)

class ExamRetakePermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    remaining_attempts = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExamSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    domain = db.Column(db.String(20), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    score = db.Column(db.Float, default=0.0)
    total_questions = db.Column(db.Integer, default=0)

class ExamResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_session_id = db.Column(db.Integer, db.ForeignKey('exam_session.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    user_answer = db.Column(db.Text, nullable=False)  # allow multi or text
    is_correct = db.Column(db.Boolean, default=False)
    awarded_points = db.Column(db.Float, default=0.0)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, role='student').first()
        if user and user.password_hash == password:
            if not user.is_approved:
                flash('Your account is pending approval by admin.', 'error')
                return redirect(url_for('login'))
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid student username or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = (request.form.get('password') or '').strip()
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('register'))
        existing = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing:
            flash('Username or email already exists.', 'error')
            return redirect(url_for('register'))
        new_user = User(
            username=username,
            email=email,
            password_hash=password,
            role='student',
            domain=None,
            is_approved=False
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Registration submitted. Await admin approval to log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# REMOVE old student-auth based admin routes (dashboard, questions, results)
# (They were previously defined with @login_required and current_user checks.)

# Session-based admin results route
@app.route('/admin/results')
def admin_results():
    if not session.get('admin_user'):
        flash('Please log in as admin.', 'error')
        return redirect(url_for('admin_login'))
    admins = load_admins()
    admin_info = next((a for a in admins if a.get('username') == session.get('admin_user')), None)
    if not admin_info:
        session.pop('admin_user', None)
        session.pop('admin_domains', None)
        flash('Admin account not found. Please log in again.', 'error')
        return redirect(url_for('admin_login'))
    all_domains = ['web_dev', 'ml', 'data_science']
    admin_domains = admin_info.get('domain', [])
    if isinstance(admin_domains, str):
        if admin_domains == 'all':
            allowed_domains = all_domains
        else:
            allowed_domains = [admin_domains]
    else:
        allowed_domains = admin_domains if admin_domains else all_domains
    # Determine if this is a super admin (can see all domains)
    if isinstance(admin_domains, str):
        is_super_admin = admin_domains == 'all'
    else:
        is_super_admin = False
    # Show list of exams first (conducted in allowed domains)
    exams = Exam.query.filter(Exam.domain.in_(allowed_domains)).order_by(Exam.created_at.desc()).all()
    exams_with_counts = []
    for e in exams:
        count = ExamSession.query.filter_by(exam_id=e.id, is_completed=True).count()
        exams_with_counts.append({'exam': e, 'completed_count': count})
    return render_template('admin_results_exams.html', exams_with_counts=exams_with_counts)

@app.route('/admin/results/exam/<int:exam_id>')
def admin_results_exam(exam_id):
    if not session.get('admin_user'):
        flash('Please log in as admin.', 'error')
        return redirect(url_for('admin_login'))
    admins = load_admins()
    admin_info = next((a for a in admins if a.get('username') == session.get('admin_user')), None)
    if not admin_info:
        session.pop('admin_user', None)
        session.pop('admin_domains', None)
        flash('Admin account not found. Please log in again.', 'error')
        return redirect(url_for('admin_login'))
    all_domains = ['web_dev', 'ml', 'data_science']
    admin_domains = admin_info.get('domain', [])
    if isinstance(admin_domains, str):
        if admin_domains == 'all':
            allowed_domains = all_domains
        else:
            allowed_domains = [admin_domains]
    else:
        allowed_domains = admin_domains if admin_domains else all_domains
    exam = Exam.query.get_or_404(exam_id)
    if exam.domain not in allowed_domains:
        flash('You are not allowed to view results for this exam.', 'error')
        return redirect(url_for('admin_results'))
    exam_sessions = ExamSession.query.filter(
        ExamSession.is_completed == True,
        ExamSession.exam_id == exam.id
    ).all()
    # Only super admin sees domain performance; domain admins see score distribution only
    if isinstance(admin_domains, str):
        is_super_admin = admin_domains == 'all'
    else:
        is_super_admin = False
    unique_students_count = len({s.user_id for s in exam_sessions})
    def domain_avg_percent(domain: str) -> float:
        domain_sessions = [s for s in exam_sessions if s.domain == domain and (s.total_questions or 0) > 0]
        if not domain_sessions:
            return 0.0
        total_correct = sum(s.score or 0 for s in domain_sessions)
        total_questions = sum(s.total_questions or 0 for s in domain_sessions)
        if total_questions <= 0:
            return 0.0
        return round((total_correct / total_questions) * 100.0, 1)
    avg_percentages = {
        'web_dev': domain_avg_percent('web_dev'),
        'ml': domain_avg_percent('ml'),
        'data_science': domain_avg_percent('data_science'),
    }
    excellent = 0
    good = 0
    fair = 0
    poor = 0
    for s in exam_sessions:
        tq = s.total_questions or 0
        if tq <= 0:
            continue
        pct = (float(s.score or 0) / float(tq)) * 100.0
        if pct >= 90:
            excellent += 1
        elif pct >= 70:
            good += 1
        elif pct >= 50:
            fair += 1
        else:
            poor += 1
    distribution = {
        'excellent': excellent,
        'good': good,
        'fair': fair,
        'poor': poor,
    }
    # Build student list for retake controls (unique students)
    student_ids = sorted({s.user_id for s in exam_sessions})
    students = [User.query.get(uid) for uid in student_ids]
    retake_map = {p.user_id: p for p in ExamRetakePermission.query.filter_by(exam_id=exam.id).all()}
    return render_template('admin_results.html', exam_sessions=exam_sessions, unique_students_count=unique_students_count, avg_percentages=avg_percentages, distribution=distribution, exam=exam, show_domain_performance=is_super_admin, students=students, retake_map=retake_map)

@app.route('/admin/exam/<int:exam_id>/retake', methods=['POST'])
def admin_grant_retake(exam_id):
    if not session.get('admin_user'):
        flash('Please log in as admin.', 'error')
        return redirect(url_for('admin_login'))
    admins = load_admins()
    admin_info = next((a for a in admins if a.get('username') == session.get('admin_user')), None)
    if not admin_info:
        flash('Admin account not found.', 'error')
        return redirect(url_for('admin_login'))
    exam = Exam.query.get_or_404(exam_id)
    user_id = int(request.form.get('user_id'))
    attempts = int(request.form.get('attempts') or '1')
    # Upsert permission
    perm = ExamRetakePermission.query.filter_by(user_id=user_id, exam_id=exam.id).first()
    if perm:
        perm.remaining_attempts = attempts
    else:
        perm = ExamRetakePermission(user_id=user_id, exam_id=exam.id, remaining_attempts=attempts)
        db.session.add(perm)
    db.session.commit()
    flash('Retake permission updated.', 'success')
    return redirect(url_for('admin_results_exam', exam_id=exam.id))

@app.route('/api/exam_time/<int:session_id>')
@login_required
def exam_time(session_id):
    exam_session = ExamSession.query.get_or_404(session_id)
    
    if exam_session.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    now = datetime.utcnow()
    time_remaining = (exam_session.end_time - now).total_seconds()
    
    if time_remaining <= 0:
        return jsonify({'time_expired': True})
    
    return jsonify({
        'time_remaining': int(time_remaining),
        'end_time': exam_session.end_time.isoformat()
    })

# Admin JSON-based authentication and management
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admins = load_admins()
        admin = next((a for a in admins if a.get('username') == username and a.get('password') == password), None)
        if admin:
            session.permanent = True
            session['admin_user'] = admin.get('username')
            session['admin_domains'] = admin.get('domain')
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard_json'))
        else:
            flash('Invalid admin username or password', 'error')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_user', None)
    session.pop('admin_domains', None)
    flash('Admin logged out.', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard_json')
def admin_dashboard_json():
    if not session.get('admin_user'):
        flash('Please log in as admin.', 'error')
        return redirect(url_for('admin_login'))
    admins = load_admins()
    admin_info = next((a for a in admins if a.get('username') == session.get('admin_user')), None)
    if not admin_info:
        session.pop('admin_user', None)
        session.pop('admin_domains', None)
        flash('Admin account not found. Please log in again.', 'error')
        return redirect(url_for('admin_login'))
    all_domains = ['web_dev', 'ml', 'data_science']
    admin_domains = admin_info.get('domain', [])
    if isinstance(admin_domains, str):
        if admin_domains == 'all':
            allowed_domains = all_domains
        else:
            allowed_domains = [admin_domains]
    else:
        allowed_domains = admin_domains if admin_domains else all_domains
    return render_template('admin_dashboard.html', domains=allowed_domains, admin_info=admin_info)

@app.route('/admin/questions/<domain>')
def admin_questions(domain):
    if not session.get('admin_user'):
        flash('Please log in as admin.', 'error')
        return redirect(url_for('admin_login'))
    admins = load_admins()
    admin_info = next((a for a in admins if a.get('username') == session.get('admin_user')), None)
    if not admin_info:
        session.pop('admin_user', None)
        session.pop('admin_domains', None)
        flash('Admin account not found. Please log in again.', 'error')
        return redirect(url_for('admin_login'))
    all_domains = ['web_dev', 'ml', 'data_science']
    admin_domains = admin_info.get('domain', [])
    if isinstance(admin_domains, str):
        if admin_domains == 'all':
            allowed_domains = all_domains
        else:
            allowed_domains = [admin_domains]
    else:
        allowed_domains = admin_domains if admin_domains else all_domains
    if domain not in allowed_domains:
        flash('You are not allowed to view questions for this domain.', 'error')
        return redirect(url_for('admin_dashboard_json'))
    questions = Question.query.filter_by(domain=domain).all()
    return render_template('admin_questions.html', questions=questions, domain=domain)

@app.route('/admin/add_question', methods=['GET', 'POST'])
def add_question():
    if not session.get('admin_user'):
        flash('Please log in as admin.', 'error')
        return redirect(url_for('admin_login'))
    admins = load_admins()
    admin_info = next((a for a in admins if a.get('username') == session.get('admin_user')), None)
    if not admin_info:
        session.pop('admin_user', None)
        session.pop('admin_domains', None)
        flash('Admin account not found. Please log in again.', 'error')
        return redirect(url_for('admin_login'))
    all_domains = ['web_dev', 'ml', 'data_science']
    admin_domains = admin_info.get('domain', [])
    if isinstance(admin_domains, str):
        if admin_domains == 'all':
            allowed_domains = all_domains
        else:
            allowed_domains = [admin_domains]
    else:
        allowed_domains = admin_domains if admin_domains else all_domains
    if request.method == 'POST':
        if request.form['domain'] not in allowed_domains:
            flash('You are not allowed to add questions for this domain.', 'error')
            return redirect(url_for('add_question'))
        q_type = request.form.get('question_type', 'mcq_single')
        points = float(request.form.get('points', '1') or 1)
        partial_credit = request.form.get('partial_credit', '1') == '1'
        if q_type == 'short_text':
            correct_text = (request.form.get('correct_answer_text') or '').strip()
            # Use empty string to satisfy existing NOT NULL constraints on some DBs
            correct_ans = ''
            option_a = ''
            option_b = ''
            option_c = ''
            option_d = ''
        else:
            correct_ans = request.form.get('correct_answer_joined') or request.form.get('correct_answer')
            correct_text = None
            option_a = request.form.get('option_a', '').strip()
            option_b = request.form.get('option_b', '').strip()
            option_c = request.form.get('option_c', '').strip()
            option_d = request.form.get('option_d', '').strip()
        question = Question(
            domain=request.form['domain'],
            question_text=request.form['question_text'],
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_answer=correct_ans,
            question_type=q_type,
            correct_answer_text=correct_text,
            points=points,
            partial_credit=partial_credit
        )
        db.session.add(question)
        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('admin_questions', domain=request.form['domain']))
    return render_template('add_question.html', domains=allowed_domains)

@app.route('/admin/manage_admins', methods=['GET', 'POST'])
def manage_admins():
    if 'admin_user' not in session:
        flash('Please log in as admin.', 'error')
        return redirect(url_for('admin_login'))
    admins = load_admins()
    all_domains = ['web_dev', 'ml', 'data_science']
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            domains = request.form.getlist('domains')
            if not domains:
                domains = [request.form.get('domain', 'all')]
            if any(a['username'] == username or a['email'] == email for a in admins):
                flash('Admin with this username or email already exists.', 'error')
            else:
                new_admin = {
                    'username': username,
                    'email': email,
                    'password': password,
                    'role': 'admin',
                    'domain': domains if len(domains) > 1 or domains[0] != 'all' else 'all',
                    'created_at': datetime.utcnow().isoformat()
                }
                admins.append(new_admin)
                save_admins(admins)
                flash('Admin added successfully!', 'success')
        elif action == 'remove':
            username = request.form['username']
            admins = [a for a in admins if a['username'] != username]
            save_admins(admins)
            flash('Admin removed successfully!', 'success')
        elif action == 'edit':
            original_username = request.form.get('original_username')
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password') or None
            domains_raw = request.form.getlist('domains') or []
            if not domains_raw:
                domains_raw = [request.form.get('domains')]
            if 'all' in domains_raw:
                new_domain = 'all'
            else:
                new_domain = domains_raw
            updated = False
            for a in admins:
                if a['username'] == original_username:
                    a['username'] = username
                    a['email'] = email
                    if password:
                        a['password'] = password
                    a['domain'] = new_domain
                    updated = True
                    break
            if updated:
                save_admins(admins)
                flash('Admin updated successfully!', 'success')
            else:
                flash('Admin not found.', 'error')
    return render_template('manage_admins.html', admins=admins, all_domains=all_domains)

@app.route('/admin/pending_students', methods=['GET', 'POST'])
def pending_students():
    if 'admin_user' not in session:
        flash('Please log in as admin.', 'error')
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        action = request.form.get('action')
        uid = request.form.get('user_id')
        user = User.query.get(uid)
        if not user:
            flash('Student not found.', 'error')
            return redirect(url_for('pending_students'))
        if action == 'approve':
            user.is_approved = True
            db.session.commit()
            flash('Student approved.', 'success')
        elif action == 'reject':
            db.session.delete(user)
            db.session.commit()
            flash('Student rejected and removed.', 'success')
        return redirect(url_for('pending_students'))
    pending = User.query.filter_by(role='student', is_approved=False).all()
    return render_template('pending_students.html', pending=pending)

@app.route('/admin/question/<int:question_id>/edit', methods=['GET', 'POST'])
def edit_question(question_id):
    if not session.get('admin_user'):
        flash('Please log in as admin.', 'error')
        return redirect(url_for('admin_login'))
    admins = load_admins()
    admin_info = next((a for a in admins if a.get('username') == session.get('admin_user')), None)
    if not admin_info:
        flash('Admin account not found.', 'error')
        return redirect(url_for('admin_login'))
    question = Question.query.get_or_404(question_id)
    # Domain restriction
    allowed = admin_info.get('domain', 'all')
    if isinstance(allowed, str):
        if allowed != 'all' and question.domain != allowed:
            flash('Not allowed to edit this question.', 'error')
            return redirect(url_for('admin_questions', domain=question.domain))
    else:
        if allowed and question.domain not in allowed:
            flash('Not allowed to edit this question.', 'error')
            return redirect(url_for('admin_questions', domain=question.domain))
    if request.method == 'POST':
        question.question_text = request.form['question_text']
        q_type = request.form.get('question_type', question.question_type or 'mcq_single')
        question.question_type = q_type
        question.points = float(request.form.get('points', question.points or 1) or 1)
        question.partial_credit = request.form.get('partial_credit', '1') == '1'
        if q_type == 'short_text':
            question.correct_answer_text = (request.form.get('correct_answer_text') or '').strip()
            question.correct_answer = ''
            question.option_a = ''
            question.option_b = ''
            question.option_c = ''
            question.option_d = ''
        else:
            question.correct_answer = request.form.get('correct_answer_joined') or request.form.get('correct_answer')
            question.correct_answer_text = None
            question.option_a = request.form.get('option_a', '')
            question.option_b = request.form.get('option_b', '')
            question.option_c = request.form.get('option_c', '')
            question.option_d = request.form.get('option_d', '')
        db.session.commit()
        flash('Question updated.', 'success')
        return redirect(url_for('admin_questions', domain=question.domain))
    return render_template('edit_question.html', question=question)

@app.route('/admin/question/<int:question_id>/delete', methods=['POST'])
def delete_question(question_id):
    if not session.get('admin_user'):
        return redirect(url_for('admin_login'))
    admins = load_admins()
    admin_info = next((a for a in admins if a.get('username') == session.get('admin_user')), None)
    question = Question.query.get_or_404(question_id)
    allowed = admin_info.get('domain', 'all') if admin_info else 'all'
    if isinstance(allowed, str):
        if allowed != 'all' and question.domain != allowed:
            flash('Not allowed to delete this question.', 'error')
            return redirect(url_for('admin_questions', domain=question.domain))
    else:
        if allowed and question.domain not in allowed:
            flash('Not allowed to delete this question.', 'error')
            return redirect(url_for('admin_questions', domain=question.domain))
    domain = question.domain
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted.', 'success')
    return redirect(url_for('admin_questions', domain=domain))

# Path for admin JSON file
ADMIN_JSON_PATH = os.path.join(os.path.dirname(__file__), 'admins.json')

def load_admins():
    if not os.path.exists(ADMIN_JSON_PATH):
        with open(ADMIN_JSON_PATH, 'w') as f:
            json.dump([], f)
    with open(ADMIN_JSON_PATH, 'r') as f:
        return json.load(f)

def save_admins(admins):
    with open(ADMIN_JSON_PATH, 'w') as f:
        json.dump(admins, f, indent=2)

# Initialize database and create sample student user

def create_tables():
    db.create_all()
    student = User.query.filter_by(username='student').first()
    if not student:
        student = User(
            username='student',
            email='student@exam.com',
            password_hash='tits123',
            role='student'
        )
        db.session.add(student)
        db.session.commit()
    admins = load_admins()
    if not admins:
        default_admin = {
            'username': 'admin',
            'email': 'admin@exam.com',
            'password': 'admin123',
            'role': 'admin',
            'domain': 'all',
            'created_at': datetime.utcnow().isoformat()
        }
        admins.append(default_admin)
        save_admins(admins)

def ensure_column(table_name: str, column_name: str, col_def_sql: str):
    """Add a column to an SQLite table if it doesn't already exist."""
    try:
        info = db.session.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        cols = {row[1] for row in info}
        if column_name not in cols:
            db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_def_sql}"))
            db.session.commit()
    except Exception as e:
        # Fallback: ignore if cannot alter (e.g., during first create)
        db.session.rollback()
        print(f"Column migration skipped for {table_name}.{column_name}: {e}")

with app.app_context():
    # Ensure tables exist first, then apply lightweight migrations
    db.create_all()
    ensure_column('user', 'is_approved', 'is_approved BOOLEAN DEFAULT 0')
    ensure_column('question', 'question_type', 'question_type VARCHAR(20) DEFAULT "mcq_single"')
    ensure_column('question', 'correct_answer_text', 'correct_answer_text TEXT')
    ensure_column('question', 'points', 'points FLOAT DEFAULT 1.0')
    ensure_column('question', 'partial_credit', 'partial_credit BOOLEAN DEFAULT 1')
    ensure_column('question', 'correct_answer', 'correct_answer VARCHAR(10)')
    ensure_column('exam_session', 'score', 'score FLOAT DEFAULT 0.0')
    ensure_column('exam_session', 'exam_id', 'exam_id INTEGER')
    ensure_column('exam_response', 'user_answer', 'user_answer TEXT')
    ensure_column('exam_response', 'awarded_points', 'awarded_points FLOAT DEFAULT 0.0')
    # Create retake permission table if not exists
    try:
        db.create_all()  # safe call; ensures new tables like ExamRetakePermission
    except Exception:
        pass
    # Create default records after schema is up-to-date
    create_tables()

@app.route('/admin/exams/<domain>')
def admin_exams(domain):
    if not session.get('admin_user'):
        flash('Please log in as admin.', 'error')
        return redirect(url_for('admin_login'))
    admins = load_admins()
    admin_info = next((a for a in admins if a.get('username') == session.get('admin_user')), None)
    if not admin_info:
        session.pop('admin_user', None)
        session.pop('admin_domains', None)
        flash('Admin account not found. Please log in again.', 'error')
        return redirect(url_for('admin_login'))
    all_domains = ['web_dev', 'ml', 'data_science']
    admin_domains = admin_info.get('domain', [])
    if isinstance(admin_domains, str):
        if admin_domains == 'all':
            allowed_domains = all_domains
        else:
            allowed_domains = [admin_domains]
    else:
        allowed_domains = admin_domains if admin_domains else all_domains
    if domain not in allowed_domains:
        flash('You are not allowed to manage exams for this domain.', 'error')
        return redirect(url_for('admin_dashboard_json'))
    exams = Exam.query.filter_by(domain=domain).order_by(Exam.created_at.desc()).all()
    return render_template('admin_exams.html', domain=domain, exams=exams)

@app.route('/admin/exams/create', methods=['GET', 'POST'])
def create_exam():
    if not session.get('admin_user'):
        flash('Please log in as admin.', 'error')
        return redirect(url_for('admin_login'))
    admins = load_admins()
    admin_info = next((a for a in admins if a.get('username') == session.get('admin_user')), None)
    if not admin_info:
        session.pop('admin_user', None)
        session.pop('admin_domains', None)
        flash('Admin account not found. Please log in again.', 'error')
        return redirect(url_for('admin_login'))
    all_domains = ['web_dev', 'ml', 'data_science']
    admin_domains = admin_info.get('domain', [])
    if isinstance(admin_domains, str):
        if admin_domains == 'all':
            allowed_domains = all_domains
        else:
            allowed_domains = [admin_domains]
    else:
        allowed_domains = admin_domains if admin_domains else all_domains
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        domain = request.form.get('domain')
        if not name:
            flash('Exam name is required.', 'error')
            return redirect(url_for('create_exam'))
        if domain not in allowed_domains:
            flash('You are not allowed to create exam for this domain.', 'error')
            return redirect(url_for('create_exam'))
        new_exam = Exam(name=name, domain=domain, is_visible=False)
        db.session.add(new_exam)
        db.session.commit()
        flash('Exam created successfully!', 'success')
        return redirect(url_for('admin_exams', domain=domain))
    return render_template('create_exam.html', domains=allowed_domains)

@app.route('/admin/exams/toggle/<int:exam_id>', methods=['POST'])
def toggle_exam_visibility(exam_id):
    if not session.get('admin_user'):
        flash('Please log in as admin.', 'error')
        return redirect(url_for('admin_login'))
    admins = load_admins()
    admin_info = next((a for a in admins if a.get('username') == session.get('admin_user')), None)
    exam = Exam.query.get_or_404(exam_id)
    # domain authorization
    allowed = admin_info.get('domain', 'all') if admin_info else 'all'
    if isinstance(allowed, str):
        if allowed != 'all' and exam.domain != allowed:
            flash('Not allowed to update this exam.', 'error')
            return redirect(url_for('admin_exams', domain=exam.domain))
    else:
        if allowed and exam.domain not in allowed:
            flash('Not allowed to update this exam.', 'error')
            return redirect(url_for('admin_exams', domain=exam.domain))
    exam.is_visible = not exam.is_visible
    db.session.commit()
    flash(f"Exam visibility set to {'ON' if exam.is_visible else 'OFF'}.", 'success')
    return redirect(url_for('admin_exams', domain=exam.domain))

@app.route('/admin/exams/<int:exam_id>/set_questions', methods=['GET', 'POST'])
def set_question_paper(exam_id):
    if not session.get('admin_user'):
        flash('Please log in as admin.', 'error')
        return redirect(url_for('admin_login'))
    admins = load_admins()
    admin_info = next((a for a in admins if a.get('username') == session.get('admin_user')), None)
    exam = Exam.query.get(exam_id)
    if not exam:
        flash('Please create an exam first before setting a question paper.', 'error')
        return redirect(url_for('create_exam'))
    # domain authorization
    allowed = admin_info.get('domain', 'all') if admin_info else 'all'
    if isinstance(allowed, str):
        if allowed != 'all' and exam.domain != allowed:
            flash('Not allowed to modify this exam.', 'error')
            return redirect(url_for('admin_exams', domain=exam.domain))
    else:
        if allowed and exam.domain not in allowed:
            flash('Not allowed to modify this exam.', 'error')
            return redirect(url_for('admin_exams', domain=exam.domain))
    if request.method == 'POST':
        selected_ids = request.form.getlist('question_ids')
        # wipe existing selection
        ExamQuestion.query.filter_by(exam_id=exam.id).delete()
        db.session.commit()
        order_counter = 1
        for qid in selected_ids:
            try:
                qid_int = int(qid)
            except ValueError:
                continue
            exists = Question.query.get(qid_int)
            if not exists or exists.domain != exam.domain:
                continue
            eq = ExamQuestion(exam_id=exam.id, question_id=qid_int, display_order=order_counter)
            db.session.add(eq)
            order_counter += 1
        db.session.commit()
        flash('Question paper updated.', 'success')
        return redirect(url_for('admin_exams', domain=exam.domain))
    # GET
    all_questions = Question.query.filter_by(domain=exam.domain).order_by(Question.created_at.desc()).all()
    selected_map = {eq.question_id for eq in ExamQuestion.query.filter_by(exam_id=exam.id).all()}
    return render_template('set_question_paper.html', exam=exam, questions=all_questions, selected_map=selected_map)

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    active_session = ExamSession.query.filter_by(
        user_id=current_user.id,
        is_completed=False
    ).first()
    if active_session:
        return redirect(url_for('take_exam', session_id=active_session.id))
    domains = ['web_dev', 'ml', 'data_science']
    visible_exams = Exam.query.filter_by(is_visible=True).order_by(Exam.created_at.desc()).all()
    return render_template('student_dashboard.html', domains=domains, exams=visible_exams)

@app.route('/confirm_start_exam/<domain>')
@login_required
def confirm_start_exam(domain):
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    # If any active session exists, continue it
    active_session = ExamSession.query.filter_by(
        user_id=current_user.id,
        is_completed=False
    ).first()
    if active_session:
        return redirect(url_for('take_exam', session_id=active_session.id))
    # Only show visible exams for this domain
    exams = Exam.query.filter_by(domain=domain, is_visible=True).order_by(Exam.created_at.desc()).all()
    # Exams already attempted by this user
    attempted_sessions = (ExamSession.query
                          .filter(ExamSession.user_id == current_user.id,
                                  ExamSession.is_completed == True,
                                  ExamSession.exam_id.isnot(None))
                          .all())
    attempted_exam_ids = {s.exam_id for s in attempted_sessions}
    # Retake permissions for current user for these exams
    exam_ids = [e.id for e in exams]
    retakes = []
    if exam_ids:
        retakes = ExamRetakePermission.query.filter(ExamRetakePermission.user_id == current_user.id,
                                                    ExamRetakePermission.exam_id.in_(exam_ids)).all()
    allowed_retake_ids = {r.exam_id for r in retakes if (r.remaining_attempts or 0) > 0}
    return render_template('confirm_start_exam.html', domain=domain, exams=exams, attempted_exam_ids=attempted_exam_ids, allowed_retake_ids=allowed_retake_ids)

@app.route('/student/exams')
@login_required
def student_exams_list():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    visible_exams = Exam.query.filter_by(is_visible=True).order_by(Exam.created_at.desc()).all()
    return render_template('student_exams.html', exams=visible_exams)

@app.route('/confirm_start_exam_by_exam/<int:exam_id>')
@login_required
def confirm_start_exam_by_exam(exam_id):
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    exam = Exam.query.get_or_404(exam_id)
    if not exam.is_visible:
        flash('This exam is not available.', 'error')
        return redirect(url_for('student_exams_list'))
    return render_template('confirm_start_exam_exam.html', exam=exam)

@app.route('/start_exam/<domain>')
@login_required
def start_exam(domain):
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    active_session = ExamSession.query.filter_by(
        user_id=current_user.id,
        is_completed=False
    ).first()
    if active_session:
        flash('You already have an active exam session', 'error')
        return redirect(url_for('student_dashboard'))
    # Redirect to domain listing to choose a specific visible exam
    flash('Please choose an exam from the list.', 'info')
    return redirect(url_for('confirm_start_exam', domain=domain))

@app.route('/start_exam_by_exam/<int:exam_id>')
@login_required
def start_exam_by_exam(exam_id):
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    active_session = ExamSession.query.filter_by(
        user_id=current_user.id,
        is_completed=False
    ).first()
    if active_session:
        flash('You already have an active exam session', 'error')
        return redirect(url_for('student_dashboard'))
    exam = Exam.query.get_or_404(exam_id)
    if not exam.is_visible:
        flash('This exam is not available.', 'error')
        return redirect(url_for('student_exams_list'))
    # Prevent multiple attempts for the same exam
    prior_attempt = ExamSession.query.filter_by(user_id=current_user.id, exam_id=exam.id).first()
    if prior_attempt:
        if prior_attempt.is_completed:
            # Check admin-granted retake
            perm = ExamRetakePermission.query.filter_by(user_id=current_user.id, exam_id=exam.id).first()
            if perm and perm.remaining_attempts > 0:
                perm.remaining_attempts -= 1
                db.session.commit()
            else:
                flash('You have already attempted this exam.', 'error')
                return redirect(url_for('student_dashboard'))
        else:
            # Resume existing unfinished attempt
            flash('Resuming your active exam session.', 'info')
            return redirect(url_for('take_exam', session_id=prior_attempt.id))
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(minutes=30)
    exam_session = ExamSession(
        user_id=current_user.id,
        domain=exam.domain,
        exam_id=exam.id,
        start_time=start_time,
        end_time=end_time
    )
    db.session.add(exam_session)
    db.session.commit()
    return redirect(url_for('take_exam', session_id=exam_session.id))

@app.route('/take_exam/<int:session_id>')
@login_required
def take_exam(session_id):
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    exam_session = ExamSession.query.get_or_404(session_id)
    if exam_session.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('student_dashboard'))
    if exam_session.is_completed:
        flash('This exam has already been completed', 'info')
        return redirect(url_for('student_dashboard'))
    if datetime.utcnow() > exam_session.end_time:
        submit_exam(session_id)
        flash('Time expired! Exam submitted automatically.', 'info')
        return redirect(url_for('exam_results', session_id=session_id))
    if exam_session.exam_id:
        selected = (ExamQuestion.query
                    .filter_by(exam_id=exam_session.exam_id)
                    .order_by(ExamQuestion.display_order.asc(), ExamQuestion.id.asc())
                    .all())
        question_ids = [s.question_id for s in selected]
        if question_ids:
            qs = Question.query.filter(Question.id.in_(question_ids)).all()
            by_id = {q.id: q for q in qs}
            questions = [by_id[qid] for qid in question_ids if qid in by_id]
        else:
            questions = []
    else:
        questions = Question.query.filter_by(domain=exam_session.domain).all()
    exam_session.total_questions = len(questions)
    db.session.commit()
    return render_template('take_exam.html', exam_session=exam_session, questions=questions)

@app.route('/submit_exam/<int:session_id>', methods=['POST'])
@login_required
def submit_exam_route(session_id):
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    exam_session = ExamSession.query.get_or_404(session_id)
    if exam_session.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('student_dashboard'))
    submit_exam(session_id)
    flash('Exam submitted successfully!', 'success')
    return redirect(url_for('exam_results', session_id=session_id))

def submit_exam(session_id):
    exam_session = ExamSession.query.get(session_id)
    if not exam_session or exam_session.is_completed:
        return
    responses_dict = request.form.to_dict(flat=False)  # allow multi-select
    total_score = 0.0
    # Build the full set of question ids for this session
    if exam_session.exam_id:
        selected = (ExamQuestion.query
                    .filter_by(exam_id=exam_session.exam_id)
                    .order_by(ExamQuestion.display_order.asc(), ExamQuestion.id.asc())
                    .all())
        question_ids = [s.question_id for s in selected]
        if question_ids:
            qs = Question.query.filter(Question.id.in_(question_ids)).all()
            questions_by_id = {q.id: q for q in qs}
        else:
            questions_by_id = {}
    else:
        qs = Question.query.filter_by(domain=exam_session.domain).all()
        question_ids = [q.id for q in qs]
        questions_by_id = {q.id: q for q in qs}

    answered_ids = set()
    for key, answers in responses_dict.items():
        if not key.startswith('question_'):
            continue
        qid = int(key.replace('question_', ''))
        answered_ids.add(qid)
        question = questions_by_id.get(qid) or Question.query.get(qid)
        if not question:
            continue
        awarded = 0.0
        is_correct = False
        if question.question_type == 'short_text':
            user_text = (answers[0] if answers else '').strip().lower()
            acceptable = [(a.strip().lower()) for a in (question.correct_answer_text or '').split(',') if a.strip()]
            is_correct = user_text in acceptable if acceptable else False
            awarded = question.points if is_correct else 0.0
            user_answer_store = user_text
        elif question.question_type == 'mcq_multi':
            correct_set = set((question.correct_answer or '').split(','))
            user_set = set(answers)
            user_answer_store = ','.join(sorted(user_set))
            if question.partial_credit and correct_set:
                num_correct_selected = len(user_set & correct_set)
                num_incorrect_selected = len(user_set - correct_set)
                base = num_correct_selected / len(correct_set)
                penalty = num_incorrect_selected / max(len(correct_set), 1)
                raw = max(0.0, base - penalty)
                awarded = round(raw * question.points, 2)
                is_correct = awarded == question.points
            else:
                is_correct = user_set == correct_set
                awarded = question.points if is_correct else 0.0
        else:  # mcq_single
            user_choice = answers[0] if answers else ''
            user_answer_store = user_choice
            correct_choice = (question.correct_answer or '').split(',')[0]
            is_correct = user_choice == correct_choice
            awarded = question.points if is_correct else 0.0
        response = ExamResponse(
            exam_session_id=session_id,
            question_id=qid,
            user_answer=user_answer_store,
            is_correct=is_correct,
            awarded_points=awarded
        )
        db.session.add(response)
        total_score += awarded
    # Fill unanswered questions as blanks
    for qid in question_ids:
        if qid in answered_ids:
            continue
        response = ExamResponse(
            exam_session_id=session_id,
            question_id=qid,
            user_answer='',
            is_correct=False,
            awarded_points=0.0
        )
        db.session.add(response)
    exam_session.score = total_score
    exam_session.is_completed = True
    db.session.commit()

@app.route('/exam_results/<int:session_id>')
@login_required
def exam_results(session_id):
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    exam_session = ExamSession.query.get_or_404(session_id)
    if exam_session.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('student_dashboard'))
    responses = ExamResponse.query.filter_by(exam_session_id=session_id).all()
    questions = Question.query.filter_by(domain=exam_session.domain).all()
    return render_template('exam_results.html', exam_session=exam_session, responses=responses, questions=questions)

@app.route('/student/results')
@login_required
def student_results_list():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    sessions = (ExamSession.query
                .filter_by(user_id=current_user.id, is_completed=True)
                .order_by(ExamSession.end_time.desc())
                .all())
    return render_template('student_results.html', sessions=sessions)

@app.route('/admin/session/<int:session_id>')
def admin_view_session(session_id):
    if not session.get('admin_user'):
        flash('Please log in as admin.', 'error')
        return redirect(url_for('admin_login'))
    admins = load_admins()
    admin_info = next((a for a in admins if a.get('username') == session.get('admin_user')), None)
    if not admin_info:
        session.pop('admin_user', None)
        session.pop('admin_domains', None)
        flash('Admin account not found. Please log in again.', 'error')
        return redirect(url_for('admin_login'))
    all_domains = ['web_dev', 'ml', 'data_science']
    admin_domains = admin_info.get('domain', [])
    if isinstance(admin_domains, str):
        if admin_domains == 'all':
            allowed_domains = all_domains
        else:
            allowed_domains = [admin_domains]
    else:
        allowed_domains = admin_domains if admin_domains else all_domains
    exam_session = ExamSession.query.get_or_404(session_id)
    if not exam_session.is_completed:
        flash('Exam is not completed yet.', 'error')
        return redirect(url_for('admin_results'))
    if exam_session.domain not in allowed_domains:
        flash('You are not allowed to view this exam session.', 'error')
        return redirect(url_for('admin_results'))
    responses = ExamResponse.query.filter_by(exam_session_id=session_id).all()
    questions = Question.query.filter_by(domain=exam_session.domain).all()
    student = User.query.get(exam_session.user_id)
    student_username = student.username if student else f'Student #{exam_session.user_id}'
    return render_template('admin_exam_view.html',
                           exam_session=exam_session,
                           responses=responses,
                           questions=questions,
                           student_username=student_username)

@app.route('/admin/export/session/<int:session_id>')
def export_session_csv(session_id):
    if not session.get('admin_user'):
        return redirect(url_for('admin_login'))
    admins = load_admins()
    admin_info = next((a for a in admins if a.get('username') == session.get('admin_user')), None)
    exam_session = ExamSession.query.get_or_404(session_id)
    # domain check
    allowed = admin_info.get('domain', 'all') if admin_info else 'all'
    if isinstance(allowed, str):
        if allowed != 'all' and exam_session.domain != allowed:
            flash('Not allowed.', 'error')
            return redirect(url_for('admin_results'))
    else:
        if allowed and exam_session.domain not in allowed:
            flash('Not allowed.', 'error')
            return redirect(url_for('admin_results'))
    responses = ExamResponse.query.filter_by(exam_session_id=session_id).all()
    questions = {q.id: q for q in Question.query.filter_by(domain=exam_session.domain).all()}
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Question ID', 'Question', 'User Answer', 'Correct', 'Correct Answer'])
    for r in responses:
        q = questions.get(r.question_id)
        if q and q.question_type == 'short_text':
            correct_disp = (q.correct_answer_text or '')
        elif q:
            correct_text = getattr(q, f"option_{(q.correct_answer or '').lower()}") if q.correct_answer else ''
            correct_disp = f"{q.correct_answer}. {correct_text}"
        else:
            correct_disp = ''
        writer.writerow([r.question_id, q.question_text if q else '', r.user_answer, 'YES' if r.is_correct else 'NO', correct_disp])
    output = si.getvalue()
    return app.response_class(output, mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename=session_{session_id}.csv'})

@app.route('/admin/export/all')
def export_all_csv():
    if not session.get('admin_user'):
        return redirect(url_for('admin_login'))
    admins = load_admins()
    admin_info = next((a for a in admins if a.get('username') == session.get('admin_user')), None)
    all_domains = ['web_dev', 'ml', 'data_science']
    allowed = admin_info.get('domain', []) if admin_info else []
    if isinstance(allowed, str):
        allowed_domains = all_domains if allowed == 'all' else [allowed]
    else:
        allowed_domains = allowed if allowed else all_domains
    sessions = ExamSession.query.filter(ExamSession.is_completed == True, ExamSession.domain.in_(allowed_domains)).all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Session ID', 'User ID', 'Domain', 'Score', 'Total Questions', 'Start', 'End'])
    for s in sessions:
        writer.writerow([s.id, s.user_id, s.domain, s.score, s.total_questions, s.start_time.isoformat(), s.end_time.isoformat()])
    output = si.getvalue()
    return app.response_class(output, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=results.csv'})

if __name__ == '__main__':
    app.run(debug=True)
