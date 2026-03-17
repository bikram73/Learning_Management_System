from datetime import datetime
import hmac
from io import BytesIO
import secrets

from flask import Blueprint, current_app, jsonify, request
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import and_, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from database import db
from models import Course, Enrollment, Lesson, PaymentRequest, Progress, User
from services.auth_service import (
    admin_required,
    generate_token,
    hash_password,
    is_valid_admin_code,
    login_required,
    verify_password,
)
from services.email_service import (
    queue_welcome_email,
    send_course_paid_email,
    send_course_payment_email,
    send_new_lesson_email,
    send_pending_welcome_emails,
    send_welcome_course_email,
)


api_bp = Blueprint("api", __name__, url_prefix="/api")


def _course_to_dict(course: Course):
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "instructor": course.instructor,
        "thumbnail": course.thumbnail,
        "pricing_type": course.pricing_type,
        "price": float(course.price or 0),
        "admin_id": course.admin_id,
        "lessons_count": len(course.lessons),
        "created_at": course.created_at.isoformat(),
    }


def _lesson_to_dict(lesson: Lesson, completed_ids: set[int] | None = None, unlocked_ids: set[int] | None = None):
    return {
        "id": lesson.id,
        "course_id": lesson.course_id,
        "title": lesson.title,
        "video_url": lesson.video_url,
        "lesson_order": lesson.lesson_order,
        "created_at": lesson.created_at.isoformat(),
        "completed": lesson.id in (completed_ids or set()),
        "unlocked": lesson.id in (unlocked_ids or set()),
    }


def _require_json_body(required_fields: list[str]):
    data = request.get_json(silent=True) or {}
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return None, jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    return data, None, None


def _is_enrolled(user_id: int, course_id: int) -> bool:
    return (
        Enrollment.query.filter(
            and_(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        ).first()
        is not None
    )


def _completed_lesson_ids(user_id: int, course_id: int) -> set[int]:
    rows = (
        db.session.query(Progress.lesson_id)
        .join(Lesson, Lesson.id == Progress.lesson_id)
        .filter(
            Progress.user_id == user_id,
            Progress.completed.is_(True),
            Lesson.course_id == course_id,
        )
        .all()
    )
    return {row[0] for row in rows}


def _unlocked_lesson_ids(course: Course, completed_ids: set[int]) -> set[int]:
    unlocked: set[int] = set()
    ordered_lessons = sorted(course.lessons, key=lambda l: l.lesson_order)
    for index, lesson in enumerate(ordered_lessons):
        if index == 0:
            unlocked.add(lesson.id)
            continue
        previous_lesson = ordered_lessons[index - 1]
        if previous_lesson.id in completed_ids:
            unlocked.add(lesson.id)
    return unlocked


def _ensure_admin_owns_course(user: User, course: Course):
    if user.role == "admin" and course.admin_id != user.id:
        return jsonify({"error": "You can only access your own courses"}), 403
    return None


def _is_valid_cron_request() -> bool:
    expected_secret = current_app.config.get("CRON_SECRET", "")
    if not expected_secret:
        return False

    provided_secret = (
        request.headers.get("X-Cron-Secret", "")
        or request.args.get("token", "")
    )
    return bool(provided_secret) and hmac.compare_digest(provided_secret, expected_secret)


def _normalize_thumbnail(value: str | None) -> str | None:
    thumbnail = (value or "").strip()
    if not thumbnail:
        return None

    # Current schema stores thumbnail as VARCHAR(500). If UI sends large base64 data,
    # keep course creation working by ignoring the oversized thumbnail instead of failing.
    if len(thumbnail) > 500:
        return None

    return thumbnail


def _ensure_courses_columns_runtime():
    inspector = inspect(db.engine)
    if "courses" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("courses")}
    is_sqlite = current_app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite")

    statements = []
    if "admin_id" not in columns:
        statements.append(
            "ALTER TABLE courses ADD COLUMN admin_id INTEGER"
            if is_sqlite
            else "ALTER TABLE courses ADD COLUMN IF NOT EXISTS admin_id INTEGER"
        )
    if "pricing_type" not in columns:
        statements.append(
            "ALTER TABLE courses ADD COLUMN pricing_type TEXT DEFAULT 'free'"
            if is_sqlite
            else "ALTER TABLE courses ADD COLUMN IF NOT EXISTS pricing_type VARCHAR(20) DEFAULT 'free'"
        )
    if "price" not in columns:
        statements.append(
            "ALTER TABLE courses ADD COLUMN price REAL"
            if is_sqlite
            else "ALTER TABLE courses ADD COLUMN IF NOT EXISTS price DOUBLE PRECISION"
        )

    for statement in statements:
        db.session.execute(text(statement))
    if statements:
        db.session.commit()


def _build_payment_receipt_pdf(user: User, course: Course, receipt_number: str, amount: float) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setTitle(f"LMS Receipt {receipt_number}")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(48, height - 64, "Learning Management System")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(48, height - 94, "Payment Receipt")

    y = height - 140
    rows = [
        ("Receipt Number", receipt_number),
        ("Student Name", user.name),
        ("Student Email", user.email),
        ("Course", course.title),
        ("Amount", f"USD {amount:.2f}"),
        ("Paid At", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")),
    ]
    for label, value in rows:
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(48, y, f"{label}:")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(170, y, str(value))
        y -= 24

    pdf.save()
    buffer.seek(0)
    return buffer.read()


@api_bp.get("/health")
def health_check():
    return jsonify({"status": "ok"})


@api_bp.post("/signup/student")
def student_signup():
    data, error_response, status = _require_json_body(["name", "email", "password"])
    if error_response:
        return error_response, status

    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(
        name=data["name"].strip(),
        email=email,
        password_hash=hash_password(data["password"]),
        role="student",
    )
    db.session.add(user)
    db.session.flush()
    queue_welcome_email(user)
    db.session.commit()

    return jsonify({"message": "Student account created successfully"}), 201


@api_bp.post("/signup/admin")
def admin_signup():
    data, error_response, status = _require_json_body(["name", "email", "password", "admin_code"])
    if error_response:
        return error_response, status

    if not is_valid_admin_code(data["admin_code"]):
        return jsonify({"error": "Invalid admin secret code"}), 403

    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(
        name=data["name"].strip(),
        email=email,
        password_hash=hash_password(data["password"]),
        role="admin",
    )
    db.session.add(user)
    db.session.flush()
    queue_welcome_email(user)
    db.session.commit()

    return jsonify({"message": "Admin account created successfully"}), 201


@api_bp.post("/login")
def login():
    data, error_response, status = _require_json_body(["email", "password"])
    if error_response:
        return error_response, status

    email = data["email"].strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user or not verify_password(user.password_hash, data["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    token = generate_token(user)
    return jsonify(
        {
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
            },
        }
    )


@api_bp.post("/logout")
@login_required
def logout():
    # JWT is stateless; client deletes token to logout.
    return jsonify({"message": "Logout successful"})


@api_bp.get("/internal/send-pending-welcome-emails")
def process_pending_welcome_emails():
    if not _is_valid_cron_request():
        return jsonify({"error": "Unauthorized cron request"}), 401

    try:
        summary = send_pending_welcome_emails(limit=25)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({
        "message": "Welcome email queue processed",
        **summary,
    })


@api_bp.get("/courses")
def list_courses():
    courses = Course.query.order_by(Course.created_at.desc()).all()
    return jsonify([_course_to_dict(course) for course in courses])


@api_bp.get("/course/<int:course_id>")
def get_course(course_id: int):
    course = Course.query.get_or_404(course_id)
    return jsonify(_course_to_dict(course))


@api_bp.post("/course")
@admin_required
def create_course():
    data, error_response, status = _require_json_body(["title", "description", "instructor"])
    if error_response:
        return error_response, status

    pricing_type = (data.get("pricing_type") or "free").strip().lower()
    if pricing_type not in {"free", "paid"}:
        return jsonify({"error": "pricing_type must be 'free' or 'paid'"}), 400

    price = None
    if pricing_type == "paid":
        try:
            price = float(data.get("price", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "price must be a number"}), 400
        if price <= 0:
            return jsonify({"error": "price must be greater than 0 for paid courses"}), 400

    course = Course(
        title=data["title"].strip(),
        description=data["description"].strip(),
        instructor=data["instructor"].strip(),
        thumbnail=_normalize_thumbnail(data.get("thumbnail")),
        pricing_type=pricing_type,
        price=price,
        admin_id=request.current_user.id,
    )
    db.session.add(course)
    try:
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        error_text = str(exc).lower()
        if any(key in error_text for key in ["pricing_type", "price", "admin_id", "column"]):
            try:
                _ensure_courses_columns_runtime()
                db.session.add(course)
                db.session.commit()
            except SQLAlchemyError as retry_exc:
                db.session.rollback()
                return jsonify({"error": f"Failed to create course after schema repair: {str(retry_exc)}"}), 500
        else:
            return jsonify({"error": f"Failed to create course: {str(exc)}"}), 500

    return jsonify({"message": "Course created", "course": _course_to_dict(course)}), 201


@api_bp.put("/course/<int:course_id>")
@admin_required
def update_course(course_id: int):
    course = Course.query.get_or_404(course_id)
    ownership_error = _ensure_admin_owns_course(request.current_user, course)
    if ownership_error:
        return ownership_error

    data = request.get_json(silent=True) or {}

    if "title" in data and data["title"].strip():
        course.title = data["title"].strip()
    if "description" in data and data["description"].strip():
        course.description = data["description"].strip()
    if "instructor" in data and data["instructor"].strip():
        course.instructor = data["instructor"].strip()
    if "thumbnail" in data:
        course.thumbnail = _normalize_thumbnail(data.get("thumbnail"))
    if "pricing_type" in data:
        pricing_type = (data.get("pricing_type") or "").strip().lower()
        if pricing_type not in {"free", "paid"}:
            return jsonify({"error": "pricing_type must be 'free' or 'paid'"}), 400
        course.pricing_type = pricing_type
        if pricing_type == "free":
            course.price = None
    if "price" in data:
        if course.pricing_type != "paid":
            return jsonify({"error": "Price can be set only for paid courses"}), 400
        try:
            parsed_price = float(data.get("price", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "price must be a number"}), 400
        if parsed_price <= 0:
            return jsonify({"error": "price must be greater than 0 for paid courses"}), 400
        course.price = parsed_price

    db.session.commit()
    return jsonify({"message": "Course updated", "course": _course_to_dict(course)})


@api_bp.delete("/course/<int:course_id>")
@admin_required
def delete_course(course_id: int):
    course = Course.query.get_or_404(course_id)
    ownership_error = _ensure_admin_owns_course(request.current_user, course)
    if ownership_error:
        return ownership_error

    db.session.delete(course)
    db.session.commit()
    return jsonify({"message": "Course deleted"})


@api_bp.get("/course/<int:course_id>/lessons")
@login_required
def course_lessons(course_id: int):
    course = Course.query.get_or_404(course_id)
    current_user = request.current_user

    ownership_error = _ensure_admin_owns_course(current_user, course)
    if ownership_error:
        return ownership_error

    if current_user.role == "student" and not _is_enrolled(current_user.id, course.id):
        return jsonify({"error": "Enroll in course to view lessons"}), 403

    completed_ids = _completed_lesson_ids(current_user.id, course.id)
    unlocked_ids = set(lesson.id for lesson in course.lessons)
    if current_user.role == "student":
        unlocked_ids = _unlocked_lesson_ids(course, completed_ids)

    lessons = [_lesson_to_dict(lesson, completed_ids, unlocked_ids) for lesson in course.lessons]
    return jsonify(lessons)


@api_bp.post("/lesson")
@admin_required
def create_lesson():
    data, error_response, status = _require_json_body(["course_id", "title", "video_url", "lesson_order"])
    if error_response:
        return error_response, status

    course = Course.query.get(data["course_id"])
    if not course:
        return jsonify({"error": "Course not found"}), 404

    ownership_error = _ensure_admin_owns_course(request.current_user, course)
    if ownership_error:
        return ownership_error

    lesson = Lesson(
        course_id=course.id,
        title=data["title"].strip(),
        video_url=data["video_url"].strip(),
        lesson_order=int(data["lesson_order"]),
    )
    db.session.add(lesson)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Lesson order must be unique per course"}), 409

    enrolled_students = (
        User.query.join(Enrollment, Enrollment.user_id == User.id)
        .filter(Enrollment.course_id == course.id, User.role == "student")
        .all()
    )
    for student in enrolled_students:
        try:
            send_new_lesson_email(student, course, lesson)
        except Exception:
            # Do not block lesson creation if email sending fails.
            pass

    return jsonify({"message": "Lesson created", "lesson": _lesson_to_dict(lesson)}), 201


@api_bp.put("/lesson/<int:lesson_id>")
@admin_required
def update_lesson(lesson_id: int):
    lesson = Lesson.query.get_or_404(lesson_id)
    ownership_error = _ensure_admin_owns_course(request.current_user, lesson.course)
    if ownership_error:
        return ownership_error

    data = request.get_json(silent=True) or {}

    if "title" in data and data["title"].strip():
        lesson.title = data["title"].strip()
    if "video_url" in data and data["video_url"].strip():
        lesson.video_url = data["video_url"].strip()
    if "lesson_order" in data:
        lesson.lesson_order = int(data["lesson_order"])

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Lesson order must be unique per course"}), 409

    return jsonify({"message": "Lesson updated", "lesson": _lesson_to_dict(lesson)})


@api_bp.delete("/lesson/<int:lesson_id>")
@admin_required
def delete_lesson(lesson_id: int):
    lesson = Lesson.query.get_or_404(lesson_id)
    ownership_error = _ensure_admin_owns_course(request.current_user, lesson.course)
    if ownership_error:
        return ownership_error

    db.session.delete(lesson)
    db.session.commit()
    return jsonify({"message": "Lesson deleted"})


@api_bp.post("/enroll")
@login_required
def enroll_course():
    data, error_response, status = _require_json_body(["course_id"])
    if error_response:
        return error_response, status

    current_user = request.current_user
    if current_user.role != "student":
        return jsonify({"error": "Only students can enroll in courses"}), 403

    course = Course.query.get(data["course_id"])
    if not course:
        return jsonify({"error": "Course not found"}), 404

    if _is_enrolled(current_user.id, course.id):
        return jsonify({"message": "Already enrolled"}), 200

    if course.pricing_type == "paid":
        pending_request = (
            PaymentRequest.query.filter_by(
                user_id=current_user.id,
                course_id=course.id,
                status="pending",
            )
            .order_by(PaymentRequest.created_at.desc())
            .first()
        )
        if not pending_request:
            pending_request = PaymentRequest(
                user_id=current_user.id,
                course_id=course.id,
                token=secrets.token_urlsafe(32),
                amount=float(course.price or 0),
                status="pending",
            )
            db.session.add(pending_request)
            db.session.commit()

        try:
            send_course_payment_email(current_user, course, pending_request.token)
        except Exception as exc:
            return jsonify({"error": f"Failed to send payment email: {str(exc)}"}), 500

        return jsonify({
            "message": "This is a paid course. A payment link has been sent to your email.",
            "payment_required": True,
        }), 202

    enrollment = Enrollment(user_id=current_user.id, course_id=course.id)
    db.session.add(enrollment)
    db.session.commit()

    try:
        send_welcome_course_email(current_user, course)
    except Exception:
        pass

    return jsonify({"message": "Enrollment successful"}), 201


@api_bp.get("/payment/<string:token>")
def get_payment_request(token: str):
    payment_request = PaymentRequest.query.filter_by(token=token).first()
    if not payment_request or payment_request.status != "pending":
        return jsonify({"error": "Payment link is invalid or expired"}), 404

    return jsonify({
        "course_id": payment_request.course.id,
        "course_title": payment_request.course.title,
        "amount": float(payment_request.amount),
        "email_hint": payment_request.user.email,
    })


@api_bp.post("/payment/<string:token>/complete")
def complete_payment(token: str):
    data, error_response, status = _require_json_body(["email", "password"])
    if error_response:
        return error_response, status

    payment_request = PaymentRequest.query.filter_by(token=token).first()
    if not payment_request or payment_request.status != "pending":
        return jsonify({"error": "Payment link is invalid or expired"}), 404

    email = data["email"].strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user or user.id != payment_request.user_id:
        return jsonify({"error": "Email does not match this payment request"}), 403
    if not verify_password(user.password_hash, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    course = payment_request.course
    if not _is_enrolled(user.id, course.id):
        db.session.add(Enrollment(user_id=user.id, course_id=course.id))

    receipt_number = f"LMS-{payment_request.id}-{int(datetime.utcnow().timestamp())}"
    payment_request.status = "paid"
    payment_request.receipt_number = receipt_number
    payment_request.paid_at = datetime.utcnow()
    db.session.commit()

    receipt_pdf = _build_payment_receipt_pdf(user, course, receipt_number, float(payment_request.amount))

    try:
        send_course_paid_email(user, course, receipt_number, receipt_pdf)
    except Exception:
        pass

    try:
        send_welcome_course_email(user, course)
    except Exception:
        pass

    return jsonify({
        "message": "Payment successful. You are now enrolled in the course.",
        "receipt_number": receipt_number,
    })


@api_bp.get("/my-courses")
@login_required
def my_courses():
    current_user = request.current_user
    if current_user.role == "admin":
        courses = (
            Course.query.filter_by(admin_id=current_user.id)
            .order_by(Course.created_at.desc())
            .all()
        )
        return jsonify([_course_to_dict(course) for course in courses])

    enrollment_rows = (
        Enrollment.query.filter_by(user_id=current_user.id)
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )
    courses = [row.course for row in enrollment_rows]
    return jsonify([_course_to_dict(course) for course in courses])


@api_bp.post("/lesson/complete")
@login_required
def mark_lesson_complete():
    data, error_response, status = _require_json_body(["lesson_id"])
    if error_response:
        return error_response, status

    current_user = request.current_user
    if current_user.role != "student":
        return jsonify({"error": "Only students can complete lessons"}), 403

    lesson = Lesson.query.get(data["lesson_id"])
    if not lesson:
        return jsonify({"error": "Lesson not found"}), 404

    if not _is_enrolled(current_user.id, lesson.course_id):
        return jsonify({"error": "Enroll in course first"}), 403

    completed_ids = _completed_lesson_ids(current_user.id, lesson.course_id)
    unlocked_ids = _unlocked_lesson_ids(lesson.course, completed_ids)
    if lesson.id not in unlocked_ids:
        return jsonify({"error": "This lesson is locked. Complete previous lessons first."}), 409

    progress = Progress.query.filter_by(user_id=current_user.id, lesson_id=lesson.id).first()
    if not progress:
        progress = Progress(user_id=current_user.id, lesson_id=lesson.id)
        db.session.add(progress)

    progress.completed = True
    progress.completed_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"message": "Lesson marked complete"})


@api_bp.get("/course-progress/<int:course_id>")
@login_required
def course_progress(course_id: int):
    course = Course.query.get_or_404(course_id)
    current_user = request.current_user

    if current_user.role == "student" and not _is_enrolled(current_user.id, course.id):
        return jsonify({"error": "Enroll in course first"}), 403

    total_lessons = len(course.lessons)
    completed_ids = _completed_lesson_ids(current_user.id, course.id)
    completed_count = len(completed_ids)
    percentage = int((completed_count / total_lessons) * 100) if total_lessons else 0

    return jsonify(
        {
            "course_id": course.id,
            "total_lessons": total_lessons,
            "completed_lessons": completed_count,
            "percentage": percentage,
        }
    )


@api_bp.get("/profile")
@login_required
def get_profile():
    user = request.current_user
    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
    })


@api_bp.put("/profile")
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}
    user = request.current_user
    changed = False

    new_name = data.get("name", "").strip()
    if new_name:
        user.name = new_name
        changed = True

    new_email = data.get("email", "").strip().lower()
    if new_email and new_email != user.email:
        if User.query.filter_by(email=new_email).first():
            return jsonify({"error": "Email already in use by another account"}), 409
        user.email = new_email
        changed = True

    new_password = data.get("password", "").strip()
    if new_password:
        if len(new_password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        user.password_hash = hash_password(new_password)
        changed = True

    if changed:
        db.session.commit()

    return jsonify({
        "message": "Profile updated successfully" if changed else "No changes made",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
    })


@api_bp.delete("/profile")
@login_required
def delete_profile():
    user = request.current_user
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "Account deleted successfully"})
