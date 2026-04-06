FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY k8s-mcp-server.py .

RUN chmod +x k8s-mcp-server.py

CMD ["python", "k8s-mcp-server.py"]
