from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from database import init_db

from api import router as api_router

from routes.auth_routes import (
    router as auth_router,
)

from routes.dashboard_routes import (
    router as dashboard_router,
)

from routes.history_routes import (
    router as history_router,
)

from routes.profile_routes import (
    router as profile_router,
)

from routes.evaluation_routes import (
    router as evaluation_router,
)


# ---------------------------------------------------------
# Application
# ---------------------------------------------------------

app = FastAPI(
    title="ScoreRent"
)


# ---------------------------------------------------------
# Static assets
# ---------------------------------------------------------

app.mount(
    "/static",

    StaticFiles(
        directory="static"
    ),

    name="static",
)


# ---------------------------------------------------------
# Startup
# ---------------------------------------------------------

@app.on_event(
    "startup"
)
def startup():
    """
    Initialise database
    tables and setup.
    """

    init_db()


# ---------------------------------------------------------
# API routes
# ---------------------------------------------------------

app.include_router(
    api_router
)


# ---------------------------------------------------------
# Authentication
# ---------------------------------------------------------

app.include_router(
    auth_router
)


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------

app.include_router(
    dashboard_router
)


# ---------------------------------------------------------
# Evaluation history
# ---------------------------------------------------------

app.include_router(
    history_router
)


# ---------------------------------------------------------
# Profile management
# ---------------------------------------------------------

app.include_router(
    profile_router
)


# ---------------------------------------------------------
# Evaluation + results
# ---------------------------------------------------------

app.include_router(
    evaluation_router
)
