from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .middleware import audit_middleware
from .routers import (
    artifacts,
    auth,
    datasets_abilities,
    datasets_anthro,
    evaluations,
    health,
    organizations,
    projects,
    rulepacks,
)

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

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(projects.router)
app.include_router(artifacts.router)
app.include_router(datasets_anthro.router)
app.include_router(datasets_abilities.router)
app.include_router(rulepacks.router)
app.include_router(evaluations.router)
