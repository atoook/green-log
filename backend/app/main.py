from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers.plants import router as plants_router
from app.routers.webhooks import router as webhooks_router

app = FastAPI(title="Green Mate API")
settings = get_settings()


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plants_router)
app.include_router(webhooks_router)


@app.get("/")
def root():
    return {"message": "Hello Green Mate"}
