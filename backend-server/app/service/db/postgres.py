import os
from sqlmodel import SQLModel, Field, create_engine
from app.models.user import * # Import the User & access token models
from app.models.job import * # Import the Job model
from app.models.submission import * # Import the Submission model
from app.models.leaderboard import * # Import the LeaderBoard model

# Use environment variable for database URL, fallback to default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/mydatabase")
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    # create the table if not exists
    SQLModel.metadata.create_all(engine)
    print("Database and tables created successfully.")

