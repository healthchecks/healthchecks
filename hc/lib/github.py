import time

import jwt
from django.conf import settings
from pydantic import BaseModel

from hc.lib import curl


class OAuthResponse(BaseModel):
    access_token: str


def get_user_access_token(code: str) -> str:
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
    installations: list[Installation]


def get_installation_ids(user_access_token: str) -> list[int]:
    url = "https://api.github.com/user/installations"
    headers = {"Authorization": f"Bearer {user_access_token}"}
    result = curl.get(url, headers=headers)
    doc = InstallationsResponse.model_validate_json(result.content, strict=True)
    return [item.id for item in doc.installations]


class Repository(BaseModel):
    full_name: str


class RepositoriesResponse(BaseModel):
    repositories: list[Repository]


def get_repos(user_access_token: str) -> dict[str, int]:
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


def get_installation_access_token(installation_id: int) -> str:
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
    doc = AccessTokensResponse.model_validate_json(result.content, strict=True)
    return doc.token
