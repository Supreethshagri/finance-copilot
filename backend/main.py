from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from services.deps import get_current_user
from models.user import User
from database.init_db import init_db
from api import auth, upload, chat



app = FastAPI(title="AI Finance Copilot")

# CORS: which frontend origins may call this API. Locked to localhost dev ports
# for now — NOT "*", which would let any website call your API.
# ...
app.include_router(upload.router)
app.include_router(chat.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://finance-copilot-dnzx.onrender.com",  # frontend URL
    ],
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


@app.get("/me")
def read_me(current_user: User = Depends(get_current_user)):
    """Protected route — proves the token guard works."""
    return {"id": current_user.id, "email": current_user.email}


app.include_router(auth.router)
