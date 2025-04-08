# VM3 워커

Kafka 컨슈머와 PostgreSQL 데이터베이스 연동 코드입니다.

## 기능

- Kafka 메시지 큐에서 투표 이벤트를 소비
- 투표 데이터를 PostgreSQL 데이터베이스에 저장
- 투표 결과를 집계하여 Redis에 저장

## 기술 스택

- Kafka: 메시지 큐로부터 투표 이벤트 소비
- PostgreSQL: 투표 데이터 영구 저장
- Redis: 실시간 투표 결과 집계 저장

## 실행 방법

```bash
cd app
python consumer.py
``` 