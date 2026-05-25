from auth import (
    create_user,

    get_user_by_email,

    verify_password,

    make_session_token,
)


def validate_password_length(
    password: str,
):
    """
    Validate bcrypt limits.

    bcrypt supports up to
    72 bytes.

    Returns:

        (
            valid,
            message
        )
    """

    length = len(
        password.encode(
            "utf-8"
        )
    )

    if length > 72:

        return (
            False,

            (
                "Password too long "
                "(max 72 bytes)."
            ),
        )

    return (
        True,
        None,
    )


def email_exists(
    email: str,
):
    """
    Check if email already
    exists.
    """

    user = get_user_by_email(
        email
    )

    return user is not None


def register_user(
    email: str,

    password: str,
):
    """
    Register user and create
    session token.

    Returns:

    {
        user_id,
        token
    }
    """

    valid, error = (
        validate_password_length(
            password
        )
    )

    if not valid:

        return {

            "success":
                False,

            "error":
                error,
        }

    if email_exists(
        email
    ):

        return {

            "success":
                False,

            "error":
                (
                    "Email already "
                    "registered."
                ),
        }

    user_id = create_user(
        email,
        password,
    )

    token = make_session_token(
        user_id
    )

    return {

        "success":
            True,

        "user_id":
            user_id,

        "token":
            token,
    }


def authenticate(
    email: str,

    password: str,
):
    """
    Authenticate user.

    Returns:

    {
        success,
        token
    }
    """

    user = get_user_by_email(
        email
    )

    if not user:

        return {

            "success":
                False,

            "error":
                (
                    "Invalid email "
                    "or password."
                ),
        }

    valid = verify_password(
        password,

        user[
            "password_hash"
        ],
    )

    if not valid:

        return {

            "success":
                False,

            "error":
                (
                    "Invalid email "
                    "or password."
                ),
        }

    token = make_session_token(
        user["id"]
    )

    return {

        "success":
            True,

        "user":
            user,

        "token":
            token,
    }


def create_session(
    token: str,
):
    """
    Build cookie metadata.
    """

    return {

        "session":
            token,

        "httponly":
            True,

        "samesite":
            "lax",
    }
