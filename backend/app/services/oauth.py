from dataclasses import dataclass

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import get_settings
from app.models.enums import OAuthProvider


class OAuthValidationError(Exception):
    pass


@dataclass(frozen=True)
class OAuthProfile:
    provider: OAuthProvider
    subject: str
    email: str | None
    name: str | None = None


class OAuthProfileVerifier:
    async def verify(self, provider: OAuthProvider, access_token: str) -> OAuthProfile:
        if provider is OAuthProvider.GOOGLE:
            return self._verify_google(access_token)
        if provider is OAuthProvider.KAKAO:
            return await self._verify_kakao(access_token)
        raise OAuthValidationError("Unsupported OAuth provider")

    def _verify_google(self, google_id_token: str) -> OAuthProfile:
        client_ids = get_settings().google_client_id_list
        if not client_ids:
            raise OAuthValidationError("Google login is not configured")
        try:
            claims = id_token.verify_oauth2_token(
                google_id_token,
                google_requests.Request(),
                audience=client_ids if len(client_ids) > 1 else client_ids[0],
            )
        except ValueError as error:
            raise OAuthValidationError("Invalid Google ID token") from error

        subject = claims.get("sub")
        if not subject:
            raise OAuthValidationError("Google token does not include a subject")
        return OAuthProfile(OAuthProvider.GOOGLE, subject, claims.get("email"), claims.get("name"))

    async def _verify_kakao(self, access_token: str) -> OAuthProfile:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://kapi.kakao.com/v2/user/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise OAuthValidationError("Invalid Kakao access token") from error

        subject = payload.get("id")
        if subject is None:
            raise OAuthValidationError("Kakao token does not include a subject")
        kakao_account = payload.get("kakao_account") or {}
        nickname = (kakao_account.get("profile") or {}).get("nickname")
        return OAuthProfile(OAuthProvider.KAKAO, str(subject), kakao_account.get("email"), nickname)