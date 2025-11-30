FROM python:3.10-slim

WORKDIR /app

COPY webapp/requirements.txt .
RUN pip install -r requirements.txt

COPY shared ./shared
COPY backend ./backend
COPY update_schema.py .
COPY update_memory_settings.py .
COPY webapp/ .

EXPOSE 5000

CMD ["python", "app.py"]
