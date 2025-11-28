from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------- MODELS -------------------- #

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    sem = db.Column(db.String(10), nullable=False)
    stream = db.Column(db.String(50), nullable=False)
    division = db.Column(db.String(10), nullable=False)

    attendances = db.relationship('Attendance', backref='student', lazy=True)

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(100), nullable=False)

    attendances = db.relationship('Attendance', backref='teacher', lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    lecture_no = db.Column(db.String(10), nullable=False)
    sem = db.Column(db.String(10), nullable=False)
    stream = db.Column(db.String(50), nullable=False)
    division = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(10), nullable=False)  # present / absent

    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)

# Simple admin credentials (you can change these)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# -------------------- UTILS -------------------- #

def create_admin_if_needed():
    # Only placeholder here – admin uses static username/password.
    pass

@app.before_request
def init_db():
    db.create_all()
    create_admin_if_needed()

def login_user(user_type, user_obj):
    session['user_type'] = user_type
    session['user_id'] = user_obj.id if user_type in ['student', 'teacher'] else None
    session['user_name'] = getattr(user_obj, 'name', 'Admin') if user_obj else 'Admin'

def logout_user():
    session.clear()

# -------------------- ROUTES -------------------- #

@app.route('/')
def index():
    return render_template('index.html')

# ----- Student Register & Login ----- #

@app.route('/student/register', methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        sem = request.form['sem'].strip()
        stream = request.form['stream'].strip()
        division = request.form['division'].strip()

        if Student.query.filter_by(email=email).first():
            flash('Email already registered as student.', 'error')
            return redirect(url_for('student_register'))

        student = Student(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            sem=sem,
            stream=stream,
            division=division
        )
        db.session.add(student)
        db.session.commit()
        flash('Student registered successfully. Please login.', 'success')
        return redirect(url_for('student_login'))

    return render_template('student_register.html')

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        student = Student.query.filter_by(email=email).first()
        if not student or not check_password_hash(student.password_hash, password):
            flash('Invalid email or password.', 'error')
            return redirect(url_for('student_login'))

        login_user('student', student)
        flash('Logged in as student.', 'success')
        return redirect(url_for('student_dashboard'))

    return render_template('login.html', title='Student Login')

@app.route('/student/dashboard')
def student_dashboard():
    if session.get('user_type') != 'student':
        flash('Please login as student.', 'error')
        return redirect(url_for('student_login'))

    student = Student.query.get(session['user_id'])
    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('student_login'))

    # Prepare attendance summary per subject
    attendance = Attendance.query.filter_by(student_id=student.id).all()
    summary = {}
    for a in attendance:
        sub = a.subject
        if sub not in summary:
            summary[sub] = {'total': 0, 'present': 0, 'absent': 0}
        summary[sub]['total'] += 1
        if a.status == 'present':
            summary[sub]['present'] += 1
        else:
            summary[sub]['absent'] += 1

    attendance_summary = []
    for subject, data in summary.items():
        percent_present = (data['present'] / data['total']) * 100 if data['total'] else 0
        attendance_summary.append({
            'subject': subject,
            'total': data['total'],
            'present': data['present'],
            'absent': data['absent'],
            'percent_present': percent_present
        })

    return render_template('student_dashboard.html', student=student, attendance_summary=attendance_summary)

# ----- Teacher Register & Login ----- #

@app.route('/teacher/register', methods=['GET', 'POST'])
def teacher_register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        department = request.form['department'].strip()

        if Teacher.query.filter_by(email=email).first():
            flash('Email already registered as teacher.', 'error')
            return redirect(url_for('teacher_register'))

        teacher = Teacher(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            department=department
        )
        db.session.add(teacher)
        db.session.commit()
        flash('Teacher registered successfully. Please login.', 'success')
        return redirect(url_for('teacher_login'))

    return render_template('teacher_register.html')

@app.route('/teacher/login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        teacher = Teacher.query.filter_by(email=email).first()
        if not teacher or not check_password_hash(teacher.password_hash, password):
            flash('Invalid email or password.', 'error')
            return redirect(url_for('teacher_login'))

        login_user('teacher', teacher)
        flash('Logged in as teacher.', 'success')
        return redirect(url_for('teacher_dashboard'))

    return render_template('login.html', title='Teacher Login')

@app.route('/teacher/dashboard', methods=['GET', 'POST'])
def teacher_dashboard():
    if session.get('user_type') != 'teacher':
        flash('Please login as teacher.', 'error')
        return redirect(url_for('teacher_login'))

    teacher = Teacher.query.get(session['user_id'])
    if not teacher:
        flash('Teacher not found.', 'error')
        return redirect(url_for('teacher_login'))

    students = None

    if request.method == 'GET' and request.args:
        date = request.args.get('date')
        subject = request.args.get('subject')
        lecture_no = request.args.get('lecture_no')
        sem = request.args.get('sem')
        stream = request.args.get('stream')
        division = request.args.get('division')

        if date and subject and lecture_no and sem and stream and division:
            students = Student.query.filter_by(
                sem=sem, stream=stream, division=division
            ).all()
        else:
            flash('Please fill all fields to load students.', 'error')

    if request.method == 'POST':
        date = request.form['date']
        subject = request.form['subject']
        lecture_no = request.form['lecture_no']
        sem = request.form['sem']
        stream = request.form['stream']
        division = request.form['division']

        students = Student.query.filter_by(
            sem=sem, stream=stream, division=division
        ).all()

        for s in students:
            status = request.form.get(f'status_{s.id}', 'absent')
            attendance = Attendance(
                date=date,
                subject=subject,
                lecture_no=lecture_no,
                sem=sem,
                stream=stream,
                division=division,
                status=status,
                student_id=s.id,
                teacher_id=teacher.id
            )
            db.session.add(attendance)
        db.session.commit()
        flash('Attendance saved successfully.', 'success')
        return redirect(url_for('teacher_dashboard'))

    return render_template(
        'teacher_dashboard.html',
        teacher=teacher,
        students=students
    )



# ----- Logout ----- #

@app.route('/logout')
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('index'))

# ----- Main ----- #

if __name__ == '__main__':
    # When running locally, ensure templates and static are discovered
    app.run(debug=True)
