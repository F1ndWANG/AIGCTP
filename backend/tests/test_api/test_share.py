"""Tests for travel note sharing and recommendation integration."""


class TestTravelNotes:
    async def test_create_and_list_public_note(self, client, auth_headers):
        create = await client.post("/api/v1/shares/notes", headers=auth_headers, json={
            "title": "北京一日游笔记",
            "content": "天坛、公园和南门涮肉路线很顺，适合第一次来北京的人。",
            "destination": "北京",
            "tags": ["北京", "美食", "citywalk"],
        })
        assert create.status_code == 201
        note = create.json()
        assert note["title"] == "北京一日游笔记"
        assert note["like_count"] == 0

        listed = await client.get("/api/v1/shares/notes?destination=北京", headers=auth_headers)
        assert listed.status_code == 200
        assert len(listed.json()) == 1
        assert listed.json()[0]["destination"] == "北京"

    async def test_note_interactions_and_comment(self, client, auth_headers):
        create = await client.post("/api/v1/shares/notes", headers=auth_headers, json={
            "title": "成都美食路线",
            "content": "宽窄巷子附近适合慢逛，晚上可以去玉林路。",
            "destination": "成都",
            "tags": ["成都", "美食"],
        })
        note_id = create.json()["id"]

        liked = await client.post(f"/api/v1/shares/notes/{note_id}/interactions", headers=auth_headers, json={
            "interaction_type": "like",
            "active": True,
        })
        assert liked.status_code == 200
        assert liked.json()["like_count"] == 1
        assert liked.json()["viewer_interactions"]["like"] is True

        commented = await client.post(f"/api/v1/shares/notes/{note_id}/comments", headers=auth_headers, json={
            "content": "这个路线适合亲子吗？",
        })
        assert commented.status_code == 201
        assert commented.json()["comment_count"] == 1
        assert commented.json()["comments"][0]["content"] == "这个路线适合亲子吗？"

    async def test_travel_feed_contains_public_notes(self, client, auth_headers):
        create = await client.post("/api/v1/shares/notes", headers=auth_headers, json={
            "title": "西安城墙骑行笔记",
            "content": "傍晚骑行体验最好，注意提前看天气和城墙开放时间。",
            "destination": "西安",
            "tags": ["西安", "骑行"],
        })
        assert create.status_code == 201

        feed = await client.get("/api/v1/recommend/feed?domain=travel&limit=10", headers=auth_headers)
        assert feed.status_code == 200
        items = feed.json()["items"]
        assert any(item["item_type"] == "travel_note" for item in items)

    async def test_recommended_notes_uses_recommendation_feed(self, client, auth_headers):
        create = await client.post("/api/v1/shares/notes", headers=auth_headers, json={
            "title": "杭州西湖轻松游",
            "content": "西湖、龙井和湖滨路线适合轻松慢走。",
            "destination": "杭州",
            "tags": ["杭州", "西湖", "轻松"],
        })
        assert create.status_code == 201

        recommended = await client.get("/api/v1/shares/notes/recommended?limit=5", headers=auth_headers)
        assert recommended.status_code == 200
        assert any(note["title"] == "杭州西湖轻松游" for note in recommended.json())

    async def test_note_create_syncs_recommendation_catalog_immediately(self, client, auth_headers, session):
        from sqlalchemy import select
        from app.models.recommendation import RecommendationItem

        create = await client.post("/api/v1/shares/notes", headers=auth_headers, json={
            "title": "苏州园林慢游",
            "content": "拙政园、平江路和评弹茶馆适合慢节奏路线。",
            "destination": "苏州",
            "tags": ["苏州", "园林", "慢游"],
        })
        assert create.status_code == 201
        note_id = str(create.json()["id"])

        result = await session.execute(
            select(RecommendationItem).where(
                RecommendationItem.domain == "travel",
                RecommendationItem.item_type == "travel_note",
                RecommendationItem.source_id == note_id,
            )
        )
        item = result.scalar_one_or_none()
        assert item is not None
        assert item.title == "苏州园林慢游"

        feed = await client.get("/api/v1/recommend/feed?domain=travel&limit=10", headers=auth_headers)
        assert any(candidate["item_id"] == note_id for candidate in feed.json()["items"])

    async def test_public_notes_from_other_users_are_recommendable(self, client, auth_headers, session):
        from app.core.security import hash_password
        from app.models.share import TravelNote
        from app.models.user import User
        from app.services.recommendation.catalog import sync_travel_note_item

        author = User(
            username="public-author",
            hashed_password=hash_password("testpass123"),
            display_name="Public Author",
        )
        session.add(author)
        await session.flush()
        note = TravelNote(
            author_id=author.id,
            title="青岛海边周末",
            content="栈桥、八大关和海边咖啡适合周末慢游。",
            destination="青岛",
            tags=["青岛", "海边", "周末"],
            visibility="public",
        )
        session.add(note)
        await session.flush()
        await sync_travel_note_item(session, note)
        await session.commit()

        feed = await client.get("/api/v1/recommend/feed?domain=travel&limit=20", headers=auth_headers)
        assert feed.status_code == 200
        assert any(item["item_type"] == "travel_note" and item["item_id"] == str(note.id) for item in feed.json()["items"])
