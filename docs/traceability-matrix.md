# Requirement Traceability Matrix

| Requirement ID | Story ID | Requirement summary | Test ID | Test type | Status |
| --- | --- | --- | --- | --- | --- |
| REQ-01 | US-03 | User can register with unique email. | API-01 | Integration | Pass |
| REQ-02 | US-04 | User can login and logout with session cookie. | API-02 | Integration | Pass |
| REQ-02 | US-04 | User can login and logout with session cookie. | E2E-01 | Playwright | Pass |
| REQ-03 | US-05 | User can view event list with remaining seats. | E2E-01 | Playwright | Pass |
| REQ-04 | US-06 | User can inspect event detail. | E2E-01 | Playwright | Pass |
| REQ-05 | US-07 | User can register when capacity remains. | SRV-01 | Unit | Pass |
| REQ-05 | US-07 | User can register when capacity remains. | API-05 | Integration | Pass |
| REQ-05 | US-07 | User can register when capacity remains. | E2E-02 | Playwright | Pass |
| REQ-06 | US-08 | User cannot register twice for same event. | SRV-02 | Unit | Pass |
| REQ-07 | US-09 | User can cancel own registration. | SRV-03 | Unit | Pass |
| REQ-07 | US-09 | User can cancel own registration. | API-07 | Integration | Pass |
| REQ-07 | US-09 | User can cancel own registration. | E2E-02 | Playwright | Pass |
| REQ-08 | US-10 | Admin can create event. | API-08 | Integration | Pass |
| REQ-08 | US-10 | Admin can create event. | E2E-03 | Playwright | Pass |
| REQ-09 | US-11 | Admin can update or delete event. | API-09 | Integration | Pass |
| REQ-10 | US-12 | Admin can inspect attendee list. | API-10 | Integration | Pass |
| REQ-11 | US-13 | Registration stores detailed account information. | API-01 | Integration | Pass |
| REQ-12 | US-04A | User can reset password with recovery information. | API-11 | Integration | Pass |
| REQ-13 | US-06A | View detail opens a dedicated event page with image and price. | E2E-01 | Playwright | Pass |
| REQ-14 | US-14 | Account icon opens access to profile and logout actions. | E2E-01 | Playwright | Pass |

## Status policy

- Planned: test defined but not executed
- Pass: test exists and latest execution passed
- Fail: test exists and latest execution failed
- Blocked: execution blocked by setup or defect
