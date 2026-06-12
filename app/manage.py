import argparse
from datetime import datetime

from app.database import SessionLocal
from app.models import User
from app.security import generate_temporary_password, hash_password, is_valid_username, normalize_username, validate_password_strength


def get_user(db, username: str):
    return db.query(User).filter(User.username == normalize_username(username)).first()


def list_users(args):
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.id.asc()).all()
        if not users:
            print("No hay usuarios creados.")
            return
        for user in users:
            print(f"ID={user.id} username={user.username} admin={user.is_admin} active={user.is_active} must_change_password={user.must_change_password} last_login_at={user.last_login_at}")
    finally:
        db.close()


def create_user(args):
    db = SessionLocal()
    try:
        username = normalize_username(args.username)
        ok, msg = is_valid_username(username)
        if not ok:
            print(f"ERROR: {msg}")
            return
        if get_user(db, username):
            print(f"ERROR: Ya existe el usuario {username}")
            return
        password = generate_temporary_password() if args.generate else args.password
        ok, msg = validate_password_strength(password)
        if not ok:
            print(f"ERROR: {msg}")
            return
        user = User(username=username, password_hash=hash_password(password), is_admin=args.admin, is_active=True, must_change_password=args.must_change_password, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        db.add(user)
        db.commit()
        print(f"Usuario creado: {username}")
        if args.generate:
            print(f"Contraseña temporal: {password}")
    finally:
        db.close()


def reset_password(args):
    db = SessionLocal()
    try:
        user = get_user(db, args.username)
        if not user:
            print(f"ERROR: No existe el usuario {args.username}")
            return
        password = generate_temporary_password() if args.generate else args.password
        ok, msg = validate_password_strength(password)
        if not ok:
            print(f"ERROR: {msg}")
            return
        user.password_hash = hash_password(password)
        user.must_change_password = args.must_change_password
        user.updated_at = datetime.utcnow()
        db.commit()
        print(f"Contraseña actualizada para {user.username}")
        if args.generate:
            print(f"Contraseña temporal: {password}")
    finally:
        db.close()


def set_active(args):
    db = SessionLocal()
    try:
        user = get_user(db, args.username)
        if not user:
            print(f"ERROR: No existe el usuario {args.username}")
            return
        user.is_active = args.active
        user.updated_at = datetime.utcnow()
        db.commit()
        print(f"Usuario {user.username} activo={user.is_active}")
    finally:
        db.close()


def set_admin(args):
    db = SessionLocal()
    try:
        user = get_user(db, args.username)
        if not user:
            print(f"ERROR: No existe el usuario {args.username}")
            return
        user.is_admin = args.admin
        user.updated_at = datetime.utcnow()
        db.commit()
        print(f"Usuario {user.username} admin={user.is_admin}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(prog="python -m app.manage")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("list-users"); p.set_defaults(func=list_users)
    p = sub.add_parser("create-user"); p.add_argument("username"); p.add_argument("password", nargs="?", default=""); p.add_argument("--admin", action="store_true"); p.add_argument("--generate", action="store_true"); p.add_argument("--must-change-password", action="store_true"); p.set_defaults(func=create_user)
    p = sub.add_parser("reset-password"); p.add_argument("username"); p.add_argument("password", nargs="?", default=""); p.add_argument("--generate", action="store_true"); p.add_argument("--must-change-password", action="store_true"); p.set_defaults(func=reset_password)
    p = sub.add_parser("set-active"); p.add_argument("username"); g=p.add_mutually_exclusive_group(required=True); g.add_argument("--active", action="store_true"); g.add_argument("--inactive", action="store_true"); p.set_defaults(func=lambda a: set_active(argparse.Namespace(username=a.username, active=a.active and not a.inactive)))
    p = sub.add_parser("set-admin"); p.add_argument("username"); g=p.add_mutually_exclusive_group(required=True); g.add_argument("--admin", action="store_true"); g.add_argument("--no-admin", action="store_true"); p.set_defaults(func=lambda a: set_admin(argparse.Namespace(username=a.username, admin=a.admin and not a.no_admin)))
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
