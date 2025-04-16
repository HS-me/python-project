# VM2 API 서버

FastAPI를 사용한 API 서버와 Kafka 프로듀서, Redis 연동 코드입니다.

## 기능

- `/api/vote`: 투표 데이터를 받아 Kafka로 전송하는 API
- `/api/results`: Redis에서 집계된 투표 결과를 조회하는 API

## 기술 스택

- FastAPI: API 서버 프레임워크
- Kafka: 메시지 큐로 투표 이벤트 전송
- Redis: 투표 결과 집계 및 저장

## 실행 방법

```bash
cd app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
``` 