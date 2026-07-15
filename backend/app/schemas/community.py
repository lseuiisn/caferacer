from datetime import datetime

from pydantic import BaseModel, Field


class PostCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    image_urls: list[str] = Field(default=[], max_length=10)


class PostResponse(BaseModel):
    id: int
    author_id: int
    author_nickname: str | None
    content: str
    image_urls: list[str]
    like_count: int
    comment_count: int
    liked_by_me: bool
    created_at: datetime


class PostPage(BaseModel):
    items: list[PostResponse]
    page: int
    size: int
    total: int


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    parent_comment_id: int | None = Field(default=None, gt=0)


class CommentResponse(BaseModel):
    id: int
    post_id: int
    author_id: int
    author_nickname: str | None
    parent_comment_id: int | None
    content: str
    created_at: datetime


class ReportCreate(BaseModel):
    target_type: str = Field(pattern="^(post|comment|user|crew|message)$")
    target_id: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=50)
    details: str | None = Field(default=None, max_length=500)


class BlockCreate(BaseModel):
    user_id: int = Field(gt=0)
