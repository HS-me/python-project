# VM2로 통합 환경 파일 전송 스크립트

# 대상 디렉토리 생성
ssh root@172.16.1.17 "mkdir -p /home/yhs2/integrated-voting-system"

# docker-compose.yml 전송
scp .\docker-compose.yml root@172.16.1.17:/home/yhs2/integrated-voting-system/

# api-server 디렉토리와 파일 전송
ssh root@172.16.1.17 "mkdir -p /home/yhs2/integrated-voting-system/api-server"
scp .\api-server\Dockerfile root@172.16.1.17:/home/yhs2/integrated-voting-system/api-server/
scp .\api-server\requirements.txt root@172.16.1.17:/home/yhs2/integrated-voting-system/api-server/

# consumer 디렉토리와 파일 전송
ssh root@172.16.1.17 "mkdir -p /home/yhs2/integrated-voting-system/consumer"
scp .\consumer\Dockerfile root@172.16.1.17:/home/yhs2/integrated-voting-system/consumer/
scp .\consumer\requirements.txt root@172.16.1.17:/home/yhs2/integrated-voting-system/consumer/

# frontend 디렉토리와 파일 전송
ssh root@172.16.1.17 "mkdir -p /home/yhs2/integrated-voting-system/frontend"
scp .\frontend\Dockerfile root@172.16.1.17:/home/yhs2/integrated-voting-system/frontend/

# logs 디렉토리 생성
ssh root@172.16.1.17 "mkdir -p /home/yhs2/integrated-voting-system/logs"

# 설정 스크립트 전송 및 실행 권한 부여
scp .\setup-integrated-env.sh root@172.16.1.17:/home/yhs2/integrated-voting-system/
ssh root@172.16.1.17 "chmod +x /home/yhs2/integrated-voting-system/setup-integrated-env.sh"

Write-Host "전송 완료! VM2에서 다음 명령을 실행하세요:"
Write-Host "cd /home/yhs2/integrated-voting-system && ./setup-integrated-env.sh" 