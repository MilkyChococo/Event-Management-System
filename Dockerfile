FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY .env.example ./.env.example

ENV APP_ENV=production
ENV APP_MONGO_URI=mongodb://mongo:27017
ENV APP_MONGO_DB_NAME=event_registration
ENV APP_SEED_DEMO=true

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
