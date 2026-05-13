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
