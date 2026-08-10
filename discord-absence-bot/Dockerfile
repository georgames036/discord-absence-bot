FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Koyebが自動的にPORT環境変数を注入する。ローカル実行用にデフォルト値も設定。
ENV PORT=8000
EXPOSE 8000

CMD ["python", "main.py"]
