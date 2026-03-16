# app/models/request_models.py

from pydantic import BaseModel, HttpUrl, field_validator
from typing import Annotated
# Annotated lets you attach metadata to a type
# e.g. Annotated[str, "max 500 chars"] — useful with Pydantic


class AnalyzeRequest(BaseModel):
    url:             HttpUrl   # Pydantic validates this is a real URL
    include_reviews: bool = True
    include_news:    bool = True
    include_seo:     bool = True

    @field_validator("url")
    @classmethod
    def url_must_be_public(cls, v: HttpUrl) -> HttpUrl:
        # v is typed as HttpUrl — IDE knows its methods
        url_str: str = str(v)
        blocked: list[str] = ["localhost", "127.0.0.1", "0.0.0.0"]
        if any(b in url_str for b in blocked):
            raise ValueError("URL must be a public website")
        return v

    def get_url_string(self) -> str:
        """Convenience method — returns URL as plain string"""
        return str(self.url)