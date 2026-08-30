FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -e .

ENV FAKE_MODEL=true \
    DATABASE_URL=sqlite:////data/harness.db

VOLUME ["/data"]
EXPOSE 8000

CMD ["uvicorn", "harness.api.app:get_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
