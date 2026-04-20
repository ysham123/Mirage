FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY mirage/ mirage/
COPY demo_ui/ demo_ui/
COPY examples/ examples/
COPY mocks.yaml .
COPY policies.yaml .
COPY tests/ tests/
RUN mkdir -p artifacts/traces

EXPOSE 8000

CMD ["uvicorn", "mirage.proxy:app", "--host", "0.0.0.0", "--port", "8000"]
