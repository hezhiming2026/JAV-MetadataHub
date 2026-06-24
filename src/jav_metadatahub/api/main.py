from __future__ import annotations

from fastapi import FastAPI

from jav_metadatahub.api.routes import (
    companies,
    health,
    observations,
    people,
    series,
    source_records,
    tags,
    works,
)


def create_app() -> FastAPI:
    app = FastAPI(title="JAV MetadataHub")
    app.include_router(health.router)
    app.include_router(works.router)
    app.include_router(people.router)
    app.include_router(companies.router)
    app.include_router(series.router)
    app.include_router(tags.router)
    app.include_router(observations.router)
    app.include_router(source_records.router)
    return app


app = create_app()
