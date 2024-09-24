# Usa un'immagine base di Python
FROM python:3.9-slim

# Installa dipendenze necessarie
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    chromium-driver \
    chromium

# Crea la directory di lavoro
WORKDIR /app

# Copia i file requirements
COPY requirements.txt /app/requirements.txt

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il resto del codice nell'immagine
COPY . /app

# Definisci il comando di esecuzione
CMD ["python", "scraper.py"]