from types import SimpleNamespace

from app.api.routers.community import list_my_posts, list_posts


class EmptyCommunitySession:
    def scalar(self, _statement):
        return 0

    def scalars(self, _statement):
        return []


def test_empty_community_feed_returns_page() -> None:
    result = list_posts(SimpleNamespace(id=1), EmptyCommunitySession(), 1, 20)

    assert result.items == []
    assert result.page == 1
    assert result.size == 20
    assert result.total == 0


def test_empty_my_posts_returns_page() -> None:
    result = list_my_posts(SimpleNamespace(id=1), EmptyCommunitySession(), 1, 20)

    assert result.items == []
    assert result.total == 0
