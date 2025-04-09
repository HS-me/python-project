# 투표 시스템 프로젝트
회식 빈도(월 1회 vs 2주 1회)에 대한 투표 시스템입니다.
## 시스템 구성
- VM2 (172.16.1.17): FastAPI API 서버, Kafka Producer, Redis
- VM3 (172.16.1.18): Kafka Consumer, PostgreSQL 연결
- VM4 (172.16.1.19): Next.js 프론트엔드

# 투표 시스템 프로젝트
회식 빈도(월 1회 vs 2주 1회)에 대한 투표 시스템입니다.
## 시스템 구성
- VM2 (172.16.1.17): FastAPI API 서버, Kafka Producer, Redis
- VM3 (172.16.1.18): Kafka Consumer, PostgreSQL 연결
- VM4 (172.16.1.19): Next.js 프론트엔드
## 실행 방법

# 투표 시스템 클러스터 구조 및 데이터 흐름

## 클러스터 구조

현재 투표 시스템은 4개의 VM에서 분산되어 실행되는 마이크로서비스 아키텍처로 구성되어 있습니다:

**VM1 (172.16.1.16)**
- Kubernetes Control Plane (마스터 노드)
- 현재 시스템은 VM에서 직접 실행 중이지만, 향후 Kubernetes 클러스터로 마이그레이션 예정

**VM2 (172.16.1.17)**
- FastAPI API 서버
- Kafka 브로커
- Zookeeper
- Redis (투표 결과 캐싱)

**VM3 (172.16.1.18)**
- Kafka Consumer (Worker)
- PostgreSQL (투표 데이터 영구 저장)

**VM4 (172.16.1.19)**
- Next.js 프론트엔드

## 데이터 흐름 및 투표 과정

1. **투표 제출 (사용자 → VM4 → VM2)**
   - 사용자가 브라우저에서 `http://172.16.1.19:3000` 접속
   - Next.js 프론트엔드에서 월 1회 또는 2주 1회 회식에 대한 찬성/반대 투표 선택
   - 투표 데이터는 axios를 통해 VM2의 FastAPI 서버로 전송:
     ```javascript
     axios.post('http://172.16.1.17:8000/api/vote', {
       user_id: 'anonymous-' + 랜덤ID,
       candidate_id: '후보ID',  // monthly 또는 biweekly
       vote_type: '투표유형'    // for 또는 against
     })
     ```

2. **메시지 생성 및 전송 (VM2: API 서버 → Kafka)**
   - FastAPI 서버의 `/api/vote` 엔드포인트가 요청 수신
   - Vote 모델 객체 생성 및 유효성 검증
   - KafkaVoteProducer가 투표 데이터를 JSON으로 직렬화
   - 직렬화된 데이터가 Kafka의 "vote-events" 토픽으로 전송
   - API 서버가 클라이언트에게 성공 응답 반환

3. **메시지 소비 및 데이터 저장 (VM3: Kafka Consumer → PostgreSQL 및 Redis)**
   - Kafka Consumer가 "vote-events" 토픽에서 메시지 소비
   - 메시지에서 user_id, candidate_id, vote_type 추출
   - PostgreSQL 데이터베이스에 투표 기록 저장
   - Redis에 투표 집계 업데이트:
     - `vote_result:{candidate_id}` 키 값 증가 (전체 투표수)
     - `vote_result:{candidate_id}:{vote_type}` 키 값 증가 (찬성/반대 투표수)
   - 메시지 처리 상태를 MessageTracker를 통해 기록

4. **결과 조회 (사용자 → VM4 → VM2 → Redis)**
   - 사용자가 브라우저에서 `http://172.16.1.19:3000/results` 접속
   - Next.js 프론트엔드가 axios를 통해 VM2의 API 서버에 결과 요청:
     ```javascript
     axios.get('http://172.16.1.17:8000/api/results')
     ```
   - VM2의 API 서버가 Redis에서 최신 투표 결과 조회
   - 투표 결과를 JSON 형식으로 클라이언트에게 반환:
     ```json
     {
       "results": {
         "monthly": {"for": 31, "against": 3, "total": 34},
         "biweekly": {"for": 16, "against": 1, "total": 17}
       }
     }
     ```
   - 프론트엔드가 결과를 시각화하여 표시 (프로그레스 바, 수치 등)

## 주요 기술 스택

- **프론트엔드**: Next.js, React, Axios
- **백엔드**: FastAPI, Pydantic
- **메시지 큐**: Apache Kafka
- **데이터베이스**: PostgreSQL (영구 저장), Redis (캐싱)
- **컨테이너화 준비**: Kubernetes (미래 배포 방식)

## 데이터 정합성 및 장애 대응

- Redis와 PostgreSQL 간의 데이터 정합성 검증 기능
- 메시지 추적 시스템으로 투표 처리 상태 모니터링
- 실패한 메시지 재처리 기능
- 분산 시스템 구조로 한 구성 요소의 일시적 장애가 전체 시스템에 영향을 미치지 않음
