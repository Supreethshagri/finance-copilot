from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    email: EmailStr          # validates it's actually an email format
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"