# Test Plan

## Objective

Verify that the event registration system satisfies its functional requirements and provides enough evidence for coursework submission.

## Test levels

### Unit tests

Purpose:

- validate pure business rules
- validate security helpers
- validate service responses for edge cases

Examples:

- password hashing and verification
- duplicate registration prevention
- capacity enforcement

### Integration and API tests

Purpose:

- verify routes, cookies, database changes, and role checks

Examples:

- register then login
- register for event then cancel
- admin can create event
- normal user cannot access admin routes

### End-to-end tests with Playwright

Purpose:

- verify critical user flows through the browser UI

Smoke set:

- login as seeded student and redirect to dashboard
- open a dedicated event detail page
- register and cancel a registration from the detail page

Critical regression set:

- admin creates event
- forgot password updates credentials
- attendee visibility restricted to admins

## Entry criteria

- app starts successfully
- seeded data available
- no unresolved blocker on current sprint stories

## Exit criteria

- all unit and integration tests pass
- all smoke tests pass
- no blocker or critical defects open for demo scope

## Environment

- local development on Python 3.13
- SQLite for lightweight reproducible testing
- GitHub Actions for CI
- Chromium via Playwright for E2E

## Evidence to archive

- unittest output
- Playwright HTML report
- screenshots for failed tests if any
- traceability matrix
- defect log
