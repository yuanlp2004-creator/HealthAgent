FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    fastapi==0.115.0 "uvicorn[standard]==0.30.6" \
    sqlalchemy==2.0.35 alembic==1.13.3 \
    pydantic==2.9.2 pydantic-settings==2.5.2 \
    "passlib[bcrypt]==1.7.4" bcrypt==4.0.1 \
    "python-jose[cryptography]==3.3.0" python-multipart==0.0.12 \
    email-validator==2.2.0 loguru==0.7.2 \
    "psycopg[binary]==3.2.3"

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
