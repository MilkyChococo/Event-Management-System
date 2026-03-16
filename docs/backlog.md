# Product Backlog

## Epic 1: Foundation

| ID | Story | Priority | Acceptance summary |
| --- | --- | --- | --- |
| US-01 | As a team, we want a repo skeleton so we can deliver incrementally. | High | Project starts locally, docs exist, CI prepared. |
| US-02 | As a developer, I want seeded demo data so I can verify flows quickly. | High | Demo accounts and sample events exist after startup. |

## Epic 2: Authentication

| ID | Story | Priority | Acceptance summary |
| --- | --- | --- | --- |
| US-03 | As a visitor, I want to create an account so I can use the system. | High | Unique email required, password stored securely, login works after registration. |
| US-04 | As a user, I want to log in and log out so my actions are protected. | High | Valid credentials create a session, invalid credentials fail cleanly, logout clears session. |
| US-04A | As a user, I want to reset my password so I can recover access. | High | Email and birth date can be used to set a new password. |

## Epic 3: Event Discovery

| ID | Story | Priority | Acceptance summary |
| --- | --- | --- | --- |
| US-05 | As a user, I want to view a list of events so I can choose what to join. | High | Events show key fields and remaining seats. |
| US-06 | As a user, I want to see event details so I can decide before registering. | High | Event detail shows description, time, location, remaining seats. |
| US-06A | As a user, I want event details on a dedicated page so the system feels like a real product flow. | High | View detail navigates to a separate page with image, price, and registration statistics. |

## Epic 4: Registration

| ID | Story | Priority | Acceptance summary |
| --- | --- | --- | --- |
| US-07 | As a user, I want to register for an event so I can reserve a seat. | High | Registration succeeds only when seats remain and user is authenticated. |
| US-08 | As a user, I want duplicate registration blocked so data stays correct. | High | Same user cannot register twice for one event. |
| US-09 | As a user, I want to cancel my registration so I can free my seat. | High | Cancellation removes only my registration and seats become available again. |

## Epic 5: Administration

| ID | Story | Priority | Acceptance summary |
| --- | --- | --- | --- |
| US-10 | As an admin, I want to create an event so new events can be published. | Medium | Valid event data creates a visible event. |
| US-11 | As an admin, I want to edit or delete an event so data stays current. | Medium | Updates persist, deleted events disappear from list. |
| US-12 | As an admin, I want to inspect attendees so I can monitor registrations. | Medium | Admin can view attendee names and emails for an event. |

## Epic 6: Account Profile

| ID | Story | Priority | Acceptance summary |
| --- | --- | --- | --- |
| US-13 | As a user, I want profile details collected at registration so my account is complete. | High | Registration stores full name, age, date of birth, permanent address, and phone number. |
| US-14 | As a user, I want to view my account profile from the top-right icon so I can inspect my information. | High | Account menu reveals profile access and logout; profile page shows the stored details. |
