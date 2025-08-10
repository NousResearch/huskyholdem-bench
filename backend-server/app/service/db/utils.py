from sqlmodel import Session, select
from app.models.user import User, AccessToken
from app.service.db.postgres import engine
from passlib.hash import bcrypt

def delete_username(username: str):
    """Delete a user by username from the database."""
    with Session(engine) as db:
        user = db.exec(select(User).where(User.username == username)).first()
        if user:
            db.delete(user)
            db.commit()

def create_admin_user(username: str, password: str, email: str):
    """Create an admin user in the database."""
    with Session(engine) as db:
        hashed_password = bcrypt.hash(password)
        user = User(username=username, password=hashed_password, email=email, admin=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

def delete_token(token_id: str):
    """Delete a token by ID from the database"""
    with Session(engine) as db:
        token = db.exec(select(AccessToken).where(AccessToken.id == token_id)).first()
        if token:
            db.delete(token)
            db.commit()

def verify_user(username: str):
    """Finds a user by username and sets their `is_verified` flag to True."""
    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        user = session.exec(statement).first()
        if user:
            user.is_verified = True
            session.add(user)
            session.commit()
            session.refresh(user)