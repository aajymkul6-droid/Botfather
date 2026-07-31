FROM python:3.10-slim

# Отключаем интерактивные диалоги при установке
ENV DEBIAN_FRONTEND=noninteractive

# Устанавливаем wkhtmltopdf, графические библиотеки и шрифты
RUN apt-get update && apt-get install -y --no-install-recommends \
    wkhtmltopdf \
    xfonts-75dpi \
    xfonts-base \
    fontconfig \
    libxrender1 \
    libxext6 \
    libfontconfig1 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта
COPY . .

EXPOSE 5000

# Запускаем app.py
CMD ["python", "app.py"]
