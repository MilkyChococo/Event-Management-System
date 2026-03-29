# Event Registration System

EventHub Verify is a Software Verification coursework project that combines a working event registration platform with Agile and testing evidence.

It currently includes:

- a complete user-facing event registration flow
- admin moderation and event management
- MongoDB persistence for users, events, registrations, billing, and notifications
- automated verification with backend tests and Playwright E2E flows
- submission artifacts for SRS, test planning, and traceability

## Current scope

### User scope

- sign up, sign in, sign out, and forgot password
- structured profile data with date of birth, address, phone, and avatar
- event dashboard, event detail, and account pages
- reserve tickets with quantity selection and a five-ticket limit per account per event
- cancel reservations and review registration history
- balance top-up by QR flow and transaction history
- notification bell with request lifecycle updates and event reminders
- event request submission, resubmission, and withdrawal from `Your activity`
- location selection with a map-based location picker

### Admin scope

- create, update, and delete events
- moderate user event requests through approve and reject actions
- inspect attendee data
- review basic analytics and operational summaries
- receive notifications for newly submitted or updated user event requests

### Verification scope

- backend unit and service tests with `unittest`
- API-level tests with FastAPI `TestClient`
- Playwright smoke and critical end-to-end tests
- Agile artifacts such as backlog, sprint plan, traceability matrix, and defect log

## Technology stack

- Frontend: HTML, CSS, vanilla JavaScript
- Backend: FastAPI
- Database: MongoDB
- Test automation: Playwright, `unittest`, FastAPI `TestClient`
- CI/CD: GitHub Actions

## Repository layout

```text
app/                    FastAPI application
app/static/             Browser UI and front-end scripts
docs/                   Coursework artifacts and report material
tests/                  Backend unit and API tests
tests/e2e/              Playwright smoke and critical flows
.github/workflows/      CI/CD pipelines
```

## Coursework deliverables

Starter and working documents are stored in `docs/`:

- [project-scope](docs/project-scope.md)
- [architecture](docs/architecture.md)
- [backlog](docs/backlog.md)
- [sprint-plan](docs/sprint-plan.md)
- [test-plan](docs/test-plan.md)
- [traceability-matrix](docs/traceability-matrix.md)
- [defect-log](docs/defect-log.md)
- [demo-checklist](docs/demo-checklist.md)
- [report-outline](docs/report-outline.md)

These can be extended into the mid-term package: report, SRS, test specification, test report, and presentation material.

## Recommended workflow

1. Read [project-scope](docs/project-scope.md).
2. Review [backlog](docs/backlog.md) and [sprint-plan](docs/sprint-plan.md).
3. Start MongoDB locally or with Docker Compose.
4. Run the app locally.
5. Run backend tests.
6. Run Playwright smoke tests.
7. Use the generated reports and docs as coursework evidence.

## Local setup

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload --port 10104
```

Open `http://127.0.0.1:10104`.

The app expects MongoDB at `APP_MONGO_URI` and uses `APP_MONGO_DB_NAME` as the database name.
For host-side tools and local scripts, `.env` points to `mongodb://127.0.0.1:10105`.
Inside Docker Compose, the app connects through `APP_MONGO_DOCKER_URI`, which resolves to `mongodb://mongo:10105`.
If an email is not found in MongoDB, the account is treated as non-existent.

### Docker Compose

```bash
docker compose up --build
```

Services:

- app: `http://127.0.0.1:10104`
- mongo-express: `http://127.0.0.1:8088`

### Backend tests

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Tests use `mongomock`, so they do not require a live MongoDB server.

### Playwright

```bash
cmd /c npm install
cmd /c npx playwright install chromium
cmd /c npm run test:e2e:smoke
```

## Demo accounts

If `APP_SEED_DEMO=true`, the app creates:

- `admin@example.com` / `Admin123!`
- `student@example.com` / `Student123!`

## CI/CD

`ci.yml` runs:

- backend unit and API tests
- app startup smoke check
- Playwright smoke tests

`nightly.yml` is prepared for a fuller regression schedule.
