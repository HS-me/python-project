#!/bin/bash

# 프로젝트 루트 디렉토리 생성
mkdir -p /home/yhs2/integrated-voting-system
cd /home/yhs2/integrated-voting-system

# 필요한 디렉토리 구조 생성
mkdir -p frontend api-server consumer logs

# VM2의 API 서버 코드 복사
echo "Copying API server code..."
cp -r /home/yhs2/voting-system/voting-system/* api-server/

# VM3의 Consumer 코드 가져오기
echo "Copying Consumer code..."
scp -r root@172.16.1.18:/home/yhs3/vote-consumer/consumer.py consumer/
scp -r root@172.16.1.18:/home/yhs3/vote-consumer/init_db.sql consumer/

# VM4의 Frontend 코드 가져오기 
echo "Copying Frontend code..."
scp -r root@172.16.1.19:/home/yhs3/voting-frontend/* frontend/

# 로그 파일 생성
touch logs/consumer.log
chmod 666 logs/consumer.log

# Docker-compose 실행
echo "Starting integrated environment..."
docker-compose up -d

echo "Done! Services should be running."
echo "- Frontend: http://172.16.1.17:3000"
echo "- API: http://172.16.1.17:8000"
echo "- Kafka UI: http://172.16.1.17:8080" 