# GPGC Nowshera College Management SaaS — deployment-prepared build

A browser-based college-management application foundation with tenant-scoped records, role checks, CSRF protection, password hashing, login throttling, security headers, and production WSGI/container configuration. **This is not yet certified or verified as production-ready for real institutional/student data.** It requires institutional requirements validation, integration/security testing, and a deployment smoke test before rollout.

## Current modules
- Authentication and role-based access
- College-scoped data records
- Student admissions
- Courses and course registration
- Attendance
- Examinations and results (grade thresholds are placeholders and must be approved by the college)
- Fee invoices and payment records
- Dashboard summaries

## Roles
- `admin`: all modules
- `admissions`: admissions, courses, registration
- `teacher`: courses, attendance, results
- `exam_officer`: exams and results
- `accounts`: invoices and payments

## Local development (Windows PowerShell)
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set a unique SECRET_KEY and INITIAL_ADMIN_PASSWORD.
py -c "from app import init_demo; init_demo()"
py run.py
```
Open `http://127.0.0.1:5000`.

The initial admin email is `admin@gpgc.local`. The password is the value of `INITIAL_ADMIN_PASSWORD`; if that variable is not set, the local demo fallback is `ChangeMe123!`. Never use the fallback password for an internet-facing deployment.

## Deployment preparation
- `wsgi.py` is the WSGI entry point (`gunicorn wsgi:app`).
- `Dockerfile` provides a non-root container build.
- `render.yaml` describes a Render web service and managed PostgreSQL database.
- `/health` is the health-check endpoint.
- Configure `APP_ENV=production`, a strong unique `SECRET_KEY`, and a managed database URL in the host's environment settings.
- Set `INITIAL_ADMIN_PASSWORD` to a unique strong password before creating the initial administrator. Run `python -c "from app import init_demo; init_demo()"` in the deployed service's shell/one-off job if available; do not publish the demo credentials.
- `BOOTSTRAP_DB=true` enables automatic table creation for initial bootstrap. For a maintained production deployment, introduce and review versioned migrations before schema changes; do not rely on automatic table creation as a migration strategy.

A hosting account must be authorized by the owner before a public deployment can be created. This repository configuration does not mean the application is already online.

## Database
SQLite is for local learning and development only. Use managed PostgreSQL or MySQL for a hosted installation. PostgreSQL URLs supplied as `postgres://` are normalized to `postgresql+psycopg://`.

## Important go-live checklist
Do not load real student data until all items are completed and accepted by the college:
- Requirements workshops and approval of roles, admissions rules, grading, fee policy, and reporting formats.
- Admin-only staff provisioning, account deactivation, secure password reset, and MFA/SSO decision.
- Versioned database migrations and tested backup/restore procedure.
- Audit trails for sensitive record access and changes.
- Formal tenant-boundary/security tests, dependency scanning, and independent security review.
- Pagination/search, editing and controlled deletion, CSV/PDF reports, official fee challans/receipts, transcript exports, and validation of all cross-record references.
- Privacy/data-retention policy, access review, operational monitoring, alerting, incident response, and documented recovery objectives.
- HTTPS, managed secrets, least-privilege database credentials, backups, and load/acceptance testing.
- User acceptance testing with authorized college staff using synthetic data first.

## Architecture
Browser UI → Flask application → SQLAlchemy models → managed PostgreSQL/MySQL. Each operational model carries `college_id`; routes scope record queries to the signed-in user's college. Preserve and test those tenant filters in every new route.
