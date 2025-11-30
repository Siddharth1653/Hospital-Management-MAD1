from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
from models import db, User, DoctorProfile, Appointment

app = Flask(__name__)
app.config['SECRET_KEY'] = 'replace-with-a-secure-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_data():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin', password_hash=generate_password_hash('admin123'))
            db.session.add(admin)
            db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username exists')
            return redirect(url_for('register'))
        user = User(username=username, role='patient', password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('patient_dashboard'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        user=User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            if user.role=='admin':
                return redirect(url_for('admin_dashboard'))
            if user.role=='doctor':
                return redirect(url_for('doctor_dashboard'))
            return redirect(url_for('patient_dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role!='admin':
        return redirect(url_for('index'))
    doctors = DoctorProfile.query.all()
    patients = User.query.filter_by(role='patient').all()
    appointments = Appointment.query.order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    return render_template('admin_dashboard.html', doctors=doctors, patients=patients, appointments=appointments)

@app.route('/admin/doctors')
@login_required
def doctor_list():
    if current_user.role!='admin':
        return redirect(url_for('index'))
    doctors = DoctorProfile.query.all()
    return render_template('doctor_list.html', doctors=doctors)

@app.route('/admin/doctor/new', methods=['GET','POST'])
@login_required
def doctor_new():
    if current_user.role!='admin':
        return redirect(url_for('index'))
    if request.method=='POST':
        name = request.form['name']
        spec = request.form['specialization']
        avail = request.form['availability']
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Doctor username exists')
            return redirect(url_for('doctor_new'))
        user = User(username=username, role='doctor', password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        profile = DoctorProfile(user_id=user.id, name=name, specialization=spec, availability=avail)
        db.session.add(profile)
        db.session.commit()
        return redirect(url_for('doctor_list'))
    return render_template('doctor_form.html')

@app.route('/admin/doctor/edit/<int:id>', methods=['GET','POST'])
@login_required
def doctor_edit(id):
    if current_user.role!='admin':
        return redirect(url_for('index'))
    profile = DoctorProfile.query.get_or_404(id)
    if request.method=='POST':
        profile.name = request.form['name']
        profile.specialization = request.form['specialization']
        profile.availability = request.form['availability']
        db.session.commit()
        return redirect(url_for('doctor_list'))
    return render_template('doctor_form.html', profile=profile)

@app.route('/admin/doctor/delete/<int:id>')
@login_required
def doctor_delete(id):
    if current_user.role!='admin':
        return redirect(url_for('index'))
    profile = DoctorProfile.query.get_or_404(id)
    user = User.query.get(profile.user_id)
    db.session.delete(profile)
    if user:
        db.session.delete(user)
    db.session.commit()
    return redirect(url_for('doctor_list'))

@app.route('/patient')
@login_required
def patient_dashboard():
    if current_user.role != 'patient':
        return redirect(url_for('index'))
    doctors = DoctorProfile.query.all()
    appointments = Appointment.query.filter_by(patient_id=current_user.id).order_by(Appointment.date.desc()).all()
    doctor_map = {d.user_id: d for d in doctors}
    return render_template('patient_dashboard.html', doctors=doctors, appointments=appointments, doctor_map=doctor_map)

@app.route('/patient/profile', methods=['GET','POST'])
@login_required
def patient_profile():
    if current_user.role!='patient':
        return redirect(url_for('index'))
    if request.method=='POST':
        current_user.contact = request.form.get('contact')
        current_user.age = request.form.get('age')
        db.session.commit()
        flash('Profile updated')
        return redirect(url_for('patient_profile'))
    return render_template('patient_profile.html')

@app.route('/doctor')
@login_required
def doctor_dashboard():
    if current_user.role!='doctor':
        return redirect(url_for('index'))
    profile = DoctorProfile.query.filter_by(user_id=current_user.id).first()
    appointments = Appointment.query.filter_by(doctor_id=current_user.id).order_by(Appointment.date.desc()).all()
    patients = {a.patient_id: User.query.get(a.patient_id) for a in appointments}
    return render_template('doctor_dashboard.html', profile=profile, appointments=appointments, patients=patients)

@app.route('/doctor/appointment/<int:id>', methods=['GET','POST'])
@login_required
def doctor_appointment(id):
    if current_user.role!='doctor':
        return redirect(url_for('index'))
    appt = Appointment.query.get_or_404(id)
    if request.method=='POST':
        appt.status = request.form.get('status')
        appt.diagnosis = request.form.get('diagnosis')
        appt.prescription = request.form.get('prescription')
        appt.notes = request.form.get('notes')
        db.session.commit()
        return redirect(url_for('doctor_dashboard'))
    return render_template('appointments.html', appt=appt, role='doctor')

@app.route('/appointments')
@login_required
def all_appointments():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    appointments = Appointment.query.order_by(Appointment.date.desc()).all()
    users = User.query.filter(User.role.in_(['patient','doctor'])).all()
    user_map = {u.id: u for u in users}
    return render_template('appointments.html', appointments=appointments, role='admin', user_map=user_map)

@app.route('/book/<int:doctor_id>', methods=['GET','POST'])
@login_required
def book_appointment(doctor_id):
    if current_user.role!='patient':
        return redirect(url_for('index'))
    doctor = DoctorProfile.query.get_or_404(doctor_id)
    if request.method=='POST':
        appt_date = request.form['date']
        appt_time = request.form['time']
        conflict = Appointment.query.filter_by(doctor_id=doctor.user_id, date=appt_date, time=appt_time, status='Booked').first()
        if conflict:
            flash('Selected slot already booked')
            return redirect(url_for('book_appointment', doctor_id=doctor_id))
        appt = Appointment(patient_id=current_user.id, doctor_id=doctor.user_id, date=appt_date, time=appt_time, status='Booked')
        db.session.add(appt)
        db.session.commit()
        return redirect(url_for('patient_dashboard'))
    return render_template('book_appointment.html', doctor=doctor, today=date.today().isoformat())

if __name__ == '__main__':
    create_data()
    app.run(debug=True)