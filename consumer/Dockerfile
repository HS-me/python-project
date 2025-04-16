FROM python:3.9-slim

WORKDIR /app

# 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 로그 디렉토리 생성
RUN mkdir -p /app/logs && touch /app/logs/consumer.log

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY consumer.py .

# Consumer 실행
CMD ["python", "consumer.py"] 