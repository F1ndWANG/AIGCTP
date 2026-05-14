from app.core.config import settings
from app.services.bootstrap import should_seed_demo_catalog


def test_demo_catalog_seed_defaults_to_dev_only(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_CATALOG_AUTO_SEED", None)
    monkeypatch.setattr(settings, "APP_ENV", "development")
    assert should_seed_demo_catalog() is True

    monkeypatch.setattr(settings, "APP_ENV", "production")
    assert should_seed_demo_catalog() is False


def test_demo_catalog_seed_explicit_override(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "DEMO_CATALOG_AUTO_SEED", True)
    assert should_seed_demo_catalog() is True

    monkeypatch.setattr(settings, "DEMO_CATALOG_AUTO_SEED", False)
    assert should_seed_demo_catalog() is False
