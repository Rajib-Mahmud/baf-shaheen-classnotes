import hmac
import os

from flask import Flask, redirect, render_template, request, url_for
from flask_login import current_user

from config import Config

from .extensions import csrf, db, limiter, login_manager, migrate


_PLACEHOLDER_KEYS = {
    "dev-only-insecure-key",
    "change-me-to-a-long-random-string",
}


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if app.config["SECRET_KEY"] in _PLACEHOLDER_KEYS:
        import warnings

        warnings.warn(
            "SECRET_KEY is a known placeholder — set a random value in .env "
            "(python -c \"import secrets; print(secrets.token_hex(32))\"). "
            "Sessions signed with a guessable key can be forged.",
            stacklevel=1,
        )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Behind Nginx/another reverse proxy, trust one hop of X-Forwarded-*
    # so rate limiting sees real client IPs (not the proxy's) and
    # request.is_secure reflects the outer HTTPS connection.
    if os.environ.get("PROXY_FIX", "0") == "1":
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = None

    from .models import User

    @login_manager.user_loader
    def load_user(token):
        try:
            uid, key = token.split(".", 1)
            user = db.session.get(User, int(uid))
        except ValueError:
            return None
        if user is None or not user.is_active:
            return None
        # Constant-time compare; a stale key means the password changed
        # after this session was issued — treat it as logged out.
        if not hmac.compare_digest(user.session_key, key):
            return None
        return user

    from .admin.routes import admin_bp
    from .auth.routes import auth_bp
    from .notes.routes import notes_bp
    from .student.routes import student_bp
    from .teacher.routes import teacher_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(teacher_bp, url_prefix="/teacher")
    app.register_blueprint(student_bp)
    app.register_blueprint(notes_bp)

    @app.before_request
    def enforce_password_change():
        """A user flagged must_change_password can only reach the
        change-password and logout endpoints until they change it."""
        if not current_user.is_authenticated:
            return None
        if not current_user.must_change_password:
            return None
        allowed = {"auth.change_password", "auth.logout", "static"}
        if request.endpoint not in allowed:
            return redirect(url_for("auth.change_password"))
        return None

    @app.after_request
    def security_headers(response):
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "same-origin")
        h.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        # Tailwind CDN injects inline <style>; our small page scripts are
        # inline — hence 'unsafe-inline', but no external hosts beyond the
        # pinned CDN/font origins can load code.
        h.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )
        if request.is_secure:
            h.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app
