FROM python:3.10-slim

WORKDIR /app

COPY bot/requirements.txt .
RUN pip install -r requirements.txt

COPY shared ./shared
COPY backend ./backend
COPY bot/ .

CMD ["python", "main.py"]
