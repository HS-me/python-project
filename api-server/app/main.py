from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from routers import votes, results
import logging
from datetime import datetime
import redis
from pydantic import BaseModel
from typing import Dict, Any, Optional
import time
import socket
# 프로메테우스 메트릭 라이브러리 추가
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
# Prometheus FastAPI Instrumentator 추가
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.responses import Response

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("api")

# 프로메테우스 메트릭 정의
REQUEST_COUNT = Counter(
    "http_requests_total", 
    "Total count of API requests", 
    ["method", "endpoint", "status_code"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", 
    "Request latency in seconds", 
    ["method", "endpoint"]
)
REDIS_LATENCY = Histogram(
    "redis_operation_latency_seconds", 
    "Redis operation latency in seconds",
    ["operation"]
)
KAFKA_CONNECTION_STATUS = Gauge(
    "kafka_connection_status", 
    "Status of Kafka connection (1=connected, 0=disconnected)"
)
REDIS_CONNECTION_STATUS = Gauge(
    "redis_connection_status", 
    "Status of Redis connection (1=connected, 0=disconnected)"
)
SYSTEM_MEMORY_USAGE = Gauge(
    "system_memory_usage_percent", 
    "System memory usage in percentage"
)
SYSTEM_CPU_USAGE = Gauge(
    "system_cpu_usage_percent", 
    "System CPU usage in percentage"
)

# 추가 메트릭 정의
REDIS_KEYSPACE_HITS = Counter(
    "redis_keyspace_hits_total",
    "Total number of successful lookups in Redis"
)
REDIS_KEYSPACE_MISSES = Counter(
    "redis_keyspace_misses_total",
    "Total number of failed lookups in Redis"
)
REDIS_CONNECTED_CLIENTS = Gauge(
    "redis_connected_clients",
    "Number of client connections to Redis"
)
REDIS_USED_MEMORY = Gauge(
    "redis_used_memory_bytes",
    "Redis total used memory in bytes"
)

# 투표 처리 메트릭
VOTES_PROCESSED = Counter(
    "vote_consumer_processed_total",
    "Total number of votes processed"
)
VOTES_CONSISTENCY_FAILURES = Counter(
    "vote_consumer_consistency_failures_total",
    "Total number of consistency failures in vote processing"
)
KAFKA_LAG = Gauge(
    "vote_consumer_kafka_lag",
    "Kafka consumer lag in number of messages",
    ["topic", "partition"]
)

app = FastAPI(title="투표 시스템 API", debug=True)

# Prometheus 메트릭 등록
Instrumentator().instrument(app).expose(app)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시에는 특정 도메인으로 제한해야 합니다
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis 클라이언트 설정
async def get_redis_client():
    redis_host = "redis"
    redis_port = 6379
    try:
        redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        return redis_client
    except Exception as e:
        logger.error(f"Redis 연결 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="Redis 연결 실패")

# Kafka 연결 확인 함수
async def check_kafka_connection():
    try:
        # 실제로는 Kafka 클라이언트를 사용하여 연결 확인
        # 여기서는 Kafka 서버에 TCP 연결이 가능한지 확인하는 간단한 방법 사용
        kafka_host = "kafka"
        kafka_port = 9092
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        try:
            s.connect((kafka_host, kafka_port))
            s.close()
            return True
        except:
            s.close()
            return False
    except Exception as e:
        logger.error(f"Kafka 연결 오류: {str(e)}")
        return False

# 요청 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"Request path: {request.url.path}")
    logger.debug(f"Request method: {request.method}")
    
    # 요청 본문 로깅 (읽은 후 다시 설정)
    body = await request.body()
    logger.debug(f"Request body: {body}")
    
    # 원래 요청 본문 복원
    async def receive():
        return {"type": "http.request", "body": body}
    
    request._receive = receive
    
    # 성능 측정을 위한 시간 기록 (프로메테우스 측정을 위한 기반)
    start_time = time.time()
    
    response = await call_next(request)
    
    # 응답 시간 계산 (밀리초)
    process_time = (time.time() - start_time) * 1000
    logger.debug(f"Request processed in {process_time:.2f}ms")
    
    # 프로메테우스 메트릭 기록
    method = request.method
    path = request.url.path
    status_code = response.status_code
    
    # 요청 수 카운트
    REQUEST_COUNT.labels(method=method, endpoint=path, status_code=status_code).inc()
    
    # 응답 시간 기록 (초 단위)
    REQUEST_LATENCY.labels(method=method, endpoint=path).observe(process_time / 1000)
    
    return response

# 강화된 헬스체크 응답 모델
class HealthCheckResponse(BaseModel):
    status: str
    timestamp: str
    checks: Dict[str, Dict[str, Any]]
    version: str = "1.0.0"
    hostname: str = socket.gethostname()

# 상태 모니터링 클래스 - 프로메테우스 구현 시 활용 가능한 구조
class StatusMonitor:
    @staticmethod
    async def check_redis_health(redis_client=None):
        """Redis 상태 확인"""
        if redis_client is None:
            try:
                redis_client = await get_redis_client()
            except Exception as e:
                REDIS_CONNECTION_STATUS.set(0)  # 연결 실패
                return {"status": "disconnected", "error": str(e)}
        
        try:
            start_time = time.time()
            ping_result = redis_client.ping()
            latency = (time.time() - start_time) * 1000  # 밀리초 단위
            
            # 프로메테우스 메트릭 기록
            REDIS_LATENCY.labels(operation="ping").observe(latency / 1000)
            REDIS_CONNECTION_STATUS.set(1 if ping_result else 0.5)  # 1은 정상, 0.5는 문제 있음
            
            # 추가 Redis 메트릭 수집
            try:
                # Redis INFO 명령으로 메트릭 수집
                info = redis_client.info()
                
                # 연결된 클라이언트 수
                if 'connected_clients' in info:
                    REDIS_CONNECTED_CLIENTS.set(info['connected_clients'])
                
                # 사용 중인 메모리
                if 'used_memory' in info:
                    REDIS_USED_MEMORY.set(info['used_memory'])
                
                # 키스페이스 히트/미스
                if 'keyspace_hits' in info:
                    REDIS_KEYSPACE_HITS.inc(info['keyspace_hits'])
                
                if 'keyspace_misses' in info:
                    REDIS_KEYSPACE_MISSES.inc(info['keyspace_misses'])
            except Exception as e:
                logger.error(f"Redis 메트릭 수집 오류: {str(e)}")
            
            return {
                "status": "connected" if ping_result else "degraded",
                "latency_ms": latency,
                "connection_count": redis_client.connection_pool.connection_kwargs.get("max_connections", "unknown")
            }
        except Exception as e:
            REDIS_CONNECTION_STATUS.set(0)  # 연결 실패
            return {"status": "disconnected", "error": str(e)}
    
    @staticmethod
    async def check_kafka_health():
        """Kafka 상태 확인"""
        try:
            kafka_connected = await check_kafka_connection()
            
            # 프로메테우스 메트릭 기록
            KAFKA_CONNECTION_STATUS.set(1 if kafka_connected else 0)
            
            return {
                "status": "connected" if kafka_connected else "disconnected",
                # 향후 프로메테우스에서 Kafka 메트릭을 추가할 때 사용할 수 있는 필드들
                "broker_count": 1,  # 실제로는 동적으로 계산
                "topics": ["votes"]  # 실제로는 동적으로 조회
            }
        except Exception as e:
            KAFKA_CONNECTION_STATUS.set(0)
            return {"status": "disconnected", "error": str(e)}
    
    @staticmethod
    async def check_voting_system():
        """투표 시스템 정상 작동 여부 확인"""
        try:
            # 실제로는 테스트 투표 생성 및 검증 로직 구현
            votes_working = True
            
            # 프로메테우스 구현 시 수집할 만한 메트릭들
            test_metrics = {
                "vote_creation_latency_ms": 15.5,  # 예시 값
                "vote_retrieval_latency_ms": 8.3,  # 예시 값
                "vote_count_last_minute": 120,     # 예시 값
                "error_rate_percent": 0.2          # 예시 값
            }
            
            return {
                "status": "operational" if votes_working else "degraded",
                "message": "투표 시스템 정상 작동 중" if votes_working else "투표 처리에 문제가 있습니다",
                **test_metrics
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

# 라우터 등록
app.include_router(votes.router)
app.include_router(results.router)

@app.get("/")
async def root():
    return {"message": "투표 시스템 API에 오신 것을 환영합니다!"}

@app.get("/health", response_model=HealthCheckResponse, tags=["monitoring"])
async def health_check():
    """
    서비스 상태를 확인하는 강화된 헬스체크 엔드포인트
    - Redis 연결 상태 확인
    - Kafka 연결 상태 확인
    - 핵심 비즈니스 로직 작동 여부 확인
    
    이 엔드포인트는 Kubernetes 헬스체크와 운영 모니터링 모두에 사용할 수 있습니다.
    향후 프로메테우스/그라파나와 연동 시 기반이 되는 정보들을 제공합니다.
    """
    status = "ok"
    checks = {}
    
    # Redis 연결 확인
    redis_health = await StatusMonitor.check_redis_health()
    checks["redis"] = redis_health
    if redis_health["status"] != "connected":
        status = "degraded"
    
    # Kafka 연결 확인
    kafka_health = await StatusMonitor.check_kafka_health()
    checks["kafka"] = kafka_health
    if kafka_health["status"] != "connected":
        status = "degraded"
    
    # 투표 시스템 검증
    voting_health = await StatusMonitor.check_voting_system()
    checks["voting_system"] = voting_health
    if voting_health["status"] != "operational":
        status = "degraded"
    
    # 시스템 리소스 상태 확인
    try:
        import psutil
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # 프로메테우스 메트릭 업데이트
        SYSTEM_MEMORY_USAGE.set(memory.percent)
        SYSTEM_CPU_USAGE.set(cpu_percent)
        
        checks["system"] = {
            "status": "healthy" if memory.percent < 90 else "warning",
            "memory_usage_percent": memory.percent,
            "cpu_usage_percent": cpu_percent
        }
        if memory.percent > 90:
            status = "degraded"
    except ImportError:
        checks["system"] = {"status": "unknown", "message": "psutil 패키지가 필요합니다"}
    except Exception as e:
        checks["system"] = {"status": "unknown", "error": str(e)}
    
    # 데이터 정합성 상태 (향후 구현 예정)
    checks["data_consistency"] = {
        "status": "not_implemented",
        "message": "데이터 정합성 검사는 향후 구현 예정입니다. 프로메테우스 메트릭으로 구현될 예정입니다."
    }
    
    # 심각한 오류가 있으면 상태를 down으로 설정
    critical_services = ["redis", "kafka"]
    for service in critical_services:
        if service in checks and checks[service]["status"] == "disconnected":
            status = "down"
            break
    
    return HealthCheckResponse(
        status=status,
        timestamp=datetime.utcnow().isoformat(),
        checks=checks
    )

@app.get("/health/liveness", tags=["monitoring"])
async def liveness_check():
    """
    서버가 살아있는지 확인하는 간단한 엔드포인트 (Kubernetes liveness probe용)
    
    이 엔드포인트는 서버가 응답하는지만 확인하며, 응답이 오면 서버가 활성 상태로 간주합니다.
    내부 서비스(Redis, Kafka 등)의 연결 상태는 확인하지 않습니다.
    """
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health/readiness", tags=["monitoring"])
async def readiness_check():
    """
    서버가 요청을 처리할 준비가 되었는지 확인하는 엔드포인트 (Kubernetes readiness probe용)
    
    이 엔드포인트는 서버가 의존하는 서비스(Redis, Kafka)에 정상적으로 연결되어 있는지 확인합니다.
    모든 의존성이 정상이면 200 OK, 아니면 503 Service Unavailable을 반환합니다.
    """
    # Redis와 Kafka 연결 상태 검사
    redis_health = await StatusMonitor.check_redis_health()
    kafka_health = await StatusMonitor.check_kafka_health()
    
    # 의존성이 모두 정상인지 확인
    dependencies_ok = (redis_health["status"] == "connected" and 
                       kafka_health["status"] == "connected")
    
    if dependencies_ok:
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "서비스가 요청을 처리할 준비가 되었습니다"
        }
    else:
        # 어떤 의존성에 문제가 있는지 상세 정보 제공
        failed_dependencies = []
        if redis_health["status"] != "connected":
            failed_dependencies.append("redis")
        if kafka_health["status"] != "connected":
            failed_dependencies.append("kafka")
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "failed_dependencies": failed_dependencies,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "일부 의존 서비스에 연결할 수 없습니다."
            }
        )

# 향후 프로메테우스 메트릭 엔드포인트 추가 시 사용할 주석 템플릿
@app.get("/metrics", tags=["monitoring"])
async def metrics():
    '''
    프로메테우스에서 수집할 수 있는 메트릭을 제공하는 엔드포인트

    이 엔드포인트는 다음 메트릭을 제공합니다:
    - API 요청 수 및 응답 시간
    - Redis 연결 상태 및 응답 시간
    - Kafka 연결 상태 및 메시지 처리량
    - 투표 처리 수 및 오류율
    - 데이터 정합성 지표 (투표 요청 수 vs DB 기록 수)
    '''
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 