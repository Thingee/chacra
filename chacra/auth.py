import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from chacra.config import CFG


security = HTTPBasic()


def authenticate(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
):
    correct_user = secrets.compare_digest(
        credentials.username.encode("utf8"),
        CFG.api_user.encode("utf8")
    )

    correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        CFG.api_key.encode("utf8")
    )

    if not (correct_user and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials
