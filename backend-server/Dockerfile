FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# revision
COPY alembic alembic/
COPY alembic.ini alembic.ini

COPY app app/
COPY pyproject.toml pytest.ini ./

# Set Python path to include the current directory
ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--reload", "--reload-dir", "app"]

