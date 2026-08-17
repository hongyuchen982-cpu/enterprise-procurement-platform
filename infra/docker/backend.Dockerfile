FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace

COPY requirements/lock.txt /workspace/requirements/lock.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install -r /workspace/requirements/lock.txt

COPY backend /workspace/backend
WORKDIR /workspace/backend

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
