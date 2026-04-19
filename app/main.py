from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Cookie, Depends, FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.database import Database
from app.schemas import (
    AdminAnalyticsOutput,
    AttendeeOutput,
    EventInput,
    EventOutput,
    ForgotPasswordInput,
    IssueReportInput,
    IssueReportOutput,
    LoginInput,
    MessageOutput,
    NotificationListOutput,
    OwnedEventCreateInput,
    OwnedEventManagementOutput,
    OwnedEventRegistrationRemovalInput,
    PasswordChangeInput,
    RegistrationInput,
    UserCreate,
    UserOutput,
    UserTicketOutput,
    UserUpdateInput,
    WalletOverviewOutput,
    WalletTopUpConfirmOutput,
    WalletTopUpInput,
    WalletTopUpOutput,
)
from app.services import EventRegistrationService, ServiceError


def _label_for_field(loc: list[object] | tuple[object, ...]) -> str:
    field_name = str(loc[-1]) if loc else "field"
    return field_name.replace("_", " ").capitalize()


def _summarize_validation_error(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Invalid request."

    first_error = errors[0]
    field_label = _label_for_field(first_error.get("loc", []))
    error_type = first_error.get("type", "")
    context = first_error.get("ctx") or {}
    message = first_error.get("msg", "Invalid request.")

    if error_type == "missing":
        return f"{field_label} is required."
    if error_type == "string_too_short":
        return f"{field_label} must be at least {context.get('min_length', 1)} characters."
    if error_type == "string_too_long":
        return f"{field_label} must be at most {context.get('max_length', 1)} characters."
    if message.startswith("Value error, "):
        return message.replace("Value error, ", "", 1)
    return message


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings.from_env()
    database = Database(active_settings.mongo_uri, active_settings.mongo_db_name, use_mock=active_settings.use_mock_db)
    service = EventRegistrationService(database)
    static_dir = Path(__file__).resolve().parent / "static"

    def page_response(filename: str) -> FileResponse:
        return FileResponse(
            static_dir / filename,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        service.initialize(seed_demo=active_settings.seed_demo)
        try:
            yield
        finally:
            database.close()

    app = FastAPI(title="Event Registration System", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.state.settings = active_settings
    app.state.service = service

    def get_service(request: Request) -> EventRegistrationService:
        return request.app.state.service

    def optional_user(
        request: Request,
        session_token: str | None = Cookie(default=None),
    ) -> dict | None:
        service = get_service(request)
        if not session_token:
            return None
        return service.get_user_by_token(session_token)

    def require_user(user: dict | None = Depends(optional_user)) -> dict:
        if user is None:
            raise ServiceError(401, "UNAUTHORIZED", "Authentication required.")
        return user

    def require_admin(user: dict = Depends(require_user)) -> dict:
        if user["role"] != "admin":
            raise ServiceError(403, "FORBIDDEN", "Admin access required.")
        return user

    @app.exception_handler(ServiceError)
    async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": _summarize_validation_error(exc),
                    "details": exc.errors(),
                }
            },
        )

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return page_response("index.html")

    @app.get("/dashboard", include_in_schema=False)
    async def dashboard_page() -> FileResponse:
        return page_response("dashboard.html")

    @app.get("/admin/manager", include_in_schema=False)
    async def admin_manager_page(_: dict = Depends(require_admin)) -> FileResponse:
        return page_response("dashboard.html")

    @app.get("/account", include_in_schema=False)
    async def account_page() -> FileResponse:
        return page_response("account.html")

    @app.get("/account/billing", include_in_schema=False)
    async def account_billing_page() -> FileResponse:
        return page_response("billing.html")

    @app.get("/account/security", include_in_schema=False)
    async def account_security_page() -> FileResponse:
        return page_response("security.html")

    @app.get("/activity", include_in_schema=False)
    async def activity_page() -> FileResponse:
        return page_response("activity.html")

    @app.get("/aboutus", include_in_schema=False)
    async def aboutus_page() -> FileResponse:
        return page_response("aboutus.html")

    @app.get("/admin/analytics", include_in_schema=False)
    async def admin_analytics_page(_: dict = Depends(require_admin)) -> FileResponse:
        return page_response("admin-analytics.html")

    @app.get("/events/{event_id}/view", include_in_schema=False)
    async def event_detail_page(event_id: int) -> FileResponse:
        return page_response("event-detail.html")

    @app.get("/health", response_model=MessageOutput)
    async def healthcheck() -> dict[str, str]:
        return {"message": "ok"}

    @app.post("/api/auth/register", response_model=UserOutput, status_code=status.HTTP_201_CREATED)
    async def register(payload: UserCreate, service: EventRegistrationService = Depends(get_service)) -> dict:
        return service.register_user(
            payload.name,
            payload.email,
            payload.password,
            payload.date_of_birth,
            payload.country,
            payload.province,
            payload.district,
            payload.ward,
            payload.street_address,
            payload.phone_country_code,
            payload.phone_country_label,
            payload.phone_country_flag,
            payload.phone_local_number,
        )

    @app.post("/api/auth/forgot-password", response_model=MessageOutput)
    async def forgot_password(
        payload: ForgotPasswordInput,
        service: EventRegistrationService = Depends(get_service),
    ) -> dict[str, str]:
        service.reset_password(payload.email, payload.date_of_birth, payload.new_password)
        return {"message": "Password updated successfully."}

    @app.post("/api/auth/login", response_model=UserOutput)
    async def login(
        payload: LoginInput,
        response: Response,
        service: EventRegistrationService = Depends(get_service),
    ) -> dict:
        user = service.authenticate(payload.email, payload.password)
        token = service.create_session(user["id"])
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            samesite="lax",
            secure=False,
        )
        return user

    @app.post("/api/auth/logout", response_model=MessageOutput)
    async def logout(
        response: Response,
        service: EventRegistrationService = Depends(get_service),
        session_token: str | None = Cookie(default=None),
    ) -> dict[str, str]:
        if session_token:
            service.logout(session_token)
        response.delete_cookie("session_token")
        return {"message": "Logged out."}

    @app.get("/api/me", response_model=UserOutput)
    async def get_me(user: dict = Depends(require_user)) -> dict:
        return user

    @app.get("/api/me/notifications", response_model=NotificationListOutput)
    async def get_my_notifications(
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> dict:
        return service.list_notifications(user["id"])

    @app.post("/api/me/notifications/read-all", response_model=MessageOutput)
    async def mark_my_notifications_read(
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> dict[str, str]:
        return service.mark_notifications_read(user["id"])

    @app.post("/api/me/issues", response_model=IssueReportOutput, status_code=status.HTTP_201_CREATED)
    async def create_my_issue_report(
        payload: IssueReportInput,
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> dict:
        return service.create_issue_report(user["id"], payload.model_dump())

    @app.put("/api/me", response_model=UserOutput)
    async def update_me(
        payload: UserUpdateInput,
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> dict:
        return service.update_user_profile(user["id"], payload.model_dump())

    @app.get("/api/me/registrations", response_model=list[UserTicketOutput])
    async def get_my_registrations(
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> list[dict]:
        return service.list_user_registrations(user["id"])

    @app.get("/api/me/wallet", response_model=WalletOverviewOutput)
    async def get_my_wallet(
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> dict:
        return service.get_wallet_overview(user["id"])

    @app.post("/api/me/wallet/top-up", response_model=WalletTopUpOutput)
    async def top_up_my_wallet(
        payload: WalletTopUpInput,
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> dict:
        return service.top_up_wallet(user["id"], payload.amount, payload.provider, payload.note)

    @app.post("/api/me/wallet/top-up/confirm", response_model=WalletTopUpConfirmOutput)
    async def confirm_my_wallet_top_up(
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> dict:
        return service.confirm_top_up_wallet(user["id"])

    @app.post("/api/me/change-password", response_model=UserOutput)
    async def change_my_password(
        payload: PasswordChangeInput,
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> dict:
        return service.change_password(user["id"], payload.current_password, payload.new_password)

    @app.get("/api/me/owned-events", response_model=list[EventOutput])
    async def get_my_owned_events(
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> list[dict]:
        return service.list_owned_events(user["id"])

    @app.post("/api/me/owned-events", response_model=EventOutput, status_code=status.HTTP_201_CREATED)
    async def create_my_owned_event(
        payload: OwnedEventCreateInput,
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> dict:
        return service.create_owned_event(user["id"], payload.model_dump())

    @app.put("/api/me/owned-events/{event_id}", response_model=EventOutput)
    async def update_my_owned_event(
        event_id: int,
        payload: OwnedEventCreateInput,
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> dict:
        return service.update_owned_event(user["id"], event_id, payload.model_dump())

    @app.delete("/api/me/owned-events/{event_id}", response_model=MessageOutput)
    async def delete_my_owned_event(
        event_id: int,
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> dict[str, str]:
        service.delete_owned_event(user["id"], event_id)
        return {"message": "Owned event deleted."}

    @app.get("/api/me/owned-events/{event_id}/management", response_model=OwnedEventManagementOutput)
    async def get_my_owned_event_management(
        event_id: int,
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> dict:
        return service.get_owned_event_management(user["id"], event_id)

    @app.post("/api/me/owned-events/{event_id}/registrations/{registration_user_id}/remove", response_model=OwnedEventManagementOutput)
    async def remove_owned_event_registration(
        event_id: int,
        registration_user_id: int,
        payload: OwnedEventRegistrationRemovalInput,
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> dict:
        return service.remove_owned_event_registration(user["id"], event_id, registration_user_id, payload.model_dump())

    @app.get("/api/events", response_model=list[EventOutput])
    async def list_events(
        service: EventRegistrationService = Depends(get_service),
        user: dict | None = Depends(optional_user),
    ) -> list[dict]:
        user_id = None if user is None else user["id"]
        return service.list_events(user_id=user_id)

    @app.get("/api/events/{event_id}", response_model=EventOutput)
    async def get_event(
        event_id: int,
        service: EventRegistrationService = Depends(get_service),
        user: dict | None = Depends(optional_user),
    ) -> dict:
        user_id = None if user is None else user["id"]
        return service.get_event(event_id, user_id=user_id)

    @app.post("/api/events/{event_id}/register", response_model=EventOutput)
    async def register_event(
        event_id: int,
        payload: RegistrationInput | None = None,
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> dict:
        return service.register_for_event(user["id"], event_id, None if payload is None else payload.model_dump())

    @app.delete("/api/events/{event_id}/register", response_model=EventOutput)
    async def cancel_event_registration(
        event_id: int,
        service: EventRegistrationService = Depends(get_service),
        user: dict = Depends(require_user),
    ) -> dict:
        return service.cancel_registration(user["id"], event_id)

    @app.get("/api/events/{event_id}/registrations", response_model=list[AttendeeOutput])
    async def get_attendees(
        event_id: int,
        service: EventRegistrationService = Depends(get_service),
        _: dict = Depends(require_admin),
    ) -> list[dict]:
        return service.list_attendees(event_id)

    @app.get("/api/admin/events", response_model=list[EventOutput])
    async def list_admin_events(
        service: EventRegistrationService = Depends(get_service),
        _: dict = Depends(require_admin),
    ) -> list[dict]:
        return service.list_admin_events()

    @app.post("/api/admin/events/{event_id}/approve", response_model=EventOutput)
    async def approve_event_request(
        event_id: int,
        service: EventRegistrationService = Depends(get_service),
        _: dict = Depends(require_admin),
    ) -> dict:
        return service.approve_event_request(event_id)

    @app.post("/api/admin/events/{event_id}/reject", response_model=EventOutput)
    async def reject_event_request(
        event_id: int,
        service: EventRegistrationService = Depends(get_service),
        _: dict = Depends(require_admin),
    ) -> dict:
        return service.reject_event_request(event_id)

    @app.post("/api/admin/events", response_model=EventOutput, status_code=status.HTTP_201_CREATED)
    async def create_event(
        payload: EventInput,
        service: EventRegistrationService = Depends(get_service),
        admin: dict = Depends(require_admin),
    ) -> dict:
        return service.create_event(admin["id"], payload.model_dump())

    @app.put("/api/admin/events/{event_id}", response_model=EventOutput)
    async def update_event(
        event_id: int,
        payload: EventInput,
        service: EventRegistrationService = Depends(get_service),
        _: dict = Depends(require_admin),
    ) -> dict:
        return service.update_event(event_id, payload.model_dump())

    @app.delete("/api/admin/events/{event_id}", response_model=MessageOutput)
    async def delete_event(
        event_id: int,
        service: EventRegistrationService = Depends(get_service),
        _: dict = Depends(require_admin),
    ) -> dict[str, str]:
        service.delete_event(event_id)
        return {"message": "Event deleted."}

    @app.get("/api/admin/issues", response_model=list[IssueReportOutput])
    async def get_admin_issue_reports(
        service: EventRegistrationService = Depends(get_service),
        _: dict = Depends(require_admin),
    ) -> list[dict]:
        return service.list_issue_reports()

    @app.get("/api/admin/analytics", response_model=AdminAnalyticsOutput)
    async def get_admin_analytics(
        service: EventRegistrationService = Depends(get_service),
        _: dict = Depends(require_admin),
    ) -> dict:
        return service.get_admin_analytics()

    return app


app = create_app()
