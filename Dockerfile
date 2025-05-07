FROM python:3.11-slim

# Устанавливаем зависимости
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Экспонируем порт
EXPOSE 8000

# Старт приложения
CMD ["uvicorn", "run_api:app", "--host", "0.0.0.0", "--port", "8000"]
