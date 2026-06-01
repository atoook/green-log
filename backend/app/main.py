from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.routers.care import router as care_router
from app.routers.plants import router as plants_router
from app.routers.watering import router as watering_router
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
app.include_router(care_router)
app.include_router(watering_router)
app.include_router(webhooks_router)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    _request: Request,
    _exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "入力内容を確認してください"},
    )


@app.get("/")
def root():
    return {"message": "Hello Green Mate"}
