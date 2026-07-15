from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import delete, func, select

from app.api.deps import CurrentUser, DbSession
from app.models.enums import ContentStatus
from app.models.social import (
    Comment,
    Post,
    PostImage,
    PostLike,
    Report,
    UserBlock,
)
from app.models.user import User
from app.schemas.community import (
    BlockCreate,
    CommentCreate,
    CommentResponse,
    PostCreate,
    PostPage,
    PostResponse,
    ReportCreate,
)

router = APIRouter(tags=["community"])


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def post_responses(
    db: DbSession,
    posts: list[Post],
    current_user_id: int,
) -> list[PostResponse]:
    if not posts:
        return []
    ids = [post.id for post in posts]
    users = {
        user.id: user for user in db.scalars(select(User).where(User.id.in_([p.author_id for p in posts])))
    }
    images: dict[int, list[str]] = {post_id: [] for post_id in ids}
    for image in db.scalars(
        select(PostImage)
        .where(PostImage.post_id.in_(ids))
        .order_by(PostImage.post_id, PostImage.display_order)
    ):
        images[image.post_id].append(image.image_url)
    like_counts = dict(
        db.execute(
            select(PostLike.post_id, func.count())
            .where(PostLike.post_id.in_(ids))
            .group_by(PostLike.post_id)
        ).all()
    )
    comment_counts = dict(
        db.execute(
            select(Comment.post_id, func.count())
            .where(Comment.post_id.in_(ids), Comment.status == ContentStatus.ACTIVE)
            .group_by(Comment.post_id)
        ).all()
    )
    liked = set(
        db.scalars(
            select(PostLike.post_id).where(
                PostLike.post_id.in_(ids), PostLike.user_id == current_user_id
            )
        )
    )
    return [
        PostResponse(
            id=post.id,
            author_id=post.author_id,
            author_nickname=users[post.author_id].nickname,
            content=post.content,
            image_urls=images[post.id],
            like_count=like_counts.get(post.id, 0),
            comment_count=comment_counts.get(post.id, 0),
            liked_by_me=post.id in liked,
            created_at=post.created_at,
        )
        for post in posts
    ]


@router.get("/posts", response_model=PostPage)
def list_posts(
    current_user: CurrentUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> PostPage:
    blocked_ids = select(UserBlock.blocked_id).where(UserBlock.blocker_id == current_user.id)
    filters = [Post.status == ContentStatus.ACTIVE, Post.author_id.not_in(blocked_ids)]
    total = db.scalar(select(func.count()).select_from(Post).where(*filters)) or 0
    posts = list(
        db.scalars(
            select(Post)
            .where(*filters)
            .order_by(Post.created_at.desc(), Post.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    )
    return PostPage(
        items=post_responses(db, posts, current_user.id),
        page=page,
        size=size,
        total=total,
    )


@router.get("/me/posts", response_model=PostPage)
def list_my_posts(
    current_user: CurrentUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> PostPage:
    filters = [Post.author_id == current_user.id, Post.status == ContentStatus.ACTIVE]
    total = db.scalar(select(func.count()).select_from(Post).where(*filters)) or 0
    posts = list(db.scalars(
        select(Post)
        .where(*filters)
        .order_by(Post.created_at.desc(), Post.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ))
    return PostPage(
        items=post_responses(db, posts, current_user.id),
        page=page,
        size=size,
        total=total,
    )


@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(payload: PostCreate, current_user: CurrentUser, db: DbSession) -> PostResponse:
    post = Post(author_id=current_user.id, content=payload.content)
    db.add(post)
    db.flush()
    db.add_all(
        [
            PostImage(post_id=post.id, image_url=url, display_order=index)
            for index, url in enumerate(payload.image_urls)
        ]
    )
    db.commit()
    db.refresh(post)
    return post_responses(db, [post], current_user.id)[0]


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, current_user: CurrentUser, db: DbSession) -> None:
    post = db.get(Post, post_id)
    if post is None or post.author_id != current_user.id:
        raise HTTPException(status_code=404, detail="Post not found")
    post.status = ContentStatus.DELETED
    db.commit()


@router.put("/posts/{post_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def like_post(post_id: int, current_user: CurrentUser, db: DbSession) -> None:
    if db.get(Post, post_id) is None:
        raise HTTPException(status_code=404, detail="Post not found")
    key = {"post_id": post_id, "user_id": current_user.id}
    if db.get(PostLike, key) is None:
        db.add(PostLike(**key, created_at=utcnow()))
        db.commit()


@router.delete("/posts/{post_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def unlike_post(post_id: int, current_user: CurrentUser, db: DbSession) -> None:
    like = db.get(PostLike, {"post_id": post_id, "user_id": current_user.id})
    if like:
        db.delete(like)
        db.commit()


@router.get("/posts/{post_id}/comments", response_model=list[CommentResponse])
def list_comments(post_id: int, current_user: CurrentUser, db: DbSession) -> list[CommentResponse]:
    comments = list(
        db.scalars(
            select(Comment)
            .where(Comment.post_id == post_id, Comment.status == ContentStatus.ACTIVE)
            .order_by(Comment.created_at, Comment.id)
        )
    )
    users = {
        user.id: user for user in db.scalars(select(User).where(User.id.in_([c.author_id for c in comments])))
    }
    return [
        CommentResponse(
            id=comment.id,
            post_id=comment.post_id,
            author_id=comment.author_id,
            author_nickname=users[comment.author_id].nickname,
            parent_comment_id=comment.parent_comment_id,
            content=comment.content,
            created_at=comment.created_at,
        )
        for comment in comments
    ]


@router.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=201)
def create_comment(
    post_id: int,
    payload: CommentCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> CommentResponse:
    if db.get(Post, post_id) is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if payload.parent_comment_id:
        parent = db.get(Comment, payload.parent_comment_id)
        if parent is None or parent.post_id != post_id:
            raise HTTPException(status_code=422, detail="Parent comment is invalid")
    comment = Comment(post_id=post_id, author_id=current_user.id, **payload.model_dump())
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return CommentResponse(
        id=comment.id,
        post_id=post_id,
        author_id=current_user.id,
        author_nickname=current_user.nickname,
        parent_comment_id=comment.parent_comment_id,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: int, current_user: CurrentUser, db: DbSession) -> None:
    comment = db.get(Comment, comment_id)
    if comment is None or comment.author_id != current_user.id:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.status = ContentStatus.DELETED
    db.commit()


@router.post("/reports", status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreate, current_user: CurrentUser, db: DbSession) -> dict[str, int]:
    report = Report(reporter_id=current_user.id, **payload.model_dump())
    db.add(report)
    db.commit()
    return {"id": report.id}


@router.put("/me/blocks", status_code=status.HTTP_204_NO_CONTENT)
def block_user(payload: BlockCreate, current_user: CurrentUser, db: DbSession) -> None:
    if payload.user_id == current_user.id:
        raise HTTPException(status_code=422, detail="You cannot block yourself")
    key = {"blocker_id": current_user.id, "blocked_id": payload.user_id}
    if db.get(UserBlock, key) is None:
        db.add(UserBlock(**key, created_at=utcnow()))
        db.commit()


@router.delete("/me/blocks/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def unblock_user(user_id: int, current_user: CurrentUser, db: DbSession) -> None:
    block = db.get(UserBlock, {"blocker_id": current_user.id, "blocked_id": user_id})
    if block:
        db.delete(block)
        db.commit()
