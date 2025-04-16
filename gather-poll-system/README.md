# 투표 시스템 (Gather Poll System)

## 개요
회식 빈도(월 1회 vs 2주 1회)에 대한 실시간 투표 시스템을 구현한 분산 아키텍처 애플리케이션입니다. 

## 시스템 아키텍처

### VM2 (API 서버 - 메인 백엔드)
- **역할**: 투표 API 제공, Kafka 메시지 생산자, Redis 결과 관리
- **기술 스택**: FastAPI, Kafka Producer, Redis 클라이언트
- **서비스 컴포넌트**:
  - `app/main.py`: 애플리케이션 진입점
  - `app/routers/votes.py`: 투표 API 엔드포인트
  - `app/routers/results.py`: 결과 조회 API
  - `app/services/kafka_producer.py`: Kafka 메시지 전송
  - `app/services/redis_service.py`: Redis 데이터 관리
  - `app/models/vote.py`: 데이터 모델 정의
- **데이터 흐름**: 투표 요청 수신 → 유효성 검증 → Redis 업데이트 → Kafka 메시지 발행 → 응답 반환
- **포트**: 8000 (HTTP)

### VM3 (Consumer 서비스)
- **역할**: Kafka 메시지 소비, PostgreSQL 데이터 저장
- **기술 스택**: Kafka Consumer, PostgreSQL, Redis 클라이언트
- **주요 기능**: 중복 처리 방지, 영구 저장, 재시도 메커니즘
- **데이터 흐름**: 이벤트 소비 → 중복 검사 → DB 저장 → 결과 업데이트 → 상태 기록 → 오프셋 커밋

### VM4 (Frontend 서비스)
- **역할**: 사용자 인터페이스 제공
- **기술 스택**: Next.js, Axios
- **주요 페이지**: 투표 페이지(`/`), 결과 페이지(`/results`)
- **포트**: 3000 (HTTP)

## 인프라 구성 요소

### Kafka
- **역할**: 이벤트 메시징 시스템
- **설정**: 토픽 `vote-events`, 복제 팩터 1, 파티션 1
- **장점**: 서비스 간 느슨한 결합, 메시지 내구성, 확장성

### Redis
- **역할**: 인메모리 데이터 저장소
- **사용 사례**: 실시간 집계, 상태 추적, 중복 방지
- **데이터 구조**: 카운터, 정렬된 집합, 일반 집합

### PostgreSQL
- **역할**: 영구 데이터 저장소
- **테이블**: `votes`, `vote_results`, `message_status`

## 메시지 정합성 보장
1. 고유 식별자 사용
2. 메시지 상태 추적 (produced → consumed → processed)
3. 중복 제거 메커니즘
4. 멱등성 처리
5. 데이터 일관성 검증

## 실행 방법

### Docker Compose
```bash
# 시스템 구동
docker compose up -d

# 상태 확인
docker compose ps
```

## API 엔드포인트
- `POST /api/vote`: 투표 제출
- `GET /api/results`: 결과 조회
- `GET /api/message/{message_id}`: 메시지 상태 조회
- `GET /api/stats`: 통계 조회

## 성능 최적화
- Kafka 메시지 배치 처리
- Redis 파이프라인 활용
- PostgreSQL 인덱싱 및 벌크 연산
- Docker 볼륨 마운트로 데이터 영속성 보장

## 모니터링 및 디버깅
- 구조화된 로깅
- Kafka UI 모니터링
- 메시지 처리 상태 추적 API
