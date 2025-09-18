from fastapi import FastAPI
from .routers import health, auth, organizations, projects, artifacts, datasets_anthro, datasets_abilities


app = FastAPI(title="IDP API")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(projects.router)
app.include_router(artifacts.router)
app.include_router(datasets_anthro.router)
app.include_router(datasets_abilities.router)
