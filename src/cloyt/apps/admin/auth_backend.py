import datetime
from hmac import compare_digest

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import Response


class AdminAuthBackend(AuthenticationBackend):
    def __init__(
            self,
            secret_key: str,
            username: str,
            password: str,
            login_duration: datetime.timedelta,
    ):
        self.username = username
        self.password = password
        self.login_duration = login_duration

        super().__init__(secret_key)

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username, password = form["username"], form["password"]

        is_valid = (
            compare_digest(username, self.username)
            and compare_digest(password, self.password)
        )
        if is_valid:
            request.session["logged_in_at"] = \
                datetime.datetime.now().timestamp()
            request.session["username"] = username
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> Response | bool:
        if "logged_in_at" not in request.session:
            return False
        logged_in_at = datetime.datetime.fromtimestamp(
            request.session["logged_in_at"],
        )
        if (
            (datetime.datetime.now() - logged_in_at) >= self.login_duration
            or request.session["username"] != self.username
        ):
            request.session.clear()
            return False
        return True
