import os

from flask import Flask, send_from_directory
from flask_cors import CORS
from sqlalchemy import text

from database import db, get_database_uri
from routes import api_bp


def ensure_schema_compatibility(app: Flask):
    """Apply minimal schema updates for local SQLite without external migration tools."""
    if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        return

    result = db.session.execute(text("PRAGMA table_info(courses)"))
    columns = {row[1] for row in result.fetchall()}
    if "admin_id" not in columns:
        db.session.execute(text("ALTER TABLE courses ADD COLUMN admin_id INTEGER"))
        db.session.commit()


def create_app() -> Flask:
    app = Flask(__name__, static_folder="../static", template_folder="../frontend")
    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

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
