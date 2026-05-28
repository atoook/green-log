from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.plants import router as plants_router

app = FastAPI(title="Green Log API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plants_router)


@app.get("/")
def root():
    return {"message": "Hello Green Log"}
