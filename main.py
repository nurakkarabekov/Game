import os
import uuid
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    send_from_directory,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "videos")
ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'academy.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    is_published = db.Column(db.Boolean, default=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    teacher = db.relationship("User", backref="courses")


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    video_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)

    course = db.relationship("Course", backref="lessons")


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="pending")
    mbank_ref = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)

    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)

    student = db.relationship("User", backref="orders")
    course = db.relationship("Course", backref="orders")


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)

    __table_args__ = (db.UniqueConstraint("student_id", "course_id", name="uniq_enrollment"),)


def init_db() -> None:
    db.create_all()

    if not User.query.filter_by(email="admin@academy.local").first():
        admin = User(
            full_name="System Admin",
            email="admin@academy.local",
            password_hash=generate_password_hash("admin123"),
            role="admin",
        )
        teacher = User(
            full_name="Demo Teacher",
            email="teacher@academy.local",
            password_hash=generate_password_hash("teacher123"),
            role="teacher",
        )
        student = User(
            full_name="Demo Student",
            email="student@academy.local",
            password_hash=generate_password_hash("student123"),
            role="student",
        )
        db.session.add_all([admin, teacher, student])
        db.session.commit()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Сначала войдите в систему.", "error")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)

    return wrapper


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login"))
            if user.role not in roles:
                flash("Нет доступа к разделу.", "error")
                return redirect(url_for("index"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator


@app.route("/")
def index():
    courses = Course.query.filter_by(is_published=True).all()
    return render_template("index.html", user=current_user(), courses=courses)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")

        if role not in {"student", "teacher"}:
            role = "student"

        if not full_name or not email or len(password) < 6:
            flash("Проверьте корректность заполнения формы.", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Пользователь с таким email уже существует.", "error")
            return redirect(url_for("register"))

        user = User(
            full_name=full_name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
        )
        db.session.add(user)
        db.session.commit()
        flash("Регистрация успешна. Войдите в аккаунт.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", user=current_user())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Неверный email или пароль.", "error")
            return redirect(url_for("login"))

        session["user_id"] = user.id
        flash("Вы вошли в систему.", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html", user=current_user())


@app.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли из системы.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    if user.role == "admin":
        return redirect(url_for("admin_panel"))
    if user.role == "teacher":
        return redirect(url_for("teacher_panel"))
    return redirect(url_for("student_panel"))


@app.route("/admin")
@role_required("admin")
def admin_panel():
    return render_template(
        "admin.html",
        user=current_user(),
        users=User.query.order_by(User.id.desc()).all(),
        courses=Course.query.order_by(Course.id.desc()).all(),
        orders=Order.query.order_by(Order.id.desc()).all(),
    )


@app.route("/admin/course/<int:course_id>/toggle", methods=["POST"])
@role_required("admin")
def toggle_course(course_id):
    course = Course.query.get_or_404(course_id)
    course.is_published = not course.is_published
    db.session.commit()
    flash("Статус курса обновлен.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/teacher")
@role_required("teacher")
def teacher_panel():
    user = current_user()
    courses = Course.query.filter_by(teacher_id=user.id).all()
    return render_template("teacher.html", user=user, courses=courses)


@app.route("/teacher/course/new", methods=["POST"])
@role_required("teacher")
def new_course():
    user = current_user()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "0").strip()

    try:
        price = float(price)
    except ValueError:
        price = -1

    if not title or not description or price <= 0:
        flash("Введите корректные данные курса.", "error")
        return redirect(url_for("teacher_panel"))

    course = Course(title=title, description=description, price=price, teacher_id=user.id)
    db.session.add(course)
    db.session.commit()
    flash("Курс создан. Ожидает публикации администратором.", "success")
    return redirect(url_for("teacher_panel"))


@app.route("/teacher/course/<int:course_id>/lesson/new", methods=["POST"])
@role_required("teacher")
def new_lesson(course_id):
    user = current_user()
    course = Course.query.get_or_404(course_id)

    if course.teacher_id != user.id:
        flash("Вы не можете редактировать этот курс.", "error")
        return redirect(url_for("teacher_panel"))

    title = request.form.get("title", "").strip()
    file = request.files.get("video")

    if not title or not file or file.filename == "":
        flash("Добавьте название урока и видеофайл.", "error")
        return redirect(url_for("teacher_panel"))

    if not allowed_file(file.filename):
        flash("Недопустимый формат видео.", "error")
        return redirect(url_for("teacher_panel"))

    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    save_path = os.path.join(UPLOAD_DIR, unique_filename)
    file.save(save_path)

    lesson = Lesson(title=title, video_path=unique_filename, course_id=course.id)
    db.session.add(lesson)
    db.session.commit()

    flash("Урок добавлен.", "success")
    return redirect(url_for("teacher_panel"))


@app.route("/courses")
def courses_list():
    courses = Course.query.filter_by(is_published=True).all()
    user = current_user()

    enrolled_ids = set()
    if user and user.role == "student":
        enrolled_ids = {e.course_id for e in Enrollment.query.filter_by(student_id=user.id).all()}

    return render_template("courses.html", user=user, courses=courses, enrolled_ids=enrolled_ids)


@app.route("/course/<int:course_id>")
@login_required
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    user = current_user()

    has_access = False
    if user.role == "admin" or (user.role == "teacher" and course.teacher_id == user.id):
        has_access = True
    elif user.role == "student":
        has_access = (
            Enrollment.query.filter_by(student_id=user.id, course_id=course.id).first() is not None
        )

    if not course.is_published and not has_access:
        flash("Курс недоступен.", "error")
        return redirect(url_for("courses_list"))

    return render_template("course_detail.html", user=user, course=course, has_access=has_access)


@app.route("/student")
@role_required("student")
def student_panel():
    user = current_user()
    enrollments = Enrollment.query.filter_by(student_id=user.id).all()
    enrolled_ids = [e.course_id for e in enrollments]
    my_courses = Course.query.filter(Course.id.in_(enrolled_ids)).all() if enrolled_ids else []
    orders = Order.query.filter_by(student_id=user.id).order_by(Order.id.desc()).all()
    return render_template("student.html", user=user, my_courses=my_courses, orders=orders)


@app.route("/buy/<int:course_id>", methods=["POST"])
@role_required("student")
def buy_course(course_id):
    user = current_user()
    course = Course.query.get_or_404(course_id)

    existing = Enrollment.query.filter_by(student_id=user.id, course_id=course.id).first()
    if existing:
        flash("Курс уже куплен.", "success")
        return redirect(url_for("course_detail", course_id=course.id))

    order = Order(student_id=user.id, course_id=course.id, amount=course.price)
    db.session.add(order)
    db.session.commit()

    return redirect(url_for("mbank_pay", order_id=order.id))


@app.route("/mbank/pay/<int:order_id>", methods=["GET", "POST"])
@role_required("student")
def mbank_pay(order_id):
    user = current_user()
    order = Order.query.get_or_404(order_id)

    if order.student_id != user.id:
        flash("Нет доступа к оплате заказа.", "error")
        return redirect(url_for("student_panel"))

    if request.method == "POST":
        if order.status == "paid":
            return redirect(url_for("student_panel"))

        order.status = "paid"
        order.paid_at = datetime.utcnow()
        order.mbank_ref = f"MB-{uuid.uuid4().hex[:10].upper()}"

        enrollment = Enrollment.query.filter_by(student_id=user.id, course_id=order.course_id).first()
        if not enrollment:
            enrollment = Enrollment(student_id=user.id, course_id=order.course_id)
            db.session.add(enrollment)

        db.session.commit()
        flash("Оплата через MBank подтверждена. Курс открыт.", "success")
        return redirect(url_for("course_detail", course_id=order.course_id))

    return render_template("mbank_pay.html", user=user, order=order)


@app.route("/videos/<path:filename>")
@login_required
def videos(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.errorhandler(413)
def too_large(_):
    flash("Файл слишком большой. Максимум: 500MB.", "error")
    return redirect(request.referrer or url_for("teacher_panel"))


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
