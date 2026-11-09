FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e . -r bot/requirements.txt
CMD ["python", "bot/ultron.py"]
