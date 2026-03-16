# Architecture

## Architectural style

The project uses a lightweight monolith:

- FastAPI application for API and static file serving
- SQLite database for deterministic local execution
- plain HTML, CSS, and JavaScript for the browser layer
- Playwright for browser verification

This architecture is intentional for coursework:

- low setup overhead
- easy traceability from UI to API to data
- easy automated verification

## Main components

### app/main.py

- API routes
- dependency wiring
- error handling
- static entry point

### app/services.py

- business rules
- authentication flow
- event registration logic
- admin event management

### app/database.py

- SQLite schema
- connection factory

### app/static/

- single-page UI for manual demo
- stable selectors for Playwright

### tests/

- service tests for business rules
- API tests for route and session behavior
- Playwright tests for critical user flows

## Data model

### users

- id
- name
- email
- password_hash
- role
- created_at

### events

- id
- title
- description
- location
- start_at
- capacity
- created_by
- created_at
- updated_at

### registrations

- id
- user_id
- event_id
- created_at
- unique(user_id, event_id)

### sessions

- token
- user_id
- created_at

## Key business rules

- only authenticated users can register
- the same user cannot register twice for one event
- registration fails when capacity is exhausted
- cancellation returns the seat to the pool
- only admins can create, update, delete events, and inspect attendees

## Verification strategy by layer

- service tests prove core business rules
- API tests prove session, cookies, role checks, and route wiring
- Playwright proves critical browser flows

## Why not only Playwright

Browser tests alone do not isolate logic failures well and are slower.
For coursework defense, layered verification is stronger because you can explain:

- what rule is being tested
- where it is being tested
- why that level is appropriate

