FROM python:3.9-slim

# Instalar ffmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar los archivos de la aplicación
COPY . .

# Instalar las dependencias
RUN pip install -r requirements.txt

# Comando para ejecutar la aplicación
CMD ["python", "app.py"]
