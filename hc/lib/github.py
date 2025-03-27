import logging
import time

import jwt
from django.conf import settings
from pydantic import BaseModel

from hc.lib import curl

logger = logging.getLogger(__name__)


class BadCredentials(Exception):
    pass


class OAuthResponse(BaseModel):
    access_token: str


def get_user_access_token(code: str) -> str:
    """Exchange OAuth code for user access token."""

    # Reference:
    # https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app

    url = "https://github.com/login/oauth/access_token"
    data = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
        "code": code,
    }
    headers = {"Accept": "application/vnd.github+json"}
    result = curl.post(url, data, headers=headers)
    doc = OAuthResponse.model_validate_json(result.content, strict=True)
    return doc.access_token


class Installation(BaseModel):
    id: int


class InstallationsResponse(BaseModel):
    # Error responses contain a "message" field
    message: str | None = None
    installations: list[Installation] | None = None


def get_installation_ids(user_access_token: str) -> list[int]:
    """Retrieve the installation ids the user has access to."""

    # Reference:
    # https://docs.github.com/en/rest/apps/installations?apiVersion=2022-11-28#list-app-installations-accessible-to-the-user-access-token

    url = "https://api.github.com/user/installations"
    headers = {"Authorization": f"Bearer {user_access_token}"}
    result = curl.get(url, headers=headers)
    doc = InstallationsResponse.model_validate_json(result.content, strict=True)
    if doc.message == "Bad credentials":
        # GitHub returns "Bad Credential" response when:
        # - We have acquired a valid user access token,
        # - The user then revokes the access token
        #   (removes us from Settings / Applications / Authorized GitHub Apps)
        # - We then try to use the token to load user's installations
        raise BadCredentials()

    if doc.installations is None:
        logger.warning(b"Unexpected response from GitHub: {result.content}")

    assert doc.installations is not None
    return [item.id for item in doc.installations]


class Repository(BaseModel):
    full_name: str


class RepositoriesResponse(BaseModel):
    repositories: list[Repository]


def get_repos(user_access_token: str) -> dict[str, int]:
    """Retrieve the repositories the user has access to.

    Return a dict with repo names as keys and the corresponding installation ids
    as values:

        {"owner/repo_name": inst_id, ...}

    """

    # Reference:
    # https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#list-repositories-for-a-user

    results = {}
    for inst_id in get_installation_ids(user_access_token):
        url = f"https://api.github.com/user/installations/{inst_id}/repositories"
        headers = {"Authorization": f"Bearer {user_access_token}"}
        result = curl.get(url, headers=headers)
        doc = RepositoriesResponse.model_validate_json(result.content, strict=True)
        for repo in doc.repositories:
            results[repo.full_name] = inst_id

    return results


class AccessTokensResponse(BaseModel):
    token: str


def get_installation_access_token(installation_id: int) -> str | None:
    """Acquire the installation access token for a specific installation id."""

    # Reference:
    # https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app

    iat = int(time.time())
    payload = {
        "iat": int(time.time()),
        "exp": iat + 600,
        "iss": settings.GITHUB_CLIENT_ID,
    }

    assert settings.GITHUB_PRIVATE_KEY
    encoded = jwt.encode(payload, settings.GITHUB_PRIVATE_KEY, algorithm="RS256")
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    result = curl.post(url, headers={"Authorization": f"Bearer {encoded}"})
    if result.status_code == 404:
        # The installation does not exist (our GitHub app has been uninstalled)
        return None

    doc = AccessTokensResponse.model_validate_json(result.content, strict=True)
    return doc.token
