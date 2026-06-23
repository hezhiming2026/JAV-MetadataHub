"""create initial javhub schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS javhub")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute(
        """
        CREATE TABLE javhub.collector_runs (
            id BIGSERIAL PRIMARY KEY,
            source TEXT NOT NULL DEFAULT 'unknown',
            run_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'running',
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            finished_at TIMESTAMPTZ,
            request_count INTEGER NOT NULL DEFAULT 0,
            success_count INTEGER NOT NULL DEFAULT 0,
            failed_count INTEGER NOT NULL DEFAULT 0,
            config JSONB,
            error_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_collector_runs_source_started
        ON javhub.collector_runs (source, started_at DESC)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.source_records (
            id BIGSERIAL PRIMARY KEY,
            source TEXT NOT NULL DEFAULT 'unknown',
            source_key TEXT NOT NULL,
            source_url TEXT,
            record_type TEXT NOT NULL,
            payload_type TEXT NOT NULL DEFAULT 'json',
            raw_json JSONB,
            raw_html TEXT,
            raw_text TEXT,
            http_status INTEGER,
            fetch_status TEXT NOT NULL DEFAULT 'success',
            error_message TEXT,
            parser_version TEXT,
            checksum TEXT,
            collector_run_id BIGINT REFERENCES javhub.collector_runs(id),
            fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_source_records_source_key_record_type
                UNIQUE (source, source_key, record_type)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_source_records_source_key
        ON javhub.source_records (source, source_key)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_source_records_record_type
        ON javhub.source_records (record_type)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_source_records_fetched_at
        ON javhub.source_records (fetched_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_source_records_raw_json_gin
        ON javhub.source_records USING GIN (raw_json)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.works (
            id BIGSERIAL PRIMARY KEY,
            code_original TEXT,
            code_norm TEXT,
            code_prefix TEXT,
            code_number TEXT,
            title_ja TEXT,
            title_en TEXT,
            title_zh TEXT,
            release_date DATE,
            runtime_minutes INTEGER,
            censor_type TEXT NOT NULL DEFAULT 'unknown',
            work_type TEXT NOT NULL DEFAULT 'unknown',
            primary_source TEXT,
            confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
            is_active BOOLEAN NOT NULL DEFAULT true,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_works_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1)
        )
        """
    )
    op.execute("CREATE INDEX idx_works_code_norm ON javhub.works (code_norm)")
    op.execute(
        """
        CREATE INDEX idx_works_code_prefix_number
        ON javhub.works (code_prefix, code_number)
        """
    )
    op.execute("CREATE INDEX idx_works_release_date ON javhub.works (release_date DESC)")
    op.execute(
        """
        CREATE INDEX idx_works_title_ja_trgm
        ON javhub.works USING GIN (title_ja gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_works_title_en_trgm
        ON javhub.works USING GIN (title_en gin_trgm_ops)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.people (
            id BIGSERIAL PRIMARY KEY,
            canonical_name TEXT NOT NULL,
            name_ja TEXT,
            name_en TEXT,
            name_zh TEXT,
            name_kana TEXT,
            person_type TEXT NOT NULL DEFAULT 'unknown',
            gender_role TEXT NOT NULL DEFAULT 'unknown',
            primary_source TEXT,
            confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
            is_active BOOLEAN,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_people_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_people_canonical_name_trgm
        ON javhub.people USING GIN (canonical_name gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_people_name_ja_trgm
        ON javhub.people USING GIN (name_ja gin_trgm_ops)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.companies (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            name_norm TEXT,
            company_type TEXT NOT NULL DEFAULT 'unknown',
            primary_source TEXT,
            confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_companies_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1)
        )
        """
    )
    op.execute("CREATE INDEX idx_companies_name_norm ON javhub.companies (name_norm)")
    op.execute(
        """
        CREATE INDEX idx_companies_name_trgm
        ON javhub.companies USING GIN (name gin_trgm_ops)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.series (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            name_norm TEXT,
            primary_source TEXT,
            confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_series_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1)
        )
        """
    )
    op.execute("CREATE INDEX idx_series_name_norm ON javhub.series (name_norm)")
    op.execute(
        """
        CREATE INDEX idx_series_name_trgm
        ON javhub.series USING GIN (name gin_trgm_ops)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.tags (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            name_norm TEXT,
            tag_type TEXT NOT NULL DEFAULT 'unknown',
            language TEXT NOT NULL DEFAULT 'unknown',
            source TEXT NOT NULL DEFAULT 'unknown',
            confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_tags_name_norm_type_language_source
                UNIQUE (name_norm, tag_type, language, source),
            CONSTRAINT ck_tags_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1)
        )
        """
    )
    op.execute("CREATE INDEX idx_tags_name_norm ON javhub.tags (name_norm)")
    op.execute(
        """
        CREATE INDEX idx_tags_name_trgm
        ON javhub.tags USING GIN (name gin_trgm_ops)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.work_external_ids (
            id BIGSERIAL PRIMARY KEY,
            work_id BIGINT NOT NULL REFERENCES javhub.works(id) ON DELETE CASCADE,
            source TEXT NOT NULL DEFAULT 'unknown',
            external_id TEXT NOT NULL,
            external_url TEXT,
            id_type TEXT NOT NULL,
            confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
            source_record_id BIGINT REFERENCES javhub.source_records(id),
            fetched_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_work_external_ids_source_external_id_type
                UNIQUE (source, external_id, id_type),
            CONSTRAINT ck_work_external_ids_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_work_external_ids_work_id
        ON javhub.work_external_ids (work_id)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_work_external_ids_source_external
        ON javhub.work_external_ids (source, external_id)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.person_aliases (
            id BIGSERIAL PRIMARY KEY,
            person_id BIGINT NOT NULL REFERENCES javhub.people(id)
                ON DELETE CASCADE,
            alias TEXT NOT NULL,
            alias_norm TEXT,
            alias_type TEXT NOT NULL DEFAULT 'unknown',
            source TEXT NOT NULL DEFAULT 'unknown',
            confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
            source_record_id BIGINT REFERENCES javhub.source_records(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_person_aliases_person_alias_type_source
                UNIQUE (person_id, alias, alias_type, source),
            CONSTRAINT ck_person_aliases_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_person_aliases_alias_norm
        ON javhub.person_aliases (alias_norm)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_person_aliases_alias_trgm
        ON javhub.person_aliases USING GIN (alias gin_trgm_ops)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.person_external_ids (
            id BIGSERIAL PRIMARY KEY,
            person_id BIGINT NOT NULL REFERENCES javhub.people(id)
                ON DELETE CASCADE,
            source TEXT NOT NULL DEFAULT 'unknown',
            external_id TEXT NOT NULL,
            external_url TEXT,
            id_type TEXT NOT NULL DEFAULT 'database_id',
            confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
            source_record_id BIGINT REFERENCES javhub.source_records(id),
            fetched_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_person_external_ids_source_external_id_type
                UNIQUE (source, external_id, id_type),
            CONSTRAINT ck_person_external_ids_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_person_external_ids_person_id
        ON javhub.person_external_ids (person_id)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.work_people (
            id BIGSERIAL PRIMARY KEY,
            work_id BIGINT NOT NULL REFERENCES javhub.works(id) ON DELETE CASCADE,
            person_id BIGINT NOT NULL REFERENCES javhub.people(id)
                ON DELETE CASCADE,
            role TEXT NOT NULL,
            billing_order INTEGER,
            source TEXT NOT NULL DEFAULT 'unknown',
            confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
            source_record_id BIGINT REFERENCES javhub.source_records(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_work_people_work_person_role_source
                UNIQUE (work_id, person_id, role, source),
            CONSTRAINT ck_work_people_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1)
        )
        """
    )
    op.execute("CREATE INDEX idx_work_people_work_role ON javhub.work_people (work_id, role)")
    op.execute(
        """
        CREATE INDEX idx_work_people_person_role
        ON javhub.work_people (person_id, role)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.company_external_ids (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NOT NULL REFERENCES javhub.companies(id)
                ON DELETE CASCADE,
            source TEXT NOT NULL DEFAULT 'unknown',
            external_id TEXT NOT NULL,
            external_url TEXT,
            id_type TEXT NOT NULL DEFAULT 'database_id',
            confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
            source_record_id BIGINT REFERENCES javhub.source_records(id),
            fetched_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_company_external_ids_source_external_id_type
                UNIQUE (source, external_id, id_type),
            CONSTRAINT ck_company_external_ids_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_company_external_ids_company_id
        ON javhub.company_external_ids (company_id)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.work_companies (
            id BIGSERIAL PRIMARY KEY,
            work_id BIGINT NOT NULL REFERENCES javhub.works(id) ON DELETE CASCADE,
            company_id BIGINT NOT NULL REFERENCES javhub.companies(id)
                ON DELETE CASCADE,
            role TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'unknown',
            confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
            source_record_id BIGINT REFERENCES javhub.source_records(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_work_companies_work_company_role_source
                UNIQUE (work_id, company_id, role, source),
            CONSTRAINT ck_work_companies_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_work_companies_work_role
        ON javhub.work_companies (work_id, role)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_work_companies_company_role
        ON javhub.work_companies (company_id, role)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.series_external_ids (
            id BIGSERIAL PRIMARY KEY,
            series_id BIGINT NOT NULL REFERENCES javhub.series(id)
                ON DELETE CASCADE,
            source TEXT NOT NULL DEFAULT 'unknown',
            external_id TEXT NOT NULL,
            external_url TEXT,
            id_type TEXT NOT NULL DEFAULT 'database_id',
            confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
            source_record_id BIGINT REFERENCES javhub.source_records(id),
            fetched_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_series_external_ids_source_external_id_type
                UNIQUE (source, external_id, id_type),
            CONSTRAINT ck_series_external_ids_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_series_external_ids_series_id
        ON javhub.series_external_ids (series_id)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.work_series (
            id BIGSERIAL PRIMARY KEY,
            work_id BIGINT NOT NULL REFERENCES javhub.works(id) ON DELETE CASCADE,
            series_id BIGINT NOT NULL REFERENCES javhub.series(id)
                ON DELETE CASCADE,
            source TEXT NOT NULL DEFAULT 'unknown',
            confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
            source_record_id BIGINT REFERENCES javhub.source_records(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_work_series_work_series_source
                UNIQUE (work_id, series_id, source),
            CONSTRAINT ck_work_series_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1)
        )
        """
    )
    op.execute("CREATE INDEX idx_work_series_work_id ON javhub.work_series (work_id)")
    op.execute("CREATE INDEX idx_work_series_series_id ON javhub.work_series (series_id)")

    op.execute(
        """
        CREATE TABLE javhub.work_tags (
            id BIGSERIAL PRIMARY KEY,
            work_id BIGINT NOT NULL REFERENCES javhub.works(id) ON DELETE CASCADE,
            tag_id BIGINT NOT NULL REFERENCES javhub.tags(id) ON DELETE CASCADE,
            source TEXT NOT NULL DEFAULT 'unknown',
            confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
            source_record_id BIGINT REFERENCES javhub.source_records(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_work_tags_work_tag_source
                UNIQUE (work_id, tag_id, source),
            CONSTRAINT ck_work_tags_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1)
        )
        """
    )
    op.execute("CREATE INDEX idx_work_tags_work_id ON javhub.work_tags (work_id)")
    op.execute("CREATE INDEX idx_work_tags_tag_id ON javhub.work_tags (tag_id)")

    op.execute(
        """
        CREATE TABLE javhub.field_observations (
            id BIGSERIAL PRIMARY KEY,
            entity_type TEXT NOT NULL,
            entity_id BIGINT NOT NULL,
            field_name TEXT NOT NULL,
            field_value JSONB,
            field_value_text TEXT,
            source TEXT NOT NULL DEFAULT 'unknown',
            source_record_id BIGINT REFERENCES javhub.source_records(id),
            confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
            observation_status TEXT NOT NULL DEFAULT 'active',
            rejection_reason TEXT,
            observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_field_observations_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_field_observations_entity
        ON javhub.field_observations (entity_type, entity_id)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_field_observations_field
        ON javhub.field_observations (field_name)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_field_observations_source
        ON javhub.field_observations (source)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_field_observations_value_text_trgm
        ON javhub.field_observations USING GIN (field_value_text gin_trgm_ops)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.entity_match_candidates (
            id BIGSERIAL PRIMARY KEY,
            entity_type TEXT NOT NULL,
            left_entity_id BIGINT NOT NULL,
            right_entity_id BIGINT NOT NULL,
            match_score NUMERIC(5, 4) NOT NULL,
            match_reason JSONB,
            status TEXT NOT NULL DEFAULT 'pending',
            reviewed_by TEXT,
            reviewed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_entity_match_candidates_entity_left_right
                UNIQUE (entity_type, left_entity_id, right_entity_id),
            CONSTRAINT ck_entity_match_candidates_match_score_range
                CHECK (match_score >= 0 AND match_score <= 1)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_entity_match_candidates_entity_status
        ON javhub.entity_match_candidates (entity_type, status)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.entity_merge_logs (
            id BIGSERIAL PRIMARY KEY,
            entity_type TEXT NOT NULL,
            from_entity_id BIGINT NOT NULL,
            to_entity_id BIGINT NOT NULL,
            merge_reason TEXT,
            merge_confidence NUMERIC(4, 3),
            merged_by TEXT NOT NULL DEFAULT 'manual',
            merged_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_entity_merge_logs_merge_confidence_range
                CHECK (merge_confidence >= 0 AND merge_confidence <= 1)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_entity_merge_logs_entity
        ON javhub.entity_merge_logs (entity_type, from_entity_id, to_entity_id)
        """
    )

    op.execute(
        """
        CREATE TABLE javhub.media_assets (
            id BIGSERIAL PRIMARY KEY,
            work_id BIGINT REFERENCES javhub.works(id) ON DELETE CASCADE,
            person_id BIGINT REFERENCES javhub.people(id) ON DELETE CASCADE,
            asset_type TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'unknown',
            url TEXT NOT NULL,
            local_path TEXT,
            width INTEGER,
            height INTEGER,
            hash TEXT,
            download_status TEXT NOT NULL DEFAULT 'url_only',
            copyright_note TEXT,
            source_record_id BIGINT REFERENCES javhub.source_records(id),
            fetched_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_media_assets_source_url UNIQUE (source, url)
        )
        """
    )
    op.execute("CREATE INDEX idx_media_assets_work_id ON javhub.media_assets (work_id)")
    op.execute("CREATE INDEX idx_media_assets_person_id ON javhub.media_assets (person_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS javhub.media_assets")
    op.execute("DROP TABLE IF EXISTS javhub.entity_merge_logs")
    op.execute("DROP TABLE IF EXISTS javhub.entity_match_candidates")
    op.execute("DROP TABLE IF EXISTS javhub.field_observations")
    op.execute("DROP TABLE IF EXISTS javhub.work_tags")
    op.execute("DROP TABLE IF EXISTS javhub.work_series")
    op.execute("DROP TABLE IF EXISTS javhub.series_external_ids")
    op.execute("DROP TABLE IF EXISTS javhub.work_companies")
    op.execute("DROP TABLE IF EXISTS javhub.company_external_ids")
    op.execute("DROP TABLE IF EXISTS javhub.work_people")
    op.execute("DROP TABLE IF EXISTS javhub.person_external_ids")
    op.execute("DROP TABLE IF EXISTS javhub.person_aliases")
    op.execute("DROP TABLE IF EXISTS javhub.work_external_ids")
    op.execute("DROP TABLE IF EXISTS javhub.tags")
    op.execute("DROP TABLE IF EXISTS javhub.series")
    op.execute("DROP TABLE IF EXISTS javhub.companies")
    op.execute("DROP TABLE IF EXISTS javhub.people")
    op.execute("DROP TABLE IF EXISTS javhub.works")
    op.execute("DROP TABLE IF EXISTS javhub.source_records")
    op.execute("DROP TABLE IF EXISTS javhub.collector_runs")
    op.execute("DROP SCHEMA IF EXISTS javhub")
