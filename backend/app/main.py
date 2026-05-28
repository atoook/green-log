from fastapi import FastAPI

app = FastAPI(title="Green Log API")

@app.get("/")
def root():
    return {"message": "Hello Green Log"}