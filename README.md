# ClassNotes — BAF Shaheen College Dhaka

A note-sharing web app for BAF Shaheen College Dhaka (bafsd.edu.bd, EIIN-107858).
Students and teachers
upload photos of class notes organised by class → section → subject → chapter,
so classmates can revise before exams and catch up on missed classes.

Built with Flask, SQLAlchemy (SQLite), Flask-Login, Flask-WTF and Pillow.

Two frontends share the same backend and security rules:

- **React SPA** (Vite + React Router + Tailwind) at **`/app`**, talking to the
  JSON API under `/api/*`. Auth stays on the HttpOnly session cookie;
  mutating calls send an `X-CSRFToken` header.
- **Server-rendered Jinja2 pages** (Tailwind CDN) at the original URLs — kept
  fully working as a fallback and for quick admin use.

### Frontend development

```bash
cd frontend
npm install
npm run dev     # dev server on :5173, proxies /api + /image to Flask on :5000
npm run build   # writes frontend/dist, which Flask serves at /app
```

The built `frontend/dist` is committed, so the VPS does not need Node —
just `git pull` and restart. Rebuild locally after frontend changes.

## Roles

| Role | Created by | Can do |
|---|---|---|
| Super Admin | `scripts/seed_admin.py` | Everything: classes, sections, subjects, users, assignments |
| Class Teacher | Super Admin | View their class+section's students & notes, add students to their own section, reset student passwords, moderate notes |
| Subject Teacher | Super Admin | Manage chapters of assigned subjects, upload **Official** notes |
| Student | Super Admin (single or CSV import) or their Class Teacher | View/upload notes in their own class+section only |

There is **no self-registration** — all accounts are issued top-down and every
new account must change its password on first login.

## Local setup

```bash
# 1. Create and activate a virtualenv
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
copy .env.example .env          # cp on Linux
# edit .env: set a long random SECRET_KEY

# 4. Create the database
flask --app run.py db upgrade   # if migrations/ exists
# or, first time from scratch:
python -c "from app import create_app; from app.extensions import db; app=create_app(); ctx=app.app_context(); ctx.push(); db.create_all()"

# 5. Seed the first Super Admin (prompts for a password)
python scripts/seed_admin.py admin "Your Name"

# 6. Run
python run.py
# open http://127.0.0.1:5000
```

### First steps after logging in as Super Admin

1. **Manage classes** → add e.g. "Class 9".
2. **Manage sections** → add "A" under Class 9.
3. **Manage users** → create a Subject Teacher.
4. **Manage subjects** → add "Physics" for Class 9 — A and assign the teacher.
5. The teacher logs in, changes password, creates chapters, uploads notes.
6. Create students (singly or via **Import students (CSV)** — columns
   `login_id, full_name[, password]`; generated passwords are shown once).

## Security notes

- All access scope is enforced server-side on every request; a student can only
  see notes (and images) of their own class+section — guessed URLs return 403.
- Uploads are validated by content (Pillow), re-encoded (EXIF and any embedded
  payloads stripped), stored under random uuid4 names **outside** the web root,
  and served only through a scope-checked route with `X-Content-Type-Options: nosniff`.
- Passwords hashed with Werkzeug (scrypt). Login rate-limited. CSRF protection
  on all forms. Session cookies `HttpOnly` + `SameSite=Lax` (+`Secure` in prod).
- Sessions are bound to the password hash: changing or resetting a password
  immediately invalidates every other session for that account.
- Security headers on all responses: CSP, `X-Frame-Options: DENY`, `nosniff`,
  `Referrer-Policy`, `Permissions-Policy`, HSTS over HTTPS.
- Rate limits on login, password change, uploads, votes and reports.
  Decompression-bomb guard (max 64 MP) on image decoding.
- In production set `PROXY_FIX=1` in `.env` (with the Nginx config below) so
  rate limiting sees real client IPs and HTTPS is detected correctly.

## Deploying on a VPS (Contabo, Ubuntu, Gunicorn + Nginx)

```bash
# as a non-root user, in /srv/classnotes
sudo apt update && sudo apt install -y python3-venv nginx
git clone <your-repo> /srv/classnotes && cd /srv/classnotes
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set SECRET_KEY (e.g. python -c "import secrets;print(secrets.token_hex(32))")
                       # set SESSION_COOKIE_SECURE=1 and PROXY_FIX=1
python -c "from app import create_app; from app.extensions import db; app=create_app(); ctx=app.app_context(); ctx.push(); db.create_all()"
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

Do **not** expose the `uploads/` directory via Nginx — images are deliberately
served through the Flask scope-check route only.

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
├── utils/
│   ├── security.py  role + scope checks
│   └── images.py    validate, re-encode, thumbnail
└── templates/
scripts/seed_admin.py
uploads/             created at runtime; never web-served directly
```

## Branding

The official college crest (from bafsd.edu.bd) lives in `app/static/img/`:
`logo_official.png` is the full-resolution original; `logo.png` (256px) and
`favicon.png` (64px) are the optimized copies actually served. If the college
updates its logo, replace `logo_official.png` and regenerate the two sizes
with Pillow (crop to `getbbox()`, then `thumbnail`).

## Phase 2 features

- **Points & leaderboard** — students earn +10 per upload, +2 per upvote
  received, +1 per unique download of their note. Tiers: Newcomer →
  Contributor (50) → Achiever (150) → Champion (300). Per-class leaderboard
  at `/leaderboard` (students and class teachers). Only students earn points.
- **Upvotes** — one per user per note; no self-votes; removing an upvote
  removes the points.
- **Reports & moderation** — any user can report a note (wrong info /
  inappropriate / unreadable / other + comment). The class teacher of that
  section and the Super Admin review reports at `/teacher/reports` and can
  hide the note, delete it, or dismiss the report. Hidden notes vanish from
  students (lists, search, direct URLs → 404) but stay visible to moderators
  with an unhide option.

Not yet built: notifications, most-downloaded rankings.
