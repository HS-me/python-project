﻿# 투표 시스템 프로젝트
회식 빈도(월 1회 vs 2주 1회)에 대한 투표 시스템입니다.
## 시스템 구성
- VM2 (172.16.1.17): FastAPI API 서버, Kafka Producer, Redis
- VM3 (172.16.1.18): Kafka Consumer, PostgreSQL 연결
- VM4 (172.16.1.19): Next.js 프론트엔드

