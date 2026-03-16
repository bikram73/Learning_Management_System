from functools import wraps
from typing import Callable

import jwt
from flask import current_app, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from models import User


ADMIN_SECRET_CODE = "ADMIN2026"


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def generate_token(user: User) -> str:
    payload = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
    }
    secret_key = current_app.config["SECRET_KEY"]
    return jwt.encode(payload, secret_key, algorithm="HS256")


def decode_token(token: str):
    secret_key = current_app.config["SECRET_KEY"]
    return jwt.decode(token, secret_key, algorithms=["HS256"])


def get_auth_token_from_header() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.replace("Bearer ", "", 1).strip()


def login_required(fn: Callable):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = get_auth_token_from_header()
        if not token:
            return jsonify({"error": "Missing or invalid authorization token"}), 401

        try:
            payload = decode_token(token)
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid or expired token"}), 401

        user = User.query.get(payload.get("user_id"))
        if not user:
            return jsonify({"error": "User not found"}), 401

        request.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn: Callable):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        user = request.current_user
        if user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)

    return wrapper


def is_valid_admin_code(code: str) -> bool:
    return code == ADMIN_SECRET_CODE
