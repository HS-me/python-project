# 투표 시스템 프로젝트
회식 빈도(월 1회 vs 2주 1회)에 대한 투표 시스템입니다.
## 시스템 구성
- VM1 (172.16.1.16): DNS 서버 (dnsmasq)
- VM2 (172.16.1.17): FastAPI API 서버, Kafka Producer, Redis
- VM3 (172.16.1.18): Kafka Consumer, PostgreSQL 연결
- VM4 (172.16.1.19): Next.js 프론트엔드
## DNS 설정
시스템은 VM1(172.16.1.16)에 구성된 DNS 서버를 통해 서비스 간 통신을 수행합니다. 각 서비스는 다음과 같은 도메인 이름으로 접근할 수 있습니다:

- API 서버: api-service.cluster.local
- Redis 서버: redis-service.cluster.local
- Kafka 서버: kafka-service.cluster.local
- PostgreSQL 서버: postgres-service.cluster.local
- Consumer 서버: consumer-service.cluster.local
- Frontend 서버: frontend-service.cluster.local

모든 서비스는 환경 변수를 통해 이러한 도메인 이름을 사용하도록 구성되어 있습니다.
## 실행 방법
1. VM2에서 API 서버 시작: `cd /home/yhs2/voting-system && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &`
2. VM3에서 Kafka Consumer 시작: `cd /home/yhs3/vote-consumer && python consumer.py &`
3. VM4에서 Next.js 프론트엔드 시작: `cd /home/yhs3/voting-frontend && npm run dev &`

## 데이터 흐름
1. 사용자가 Next.js 프론트엔드에서 투표를 진행합니다.
2. 프론트엔드가 API 서버로 투표 데이터를 전송합니다.
3. API 서버는 Redis에 투표 결과를 즉시 업데이트하고 Kafka에 메시지를 발행합니다.
4. Kafka Consumer가 메시지를 수신하여 PostgreSQL에 투표 데이터를 저장합니다.
5. 결과 페이지는 API 서버로부터 최신 투표 결과를 조회합니다.

## Docker Compose를 이용한 통합 환경 실행

프로젝트 전체를 한 번에 실행하기 위해 Docker Compose를 사용할 수 있습니다.

### 사전 요구사항
- Docker와 Docker Compose가 설치되어 있어야 합니다.

### 실행 방법

1. 프로젝트 루트 디렉토리로 이동합니다.
```bash
cd python-project
```

2. Docker Compose로 모든 서비스를 실행합니다.
```bash
docker-compose up -d
```

3. 서비스 상태 확인:
```bash
docker-compose ps
```

4. 로그 확인:
```bash
docker-compose logs -f
```

5. 특정 서비스의 로그만 확인:
```bash
docker-compose logs -f api-server
docker-compose logs -f consumer
```

6. 브라우저에서 다음 URL로 접속하여 프론트엔드 확인:
```
http://localhost:3000
```

7. 모든 서비스 종료:
```bash
docker-compose down
```

8. 볼륨을 포함한 모든 리소스 종료 및 삭제:
```bash
docker-compose down -v
```

## 메시지 정합성 보장

이 시스템은 다음과 같은 방식으로 메시지 처리의 정합성을 보장합니다:

1. Kafka 메시지 수신 시 message_id를 통해 중복 처리를 방지합니다.
2. Redis에서 이미 처리된 메시지인지 확인 후 스킵합니다.
3. PostgreSQL에 삽입 시 message_id의 고유성을 보장합니다.
4. 모든 단계에서 메시지 상태를 추적하여 시스템 신뢰성을 높입니다.
5. 메시지 처리가 성공한 후에만 Kafka offset을 커밋합니다.

이 구조를 통해 메시지의 at-least-once 처리를 보장하면서 동시에 중복 처리를 방지합니다.

## 서비스 실행 방법

### VM2 (API 서버) 실행
```bash
# VM2 (172.16.1.17)에서 실행
cd /home/yhs2/voting-system
docker compose up -d
```

### VM3 (Kafka Consumer) 실행
```bash
# VM3 (172.16.1.18)에서 실행
cd /home/yhs3/vote-consumer
docker compose up -d
```

### VM4 (Frontend) 실행
```bash
# VM4 (172.16.1.19)에서 실행
cd /home/yhs4/voting-frontend
docker compose up -d
```
