import os
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash, request, abort, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required, current_user
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address, default_limits=[])

# All records belong to a college tenant. Users can only access their own tenant's data.
class College(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    code = db.Column(db.String(40), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("college.id"), nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="teacher")
    active = db.Column(db.Boolean, default=True, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("college.id"), nullable=False, index=True)
    student_no = db.Column(db.String(40), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False, default="")
    father_name = db.Column(db.String(120), default="")
    email = db.Column(db.String(180), default="")
    phone = db.Column(db.String(40), default="")
    program = db.Column(db.String(100), default="")
    semester = db.Column(db.String(40), default="")
    admission_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(30), default="Applied")
    __table_args__ = (db.UniqueConstraint("college_id", "student_no", name="uq_student_no"),)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("college.id"), nullable=False, index=True)
    code = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(140), nullable=False)
    credit_hours = db.Column(db.Integer, default=3)
    semester = db.Column(db.String(40), default="")
    teacher_name = db.Column(db.String(120), default="")
    __table_args__ = (db.UniqueConstraint("college_id", "code", name="uq_course_code"),)

class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("college.id"), nullable=False, index=True)
    student_no = db.Column(db.String(40), nullable=False)
    course_code = db.Column(db.String(40), nullable=False)
    semester = db.Column(db.String(40), default="")
    status = db.Column(db.String(30), default="Registered")
    registered_on = db.Column(db.Date, default=date.today)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("college.id"), nullable=False, index=True)
    student_no = db.Column(db.String(40), nullable=False)
    course_code = db.Column(db.String(40), nullable=False)
    attendance_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default="Present")

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("college.id"), nullable=False, index=True)
    exam_code = db.Column(db.String(40), nullable=False)
    course_code = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(140), nullable=False)
    exam_date = db.Column(db.Date, nullable=True)
    total_marks = db.Column(db.Integer, default=100)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("college.id"), nullable=False, index=True)
    student_no = db.Column(db.String(40), nullable=False)
    exam_code = db.Column(db.String(40), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False, default=0)
    grade = db.Column(db.String(5), default="")
    status = db.Column(db.String(30), default="Draft")

class FeeInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("college.id"), nullable=False, index=True)
    invoice_no = db.Column(db.String(50), nullable=False)
    student_no = db.Column(db.String(40), nullable=False)
    description = db.Column(db.String(180), default="Semester fee")
    amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(30), default="Unpaid")

class FeePayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("college.id"), nullable=False, index=True)
    invoice_no = db.Column(db.String(50), nullable=False)
    student_no = db.Column(db.String(40), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    paid_on = db.Column(db.Date, default=date.today)
    reference = db.Column(db.String(100), default="")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

MODULES = {
    "students": {
        "title": "Student Admissions", "model": Student, "roles": ["admin", "admissions"],
        "fields": [
            ("student_no","Student / PRN number","text",True),("first_name","First name","text",True),
            ("last_name","Last name","text",False),("father_name","Father name","text",False),
            ("email","Email","email",False),("phone","Phone","text",False),
            ("program","Program","text",False),("semester","Semester","text",False),
            ("admission_date","Admission date","date",False),
            ("status","Admission status","select:Applied,Under Review,Accepted,Rejected,Enrolled",True)
        ], "columns": [("student_no","Student No."),("first_name","First name"),("last_name","Last name"),("program","Program"),("semester","Semester"),("status","Status")]
    },
    "courses": {
        "title": "Courses", "model": Course, "roles": ["admin", "admissions", "teacher"],
        "fields": [("code","Course code","text",True),("title","Course title","text",True),
                   ("credit_hours","Credit hours","number",True),("semester","Semester","text",False),
                   ("teacher_name","Teacher name","text",False)],
        "columns": [("code","Code"),("title","Title"),("credit_hours","Credits"),("semester","Semester"),("teacher_name","Teacher")]
    },
    "registrations": {
        "title": "Course Registration", "model": Registration, "roles": ["admin", "admissions"],
        "fields": [("student_no","Student / PRN number","text",True),("course_code","Course code","text",True),
                   ("semester","Semester","text",True),("status","Status","select:Registered,Withdrawn,Completed",True)],
        "columns": [("student_no","Student No."),("course_code","Course"),("semester","Semester"),("status","Status"),("registered_on","Registered")]
    },
    "attendance": {
        "title": "Attendance", "model": Attendance, "roles": ["admin", "teacher"],
        "fields": [("student_no","Student / PRN number","text",True),("course_code","Course code","text",True),
                   ("attendance_date","Date","date",True),("status","Attendance","select:Present,Absent,Late,Excused",True)],
        "columns": [("student_no","Student No."),("course_code","Course"),("attendance_date","Date"),("status","Status")]
    },
    "exams": {
        "title": "Examinations", "model": Exam, "roles": ["admin", "exam_officer"],
        "fields": [("exam_code","Exam code","text",True),("course_code","Course code","text",True),
                   ("title","Exam title","text",True),("exam_date","Exam date","date",False),
                   ("total_marks","Total marks","number",True)],
        "columns": [("exam_code","Exam code"),("course_code","Course"),("title","Title"),("exam_date","Date"),("total_marks","Total marks")]
    },
    "results": {
        "title": "Results", "model": Result, "roles": ["admin", "exam_officer", "teacher"],
        "fields": [("student_no","Student / PRN number","text",True),("exam_code","Exam code","text",True),
                   ("marks_obtained","Marks obtained","number",True),("status","Status","select:Draft,Verified,Published",True)],
        "columns": [("student_no","Student No."),("exam_code","Exam"),("marks_obtained","Marks"),("grade","Grade"),("status","Status")],
    },
    "fees": {
        "title": "Fee Invoices", "model": FeeInvoice, "roles": ["admin", "accounts"],
        "fields": [("invoice_no","Invoice number","text",True),("student_no","Student / PRN number","text",True),
                   ("description","Description","text",False),("amount","Amount (PKR)","number",True),
                   ("due_date","Due date","date",False),("status","Status","select:Unpaid,Partially Paid,Paid,Overdue",True)],
        "columns": [("invoice_no","Invoice"),("student_no","Student No."),("description","Description"),("amount","Amount (PKR)"),("due_date","Due date"),("status","Status")]
    },
    "payments": {
        "title": "Fee Payments", "model": FeePayment, "roles": ["admin", "accounts"],
        "fields": [("invoice_no","Invoice number","text",True),("student_no","Student / PRN number","text",True),
                   ("amount","Amount paid (PKR)","number",True),("paid_on","Payment date","date",True),
                   ("reference","Receipt / bank reference","text",False)],
        "columns": [("invoice_no","Invoice"),("student_no","Student No."),("amount","Amount"),("paid_on","Paid on"),("reference","Reference")]
    },
}

def create_app(test_config=None):
    app = Flask(__name__)
    environment = os.getenv("FLASK_ENV", os.getenv("APP_ENV", "development")).lower()
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key and environment in {"production", "prod"}:
        raise RuntimeError("SECRET_KEY must be set in production. Generate a long random secret and configure it in the hosting environment.")
    app.config["SECRET_KEY"] = secret_key or "local-development-only-secret-change-me"
    database_url = os.getenv("DATABASE_URL", "sqlite:///gpgc_saas.db")
    # Managed PostgreSQL providers commonly supply postgres://; SQLAlchemy expects postgresql://.
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = environment in {"production", "prod"}
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SECURE"] = environment in {"production", "prod"}
    app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 8
    if test_config:
        app.config.update(test_config)
    # Trust one reverse proxy hop for HTTPS and host metadata on typical managed hosting.
    if environment in {"production", "prod"}:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"
    csrf.init_app(app)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if environment in {"production", "prod"}:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.context_processor
    def inject_globals():
        return {"module_config": MODULES}

    @app.route("/")
    def index():
        return redirect(url_for("dashboard") if current_user.is_authenticated else url_for("login"))

    @app.route("/login", methods=["GET","POST"])
    @limiter.limit("10 per minute", methods=["POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            email = request.form.get("email","").strip().lower()
            password = request.form.get("password","")
            user = User.query.filter_by(email=email, active=True).first()
            if user and user.check_password(password):
                login_user(user)
                flash("Welcome back.", "success")
                return redirect(url_for("dashboard"))
            flash("Invalid email or password.", "danger")
        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        logout_user()
        flash("You have been signed out.", "info")
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        cid = current_user.college_id
        counts = {
            "students": Student.query.filter_by(college_id=cid).count(),
            "courses": Course.query.filter_by(college_id=cid).count(),
            "attendance": Attendance.query.filter_by(college_id=cid).count(),
            "exams": Exam.query.filter_by(college_id=cid).count(),
            "results": Result.query.filter_by(college_id=cid).count(),
            "unpaid": FeeInvoice.query.filter_by(college_id=cid).filter(FeeInvoice.status != "Paid").count(),
        }
        college = db.session.get(College, cid)
        return render_template("dashboard.html", counts=counts, college=college)

    def role_required(roles):
        def decorator(fn):
            @wraps(fn)
            @login_required
            def wrapper(*args, **kwargs):
                if current_user.role not in roles:
                    abort(403)
                return fn(*args, **kwargs)
            return wrapper
        return decorator

    def parse_value(value, kind, field_name):
        if value == "":
            return None
        if kind == "date":
            return date.fromisoformat(value)
        if kind == "number":
            if field_name in ("credit_hours","total_marks"):
                return int(value)
            return Decimal(value) if field_name in ("amount",) else float(value)
        return value.strip()

    @app.route("/m/<module_key>", methods=["GET","POST"])
    @login_required
    def module_page(module_key):
        config = MODULES.get(module_key)
        if not config:
            abort(404)
        if current_user.role not in config["roles"]:
            abort(403)
        Model = config["model"]
        if request.method == "POST":
            record = Model(college_id=current_user.college_id)
            try:
                for field, label, kind, required in config["fields"]:
                    raw = request.form.get(field, "").strip()
                    if required and not raw:
                        raise ValueError(f"{label} is required.")
                    val = parse_value(raw, kind, field)
                    if field == "marks_obtained" and val is not None and val < 0:
                        raise ValueError("Marks cannot be negative.")
                    if field == "amount" and val is not None and val < 0:
                        raise ValueError("Amount cannot be negative.")
                    if val is not None:
                        setattr(record, field, val)
                if module_key == "results":
                    exam = Exam.query.filter_by(college_id=current_user.college_id,
                                                exam_code=record.exam_code).first()
                    if not exam:
                        raise ValueError("Create the exam first using its exam code.")
                    if record.marks_obtained > exam.total_marks:
                        raise ValueError(f"Marks cannot exceed total marks ({exam.total_marks}).")
                    ratio = record.marks_obtained / exam.total_marks if exam.total_marks else 0
                    record.grade = "A" if ratio >= .8 else "B" if ratio >= .7 else "C" if ratio >= .6 else "D" if ratio >= .5 else "F"
                db.session.add(record)
                db.session.commit()
                flash(f"{config['title']} record saved.", "success")
                return redirect(url_for("module_page", module_key=module_key))
            except (ValueError, TypeError, InvalidOperation) as exc:
                db.session.rollback()
                flash(str(exc) or "Please check the entered values.", "danger")
            except Exception:
                db.session.rollback()
                flash("Could not save record. Check for duplicate codes or invalid references.", "danger")
        records = Model.query.filter_by(college_id=current_user.college_id).order_by(Model.id.desc()).limit(300).all()
        return render_template("module.html", config=config, module_key=module_key, records=records)

    @app.route("/health")
    def health():
        return {"status": "ok", "application": "GPGC Nowshera SaaS"}, 200

    @app.errorhandler(403)
    def forbidden(_):
        return render_template("error.html", code=403, message="Your role does not have permission to access this module."), 403

    @app.errorhandler(404)
    def not_found(_):
        return render_template("error.html", code=404, message="The requested page was not found."), 404

    # Convenience schema creation is restricted to local development. Production schema
    # changes must be applied as explicit migrations before a release.
    if environment not in {"production", "prod"} or os.getenv("BOOTSTRAP_DB", "").lower() == "true":
        with app.app_context():
            db.create_all()
            # One-time production bootstrap: create the initial college administrator only
            # when no admin account exists. Disable BOOTSTRAP_DB after first successful start.
            if environment in {"production", "prod"} and os.getenv("BOOTSTRAP_DB", "").lower() == "true":
                initial_password = os.getenv("INITIAL_ADMIN_PASSWORD", "")
                if len(initial_password) < 14:
                    raise RuntimeError("Set INITIAL_ADMIN_PASSWORD to a unique password of at least 14 characters before enabling BOOTSTRAP_DB.")
                college = College.query.filter_by(code="GPGC-NSR").first()
                if not college:
                    college = College(name="GPGC Nowshera", code="GPGC-NSR")
                    db.session.add(college)
                    db.session.flush()
                admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "admin@gpgc.local").strip().lower()
                existing_admin = User.query.filter_by(email=admin_email).first()
                if not existing_admin:
                    admin = User(college_id=college.id, full_name="System Administrator",
                                 email=admin_email, role="admin", active=True)
                    admin.set_password(initial_password)
                    db.session.add(admin)
                    db.session.commit()
    return app

def init_demo():
    app = create_app()
    with app.app_context():
        college = College.query.filter_by(code="GPGC-NSR").first()
        if not college:
            college = College(name="GPGC Nowshera", code="GPGC-NSR")
            db.session.add(college)
            db.session.flush()
        user = User.query.filter_by(college_id=college.id, email="admin@gpgc.local").first()
        if not user:
            user = User(college_id=college.id, full_name="System Administrator",
                        email="admin@gpgc.local", role="admin")
            user.set_password(os.getenv("INITIAL_ADMIN_PASSWORD", "ChangeMe123!"))
            db.session.add(user)
        db.session.commit()
        print("Demo tenant: GPGC Nowshera")
        print("Login: admin@gpgc.local")
        print("Initial password: set INITIAL_ADMIN_PASSWORD or use ChangeMe123! (change immediately)")
