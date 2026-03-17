import os

from flask import Flask, send_from_directory
from flask_cors import CORS
from sqlalchemy import inspect, text

from database import db, get_database_uri
from routes import api_bp


def load_env_file():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env_path = os.path.join(base_dir, ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def ensure_schema_compatibility(app: Flask):
    """Apply minimal schema updates for both SQLite and PostgreSQL without migration tools."""
    inspector = inspect(db.engine)
    
    is_sqlite = app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite")
    statements = []

    # Update courses table
    if "courses" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("courses")}
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

    # Update users table
    if "users" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "reset_sent_at" not in columns:
            statements.append(
                "ALTER TABLE users ADD COLUMN reset_sent_at DATETIME"
                if is_sqlite
                else "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_sent_at TIMESTAMP"
            )

    for statement in statements:
        db.session.execute(text(statement))
    if statements:
        db.session.commit()


def create_app() -> Flask:
    load_env_file()

    app = Flask(__name__, static_folder="../static", template_folder="../frontend")
    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
    app.config["APP_BASE_URL"] = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000")
    app.config["MAIL_HOST"] = os.getenv("MAIL_HOST", "")
    app.config["MAIL_PORT"] = os.getenv("MAIL_PORT", "587")
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "")
    app.config["MAIL_FROM"] = os.getenv("MAIL_FROM", "")
    app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "true")
    app.config["SUPPORT_EMAIL"] = os.getenv("SUPPORT_EMAIL", "support@example.com")
    app.config["CRON_SECRET"] = os.getenv("CRON_SECRET", "")

    CORS(app)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_schema_compatibility(app)

    app.register_blueprint(api_bp)

    @app.get("/")
    def home_page():
        return send_from_directory(app.template_folder, "index.html")

    @app.get("/<path:filename>")
    def frontend_pages(filename: str):
        # Serve static HTML pages from /frontend.
        if filename.endswith(".html"):
            return send_from_directory(app.template_folder, filename)
        return send_from_directory(app.static_folder, filename)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)