from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

import jav_metadatahub.db.models  # noqa: F401
from jav_metadatahub.db.base import Base

EXPECTED_TABLES = {
    "javhub.collector_runs",
    "javhub.source_records",
    "javhub.works",
    "javhub.work_external_ids",
    "javhub.people",
    "javhub.person_aliases",
    "javhub.person_external_ids",
    "javhub.work_people",
    "javhub.companies",
    "javhub.company_external_ids",
    "javhub.work_companies",
    "javhub.series",
    "javhub.series_external_ids",
    "javhub.work_series",
    "javhub.tags",
    "javhub.work_tags",
    "javhub.field_observations",
    "javhub.entity_match_candidates",
    "javhub.entity_merge_logs",
    "javhub.media_assets",
}


def test_metadata_uses_javhub_schema() -> None:
    assert Base.metadata.schema == "javhub"


def test_all_task_02_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_works_code_norm_is_not_globally_unique() -> None:
    table = Base.metadata.tables["javhub.works"]

    unique_column_sets = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert ("code_norm",) not in unique_column_sets


def test_field_observations_entity_id_has_no_foreign_key() -> None:
    table = Base.metadata.tables["javhub.field_observations"]

    assert not table.c.entity_id.foreign_keys
    assert not any(
        "entity_id" in constraint.columns
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    )


def test_unique_constraint_source_columns_are_not_nullable() -> None:
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            if not isinstance(constraint, UniqueConstraint):
                continue
            if "source" not in constraint.columns:
                continue

            assert not table.c.source.nullable, table.fullname


def test_media_assets_remain_url_only_by_default() -> None:
    table = Base.metadata.tables["javhub.media_assets"]

    assert table.c.download_status.server_default is not None
    assert str(table.c.download_status.server_default.arg) == "'url_only'"
    assert "local_path" in table.c
