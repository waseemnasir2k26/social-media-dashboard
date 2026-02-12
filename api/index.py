from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api")
def root():
    return {"status": "ok"}

@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "supabase_url": bool(os.environ.get("SUPABASE_URL")),
        "supabase_key": bool(os.environ.get("SUPABASE_KEY")),
    }

@app.get("/api/test")
def test():
    return {"message": "API is working!"}

handler = Mangum(app, lifespan="off")
