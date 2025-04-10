# 투표 시스템 프로젝트
회식 빈도(월 1회 vs 2주 1회)에 대한 투표 시스템입니다.
## 시스템 구성
- VM2 (172.16.1.17): FastAPI API 서버, Kafka Producer, Redis
- VM3 (172.16.1.18): Kafka Consumer, PostgreSQL 연결
- VM4 (172.16.1.19): Next.js 프론트엔드
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
