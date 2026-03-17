from datetime import datetime

from database import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reset_sent_at = db.Column(db.DateTime, nullable=True)

    created_courses = db.relationship("Course", back_populates="owner_admin", cascade="all, delete-orphan")
    enrollments = db.relationship("Enrollment", back_populates="user", cascade="all, delete-orphan")
    progress_items = db.relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    welcome_email_jobs = db.relationship("WelcomeEmailJob", back_populates="user", cascade="all, delete-orphan")
    payment_requests = db.relationship("PaymentRequest", back_populates="user", cascade="all, delete-orphan")


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    instructor = db.Column(db.String(120), nullable=False)
    thumbnail = db.Column(db.String(500), nullable=True)
    pricing_type = db.Column(db.String(20), nullable=False, default="free")
    price = db.Column(db.Float, nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    owner_admin = db.relationship("User", back_populates="created_courses")
    lessons = db.relationship(
        "Lesson",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Lesson.lesson_order",
    )
    enrollments = db.relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    payment_requests = db.relationship("PaymentRequest", back_populates="course", cascade="all, delete-orphan")


class Lesson(db.Model):
    __tablename__ = "lessons"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    video_url = db.Column(db.String(500), nullable=False)
    lesson_order = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    course = db.relationship("Course", back_populates="lessons")
    progress_items = db.relationship("Progress", back_populates="lesson", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("course_id", "lesson_order", name="uq_course_lesson_order"),
    )


class Enrollment(db.Model):
    __tablename__ = "enrollments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    enrolled_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="enrollments")
    course = db.relationship("Course", back_populates="enrollments")

    __table_args__ = (
        db.UniqueConstraint("user_id", "course_id", name="uq_user_course_enrollment"),
    )


class Progress(db.Model):
    __tablename__ = "progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False)
    completed = db.Column(db.Boolean, nullable=False, default=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="progress_items")
    lesson = db.relationship("Lesson", back_populates="progress_items")

    __table_args__ = (
        db.UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson_progress"),
    )


class WelcomeEmailJob(db.Model):
    __tablename__ = "welcome_email_jobs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    template_name = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    attempts = db.Column(db.Integer, nullable=False, default=0)
    last_error = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="welcome_email_jobs")


class PaymentRequest(db.Model):
    __tablename__ = "payment_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    token = db.Column(db.String(120), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    receipt_number = db.Column(db.String(80), nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="payment_requests")
    course = db.relationship("Course", back_populates="payment_requests")
