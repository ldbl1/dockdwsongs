from datetime import datetime, timedelta
from typing import Optional, Union

from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.models import User, UserSession
from app.security import generate_session_token, verify_password


SESSION_COOKIE_NAME = "dwsongs_session"
SESSION_DAYS = 14


def any_user_exists(db: Session) -> bool:
    return db.query(User).first() is not None


def any_admin_exists(db: Session) -> bool:
    admin = (
        db.query(User)
        .filter(User.is_admin.is_(True))
        .filter(User.is_active.is_(True))
        .first()
    )
    return admin is not None


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    if not username:
        return None

    normalized_username = username.strip().lower()
    return db.query(User).filter(User.username == normalized_username).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)

    if not user or not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    user.last_login_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return user


def create_session(db: Session, user: User, request: Optional[Request] = None) -> UserSession:
    token = generate_session_token()
    expires_at = datetime.utcnow() + timedelta(days=SESSION_DAYS)

    user_agent = None
    ip_address = None

    if request is not None:
        user_agent = request.headers.get("user-agent")
        if request.client:
            ip_address = request.client.host

    session = UserSession(
        user_id=user.id,
        session_token=token,
        expires_at=expires_at,
        is_active=True,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def attach_session_cookie(response, session: UserSession) -> None:
    max_age = SESSION_DAYS * 24 * 60 * 60
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.session_token,
        httponly=True,
        max_age=max_age,
        samesite="lax",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, httponly=True, samesite="lax")


def get_session_token_from_request(request: Request) -> Optional[str]:
    return request.cookies.get(SESSION_COOKIE_NAME)


def get_session_by_token(db: Session, token: Optional[str]) -> Optional[UserSession]:
    if not token:
        return None

    session = (
        db.query(UserSession)
        .filter(UserSession.session_token == token)
        .filter(UserSession.is_active.is_(True))
        .first()
    )

    if not session:
        return None

    if session.expires_at <= datetime.utcnow():
        session.is_active = False
        db.commit()
        return None

    return session


def get_current_user(request: Request, db: Session) -> Optional[User]:
    token = get_session_token_from_request(request)
    session = get_session_by_token(db, token)

    if not session:
        return None

    user = session.user

    if not user or not user.is_active:
        return None

    return user


def logout_current_session(request: Request, db: Session) -> None:
    token = get_session_token_from_request(request)
    session = get_session_by_token(db, token)

    if session:
        session.is_active = False
        db.commit()


def require_login(request: Request, db: Session) -> Union[User, RedirectResponse]:
    if not any_user_exists(db):
        return RedirectResponse("/setup", status_code=303)

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    return user


def require_admin(request: Request, db: Session) -> Union[User, RedirectResponse]:
    user_or_response = require_login(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return user_or_response

    user = user_or_response

    if not user.is_admin:
        return RedirectResponse("/", status_code=303)

    return user


def user_can_see_download(user: User, download) -> bool:
    if user.is_admin:
        return True
    return download.user_id == user.id


def build_login_redirect_response() -> RedirectResponse:
    return RedirectResponse("/login", status_code=303)


def build_home_redirect_response() -> RedirectResponse:
    return RedirectResponse("/", status_code=303)
