FROM python:3.10-slim

# Установка системных зависимостей и wkhtmltopdf + кириллических шрифтов
RUN apt-get update && apt-get install -y \
    wkhtmltopdf \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Открываем порт для Render
EXPOSE 5000

# Запуск бота
CMD ["python", "app.py"]
