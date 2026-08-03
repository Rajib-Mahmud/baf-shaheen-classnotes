import hmac
import os

from flask import Flask, jsonify, redirect, render_template, request, url_for
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

    @login_manager.unauthorized_handler
    def unauthorized():
        # API callers get machine-readable 401s, never HTML redirects.
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": "Authentication required."}), 401
        return redirect(url_for("auth.login", next=request.full_path))

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
    from .api.routes import api_bp
    from .auth.routes import auth_bp
    from .notes.routes import notes_bp
    from .student.routes import student_bp
    from .teacher.routes import teacher_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(teacher_bp, url_prefix="/teacher")
    app.register_blueprint(student_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    # React SPA (frontend/dist, built with `npm run build`), served at /app.
    from flask import send_from_directory

    spa_dist = os.path.join(os.path.dirname(app.root_path), "frontend", "dist")

    @app.route("/app/", defaults={"path": ""})
    @app.route("/app/<path:path>")
    def spa(path):
        full = os.path.normpath(os.path.join(spa_dist, path))
        if path and full.startswith(os.path.normpath(spa_dist)) and os.path.isfile(full):
            return send_from_directory(spa_dist, path)
        return send_from_directory(spa_dist, "index.html")

    @app.before_request
    def enforce_password_change():
        """A user flagged must_change_password can only reach the
        change-password and logout endpoints until they change it."""
        if not current_user.is_authenticated:
            return None
        if not current_user.must_change_password:
            return None
        endpoint = request.endpoint or ""
        # API endpoints answer 428 JSON themselves; the SPA shell must load
        # so it can show its own change-password screen.
        if endpoint.startswith("api.") or endpoint == "spa":
            return None
        allowed = {"auth.change_password", "auth.logout", "static"}
        if endpoint not in allowed:
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

    def _error_response(status, template, message):
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": message}), status
        return render_template(template), status

    @app.errorhandler(403)
    def forbidden(e):
        return _error_response(403, "errors/403.html", "You don't have access to that.")

    @app.errorhandler(404)
    def not_found(e):
        return _error_response(404, "errors/404.html", "Not found.")

    @app.errorhandler(413)
    def too_large(e):
        return _error_response(413, "errors/413.html", "Upload too large — max 10 photos, 8 MB each.")

    @app.errorhandler(429)
    def rate_limited(e):
        return _error_response(429, "errors/429.html", "Too many requests — slow down and try again shortly.")

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return _error_response(500, "errors/500.html", "Something went wrong on our side.")

    return app
