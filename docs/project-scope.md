# Project Scope

## Problem statement

Build a small event registration system that allows users to browse events, register if seats are available, and cancel a registration. Administrators can manage events and inspect attendee lists.

## Roles

- user: browse events, register, cancel own registration
- admin: all user actions plus create, update, delete events and view attendees

## Functional scope

### In scope

- account registration
- login and logout
- forgot password with profile verification
- event listing
- event detail
- event image and ticket price display
- register for event
- cancel registration
- duplicate registration prevention
- seat capacity enforcement
- detailed account profile view
- admin CRUD for events
- attendee list for admin

### Out of scope

- payment
- email delivery
- QR code tickets
- event recommendation
- analytics dashboard
- multi-tenant deployment

## Non-functional scope

- clear validation and error messages
- repeatable test execution
- simple CI automation
- evidence mapping from requirements to tests
- enough UI for end-to-end verification

## Definition of done

A story is done only when:

- acceptance criteria are written
- backend logic is implemented
- backend tests pass
- Playwright test exists for critical UI flows when applicable
- code is merged to main through CI
- the story is demoable on staging or local demo environment
