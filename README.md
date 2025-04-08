# 투표 시스템 프로젝트

이 프로젝트는 분산 시스템 환경에서 동작하는 투표 시스템을 구현한 것입니다.

## 시스템 구성

- **VM2 (API Server)**: FastAPI를 사용한 API 서버, Kafka 프로듀서 및 Redis 연동
- **VM3 (Worker)**: Kafka 컨슈머 및 PostgreSQL 데이터베이스 연동
- **VM4 (Frontend)**: Next.js를 사용한 웹 프론트엔드

## 디렉토리 구조

```
python-project/
├── vm2-api-server/    # FastAPI, Kafka, Redis 코드
├── vm3-worker/        # Kafka Consumer, PostgreSQL 코드
└── vm4-frontend/      # Next.js 프론트엔드 코드
```

## 기능

- 사용자가 월 1회 회식과 2주 1회 회식에 대해 찬성/반대 투표 가능
- 투표 결과는 실시간으로 집계되어 결과 페이지에 표시
- 사용자별 중복 투표 방지
