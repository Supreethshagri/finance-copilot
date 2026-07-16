from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.init_db import init_db
from api import auth

app = FastAPI(title="AI Finance Copilot")

# CORS: which frontend origins may call this API. Locked to localhost dev ports
# for now — NOT "*", which would let any website call your API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()  # ensure tables exist when the server boots


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)