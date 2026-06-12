import base64
import hashlib
import hmac
import secrets
import string


PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 260000
SALT_BYTES = 32
HASH_BYTES = 32


def hash_password(password: str) -> str:
    if password is None:
        raise ValueError("La contraseña no puede ser None")

    password_bytes = password.encode("utf-8")
    salt = secrets.token_bytes(SALT_BYTES)

    password_hash = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password_bytes,
        salt,
        PBKDF2_ITERATIONS,
        dklen=HASH_BYTES,
    )

    salt_b64 = base64.b64encode(salt).decode("ascii")
    hash_b64 = base64.b64encode(password_hash).decode("ascii")

    return f"pbkdf2_{PBKDF2_ALGORITHM}${PBKDF2_ITERATIONS}${salt_b64}${hash_b64}"


def verify_password(password: str, stored_hash: str) -> bool:
    if not password or not stored_hash:
        return False

    try:
        algorithm_name, iterations_text, salt_b64, expected_hash_b64 = stored_hash.split("$", 3)

        if algorithm_name != f"pbkdf2_{PBKDF2_ALGORITHM}":
            return False

        iterations = int(iterations_text)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected_hash = base64.b64decode(expected_hash_b64.encode("ascii"))

        actual_hash = hashlib.pbkdf2_hmac(
            PBKDF2_ALGORITHM,
            password.encode("utf-8"),
            salt,
            iterations,
            dklen=len(expected_hash),
        )

        return hmac.compare_digest(actual_hash, expected_hash)

    except Exception:
        return False


def generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def validate_password_strength(password: str) -> tuple[bool, str]:
    if not password:
        return False, "La contraseña no puede estar vacía."

    if len(password) < 10:
        return False, "La contraseña debe tener al menos 10 caracteres."

    if not any(char.islower() for char in password):
        return False, "La contraseña debe incluir al menos una letra minúscula."

    if not any(char.isupper() for char in password):
        return False, "La contraseña debe incluir al menos una letra mayúscula."

    if not any(char.isdigit() for char in password):
        return False, "La contraseña debe incluir al menos un número."

    return True, ""


def generate_temporary_password(length: int = 16) -> str:
    if length < 12:
        length = 12

    alphabet = string.ascii_lowercase + string.ascii_uppercase + string.digits + "!@#$%*-_"

    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        is_valid, _message = validate_password_strength(password)
        if is_valid:
            return password


def normalize_username(username: str) -> str:
    return (username or "").strip().lower()


def is_valid_username(username: str) -> tuple[bool, str]:
    username = normalize_username(username)

    if not username:
        return False, "El usuario no puede estar vacío."

    if len(username) < 3:
        return False, "El usuario debe tener al menos 3 caracteres."

    if len(username) > 40:
        return False, "El usuario no puede tener más de 40 caracteres."

    allowed = set(string.ascii_lowercase + string.digits + "._-")

    if any(char not in allowed for char in username):
        return False, "El usuario solo puede contener letras, números, punto, guion y guion bajo."

    return True, ""
