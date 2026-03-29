# Project Scope

## Problem statement

The project addresses the need for a centralized and verifiable event registration system. Manual or fragmented event registration often leads to duplicate reservations, unclear seat tracking, delayed updates, and poor moderation of user-submitted events.

## Roles

- `user`: browse events, reserve tickets, manage profile and billing, review activity, submit event requests, and receive notifications
- `admin`: all user capabilities plus manage events, moderate event requests, inspect attendee data, and view analytics

## Functional scope

### In scope

- account registration, login, logout, and forgot password
- structured account profile with address, phone, date of birth, and avatar
- event dashboard and event detail pages
- event images, location, schedule, and ticket pricing display
- ticket reservation with quantity selection
- five-ticket limit per account per event
- reservation cancellation and registration history
- balance top-up through QR flow and transaction history
- duplicate reservation prevention and seat capacity enforcement
- account detail, billing, and security pages
- `Your activity` page for joined events and user event requests
- user event request creation, update, and deletion
- admin approval and rejection of user event requests
- admin CRUD for published events
- attendee list for admin
- notification bell for request lifecycle updates and near-event reminders
- map-based location validation for event submission forms
- basic admin analytics

### Out of scope

- external payment gateway integration
- email delivery and email-based notification sending
- realtime chat or websocket messaging
- recommendation engine
- mobile application
- multi-tenant deployment

## Non-functional scope

- clear validation and human-readable error messages
- repeatable local and CI-based test execution
- automated smoke coverage for main workflows
- evidence mapping from requirements to tests
- UI sufficient for end-to-end verification and coursework demo

## Definition of done

A story is done only when:

- acceptance criteria are written
- backend and front-end behavior are implemented
- backend tests pass
- Playwright coverage exists for critical UI flows when applicable
- the feature is demoable in the local or staging workflow
- related documentation and verification evidence are updated when required
