# ClassNotes

An open-source, self-hostable note-sharing web app for schools and colleges.
Students and teachers upload photos of class notes organised by
**class → section → subject → chapter**, so classmates can revise before exams
and catch up on missed classes.

Fork it, change the branding, and run it for your own institution.

> Reference deployment: **BAF Shaheen College, Dhaka** — see [Make it yours](#make-it-yours) to rebrand it for any school or college.

Built with Flask, SQLAlchemy (SQLite), Flask-Login, Flask-WTF and Pillow.

## Features

- **Role-based access** with a clear chain of command (Super Admin → Class Teacher → Subject Teacher → Student).
- **Organised notes** — class → section → subject → chapter → note (one or more photos per note). Official teacher notes are pinned above student notes.
- **Photo uploads** validated, re-encoded and served securely.
- **Search** within a student's own class+section.
- **Points & leaderboard** — students earn points for contributing notes.
- **Reports & moderation** — flag bad notes; class teachers and admins review them.
- **Two frontends, one backend** — a React SPA and server-rendered pages, sharing the same security rules.

## Roles

Accounts are issued **top-down** — there is **no public self-registration**, and every new account must change its password on first login.

| Role | Created by | Can do |
| --- | --- | --- |
| **Super Admin** | `scripts/seed_admin.py` | Everything: classes, sections, subjects, users, assignments |
| **Class Teacher** | Super Admin | View their class+section's students & notes, add students to their section, reset student passwords, moderate notes |
| **Subject Teacher** | Super Admin | Manage chapters of assigned subjects, upload **Official** notes |
| **Student** | Super Admin (single or CSV import) or their Class Teacher | View/upload notes in their own class+section only |

## Tech stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.11+, Flask |
| Database | SQLite via SQLAlchemy (portable to Postgres) |
| Auth | Flask-Login + Werkzeug (scrypt) |
| Forms/CSRF | Flask-WTF |
| Images | Pillow |
| Migrations | Flask-Migrate (Alembic) |
| Frontend | React (Vite + React Router + Tailwind) SPA at `/app`, plus Jinja2 server-rendered pages as a fallback |
| Production | Gunicorn + Nginx |

## Quick start (local)

```bash
# 1. Clone
git clone https://github.com/Rajib-Mahmud/baf-shaheen-classnotes.git
cd baf-shaheen-classnotes

# 2. Virtualenv
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 3. Install
pip install -r requirements.txt

# 4. Configure
copy .env.example .env          # cp on Linux/macOS
# edit .env and set a long random SECRET_KEY:
#   python -c "import secrets; print(secrets.token_hex(32))"

# 5. Create the database
flask --app run.py db upgrade

# 6. Seed the first Super Admin (prompts for a password)
python scripts/seed_admin.py admin "Your Name"

# 7. Run
python run.py
# open http://127.0.0.1:5000
```

### First steps as Super Admin

1. **Manage classes** → add e.g. "Class 9".
2. **Manage sections** → add "A" under Class 9.
3. **Manage users** → create a Subject Teacher.
4. **Manage subjects** → add "Physics" for Class 9 – A and assign the teacher.
5. The teacher logs in, changes password, creates chapters, uploads notes.
6. Create students singly or via **Import students (CSV)** — columns `login_id, full_name[, password]`; generated passwords are shown once.

### Frontend development

```bash
cd frontend
npm install
npm run dev     # dev server on :5173, proxies /api + /image to Flask on :5000
npm run build   # writes frontend/dist, which Flask serves at /app
```

The built `frontend/dist` is committed, so a server doesn't need Node — just `git pull` and restart. Rebuild locally after frontend changes.

## Make it yours

This project ships branded for BAF Shaheen College as an example. To run it for **your** institution:

1. **Name & text** — update the title and college name in the templates (`app/templates/base.html`) and in the React app (`frontend/src`).
2. **Logo** — replace the images in `app/static/img/`: drop in your institution's logo as `logo_official.png`, then regenerate the optimized copies with Pillow (crop to `getbbox()`, then `thumbnail` to 256px `logo.png` and 64px `favicon.png`).
3. **Classes & subjects** — everything else (classes, sections, subjects, chapters, users) is created at runtime from the admin panel, not hardcoded — so no code changes needed.
4. **License** — the MIT license only asks that you keep the original copyright notice; you're otherwise free to modify and deploy.

## Security notes

- All access scope is enforced server-side on every request; a student can only see notes and images of their own class+section — guessed URLs return 403.
- Uploads are validated by content (Pillow), re-encoded (EXIF and any embedded payloads stripped), stored under random uuid4 names **outside** the web root, and served only through a scope-checked route with `X-Content-Type-Options: nosniff`.
- Passwords hashed with Werkzeug (scrypt). Login rate-limited. CSRF protection on all forms. Session cookies `HttpOnly` + `SameSite=Lax` (+`Secure` in prod).
- Sessions are bound to the password hash: changing or resetting a password immediately invalidates every other session for that account.
- Security headers on all responses: CSP, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, HSTS over HTTPS.
- Rate limits on login, password change, uploads, votes and reports. Decompression-bomb guard (max 64 MP) on image decoding.
- In production set `PROXY_FIX=1` in `.env` (with the Nginx config below) so rate limiting sees real client IPs and HTTPS is detected correctly.
- The JSON API returns machine-readable errors (401/403/404/413/429/500), never HTML redirects, and is CSRF-protected via the `X-CSRFToken` header.

## Deploying on a VPS (Ubuntu, Gunicorn + Nginx)

```bash
# as a non-root user, in /srv/classnotes
sudo apt update && sudo apt install -y python3-venv nginx
git clone https://github.com/Rajib-Mahmud/baf-shaheen-classnotes.git /srv/classnotes && cd /srv/classnotes
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set SECRET_KEY, SESSION_COOKIE_SECURE=1, PROXY_FIX=1
flask --app run.py db upgrade
python scripts/seed_admin.py admin "Your Name"
```

`/etc/systemd/system/classnotes.service`:

```ini
[Unit]
Description=ClassNotes (Gunicorn)
After=network.target

[Service]
User=www-data
WorkingDirectory=/srv/classnotes
Environment="PATH=/srv/classnotes/.venv/bin"
ExecStart=/srv/classnotes/.venv/bin/gunicorn -w 3 -b 127.0.0.1:8000 run:app

[Install]
WantedBy=multi-user.target
```

`/etc/nginx/sites-available/classnotes`:

```nginx
server {
    listen 80;
    server_name your-domain.example;
    client_max_body_size 10m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/classnotes /etc/nginx/sites-enabled/
sudo systemctl enable --now classnotes
sudo systemctl restart nginx
# then add HTTPS: sudo apt install certbot python3-certbot-nginx && sudo certbot --nginx
```

Do **not** expose the `uploads/` directory via Nginx — images are deliberately served through the Flask scope-check route only.

## Project layout

```
app/
├── __init__.py      app factory, blueprints, forced-password-change hook
├── models.py        User, SchoolClass, Section, Subject, Chapter, Note, NoteImage
├── auth/            login, logout, change password
├── admin/           Super Admin CRUD + CSV import
├── teacher/         subject-teacher chapters, class-teacher dashboard
├── student/         dashboard → subject → chapter views
├── notes/           upload, note view/edit/delete, scoped image serving, search
├── api/             JSON API for the React SPA
├── utils/           security (role + scope checks), images (validate, re-encode)
└── templates/
frontend/            React SPA (Vite)
scripts/seed_admin.py
uploads/             created at runtime; never web-served directly
```

## Contributing

Contributions are welcome. Please open an issue to discuss a change before a large PR. Keep the server-side access checks intact — they are the core of the app's safety model. Run `pip-audit` and `npm audit` before submitting.

## License

Released under the [MIT License](LICENSE) — free to use, modify, and deploy, including for other institutions. Just keep the original copyright notice.

## Author

Built by **Rajib Mahmud** ([@Rajib-Mahmud](https://github.com/Rajib-Mahmud)).
