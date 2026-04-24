FROM python:3.12-slim

WORKDIR /app

# Zainstaluj zależności
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj kod serwera
COPY server/ .

# Skopiuj pliki HTML z korzenia projektu
COPY regulamin.html polityka-prywatnosci.html ./

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
