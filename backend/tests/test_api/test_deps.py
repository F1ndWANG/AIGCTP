from typing import Annotated, get_args, get_origin

from app.api import deps


def _metadata(alias):
    assert get_origin(alias) is Annotated
    return get_args(alias)[1:]


def test_dependency_aliases_are_annotated_fastapi_dependencies():
    db_meta = _metadata(deps.DbSession)
    user_meta = _metadata(deps.CurrentUser)
    bearer_meta = _metadata(deps.BearerCredentials)

    assert db_meta[0].dependency is deps.get_db
    assert user_meta[0].dependency is deps.get_current_user
    assert bearer_meta[0].dependency is deps.bearer_scheme
