FROM node:22-bookworm-slim AS css-builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY tailwind.config.js ./
COPY static ./static
RUN npm run build:css

FROM python:3.12-slim AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=css-builder /app/static/css/app.css ./static/css/app.css
RUN python manage.py collectstatic --no-input

EXPOSE 8000

CMD ["sh", "-c", "gunicorn jobhunt.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
