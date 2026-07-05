from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api import router as api_router
from database import init_db
from web import router as web_router


app = FastAPI(title="ScoreRent")

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

app.include_router(web_router)
app.include_router(api_router)


@app.on_event("startup")
def initialize_application():
    init_db()
