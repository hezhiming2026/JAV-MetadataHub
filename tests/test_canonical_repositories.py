from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from jav_metadatahub.db.models import Company, Person, Series, Tag, Work
from jav_metadatahub.repositories import (
    CompanyRepository,
    PersonRepository,
    SeriesRepository,
    TagRepository,
    WorkRepository,
)


@pytest.mark.parametrize(
    ("repository_class", "model_name"),
    [
        (WorkRepository, "works"),
        (PersonRepository, "people"),
        (CompanyRepository, "companies"),
        (SeriesRepository, "series"),
        (TagRepository, "tags"),
    ],
)
def test_canonical_repository_list_page_counts_and_uses_stable_order(
    repository_class: type[Any],
    model_name: str,
) -> None:
    session = Mock(spec=Session)
    session.scalar.return_value = 0
    session.scalars.return_value.all.return_value = []
    repository = repository_class(session)

    items, total = repository.list_page(limit=20, offset=10)

    assert items == []
    assert total == 0
    statement = session.scalars.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert f"FROM javhub.{model_name}" in sql
    assert f"ORDER BY javhub.{model_name}.created_at DESC, javhub.{model_name}.id DESC" in sql
    assert compiled.params == {"param_1": 20, "param_2": 10}


@pytest.mark.parametrize(
    ("repository_class", "model"),
    [
        (WorkRepository, Work),
        (PersonRepository, Person),
        (CompanyRepository, Company),
        (SeriesRepository, Series),
        (TagRepository, Tag),
    ],
)
def test_canonical_repository_get_by_id_uses_session_get(
    repository_class: type[Any],
    model: type[Work] | type[Person] | type[Company] | type[Series] | type[Tag],
) -> None:
    session = Mock(spec=Session)
    repository = repository_class(session)

    repository.get_by_id(123)

    session.get.assert_called_once_with(model, 123)
