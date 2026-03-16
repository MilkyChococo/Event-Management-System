# Event Registration System

This repository is a coursework starter for a Software Verification project.
It combines:

- a small but complete event registration system
- Agile delivery artifacts
- automated verification with unit, integration, and Playwright E2E tests
- CI/CD automation for repeatable evidence
- MongoDB persistence for easier account and event management

## Why this scope

The project stays intentionally small so the team can prove quality instead of building too many features.
Core scope:

- user registration and login
- event catalog and event detail
- register for an event
- cancel a registration
- capacity enforcement
- duplicate registration prevention
- admin event management
- attendee list for admins

## Repository layout

```text
app/                    FastAPI application
app/static/             Simple UI for browser and Playwright
docs/                   Coursework artifacts and Agile deliverables
tests/                  Unit and integration tests
tests/e2e/              Playwright smoke and critical flows
.github/workflows/      CI/CD pipelines
```

## Recommended workflow

1. Read [project-scope](docs/project-scope.md).
2. Read [backlog](docs/backlog.md) and [sprint-plan](docs/sprint-plan.md).
3. Start MongoDB locally or with Docker Compose.
4. Run the app locally.
5. Run backend tests.
6. Install Node dependencies and run Playwright tests.
7. Use the reports as submission evidence.

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
For host-side tools and local scripts, `.env` now points to `mongodb://127.0.0.1:10105`.
Inside Docker Compose, the app still connects through the internal service address stored in `APP_MONGO_DOCKER_URI`, which now resolves to `mongodb://mongo:10105`.
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

## Submission artifacts

The essential coursework artifacts already have starter versions:

- [project-scope](docs/project-scope.md)
- [architecture](docs/architecture.md)
- [backlog](docs/backlog.md)
- [sprint-plan](docs/sprint-plan.md)
- [test-plan](docs/test-plan.md)
- [traceability-matrix](docs/traceability-matrix.md)
- [defect-log](docs/defect-log.md)
- [demo-checklist](docs/demo-checklist.md)
- [report-outline](docs/report-outline.md)

## CI/CD

`ci.yml` runs:

- backend unit and integration tests
- app startup smoke check
- Playwright smoke tests

`nightly.yml` is prepared for a full regression schedule.
