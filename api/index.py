from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api")
async def root():
    return {"status": "running", "message": "Social Media Dashboard API"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

handler = Mangum(app, lifespan="off")
