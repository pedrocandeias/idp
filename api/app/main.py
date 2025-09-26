from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .middleware import audit_middleware
from .routers import (
    artifacts,
    admin,
    auth,
    datasets_abilities,
    datasets_anthro,
    demo,
    evaluations,
    health,
    organizations,
    conversion,
    scenarios,
    users,
    projects,
    rulepacks,
    files,
)
from .persistence import load_all_from_json

app = FastAPI(title="IDP API")

# CORS for web app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(audit_middleware)


@app.on_event("startup")
def _load_json_seed() -> None:
    try:
        load_all_from_json()
    except Exception:
        # do not block startup on file load
        pass

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(projects.router)
app.include_router(demo.router)
app.include_router(scenarios.router)
app.include_router(artifacts.router)
app.include_router(artifacts.router_common)
app.include_router(datasets_anthro.router)
app.include_router(datasets_abilities.router)
app.include_router(rulepacks.router)
app.include_router(evaluations.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(conversion.router)
app.include_router(files.router)
