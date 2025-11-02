# ADR-017: Production Dockerization & TrueNAS Deployment

**Date:** 2025-01-30  
**Status:** Proposed  
**Deciders:** Development Team  
**Related ADRs:** ADR-012 (FastAPI Application Scaffold)

## Context

현재 배포 환경이 일관되지 않고 TrueNAS 환경에 최적화되어 있지 않습니다.

### Problems

1. Docker 이미지가 프로덕션용이 아님
2. TrueNAS 배포 가이드/설정 부재
3. CI/CD 없음
4. 보안/헬스체크/모니터링 부족

## Decision

프로덕션용 Docker와 배포 파이프라인을 구축합니다.

### Architecture

#### Multi-Stage Dockerfile

```
Builder Stage → Runtime Stage → Specialized Targets
                                ├─ API
                                ├─ Frontend
                                ├─ Celery Worker
                                └─ CLI
```

#### Deployment Stack

```
┌─────────────────────────────────────────────┐
│         TrueNAS Host System                 │
├─────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │ LangFlix │  │ LangFlix │  │ PostgreSQL│ │
│  │   API    │  │ Frontend │  │  Database │ │
│  └──────────┘  └──────────┘  └───────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │  Celery  │  │  Celery  │  │  Redis    │ │
│  │  Worker  │  │   Beat   │  │   Cache   │ │
│  └──────────┘  └──────────┘  └───────────┘ │
└─────────────────────────────────────────────┘
```

### Components

1. Multi-stage Build
2. Docker Compose Stack (API, Frontend, PostgreSQL, Redis, Celery, Flower)
3. GitHub Actions CI/CD
4. Health Checks, 모니터링, 로그
5. 보안 (비루트, secrets 관리, Trivy 스캔)
6. TrueNAS 배포 가이드

### Configuration

환경별 override:
- `docker-compose.truenas.yml`
- `docker-compose.dev.yml`
- `docker-compose.override.yml` (로컬)

비밀 관리:
- Docker Secrets
- 환경 변수
- .env(.gitignore)

### Deployment Flow

```
Code Push → GitHub Actions:
  1. Lint & Format Check
  2. Run Tests (unit, integration, functional)
  3. Build Docker Images
  4. Security Scan
  5. Push to Container Registry
  6. Deploy to TrueNAS
  7. Run Migrations
  8. Health Checks
  9. Notify
```

## Consequences

### Benefits

- 일관된 배포
- TrueNAS 지원
- CI/CD 자동화
- 보안 강화
- 모니터링
- 확장성(워커 스케일)
- 개발/운영 분리

### Trade-offs

- Docker 기반
- 초기 설정 비용
- 운영 복잡도 증가
- 이미지 크기/빌드 시간

### Risks & Mitigations

**Risk**: Docker 체크포인트  
**Mitigation**: 가이드, 단계적 배포

**Risk**: 리소스 사용  
**Mitigation**: 리미트, 모니터링

**Risk**: Secrets 노출  
**Mitigation**: Docker Secrets + rotation

**Risk**: 다운타임  
**Mitigation**: 롤링 업데이트, 헬스체크

## Alternatives Considered

**Option 1**: Single Dockerfile  
- 장점: 단순
- 단점: 환경 분리 어려움

**Option 2**: Kubernetes  
- 장점: 확장성
- 단점: TrueNAS 불필요, 복잡함

**Option 3**: Docker Compose + Multi-stage  
- 장점: 균형
- 선택

## Success Criteria

- 모든 스테이지 빌드 성공
- 이미지 크기 절감(멀티 스테이지)
- TrueNAS 배포 정상
- CI/CD 전체 통과
- 보안 스캔 통과
- 헬스체크 100% 통과
- 문서화 완료

## References

- TICKET-003: Production Dockerization
- Docker Docs
- TrueNAS Docs
- GitHub Actions Docs

## Next Steps

1. 멀티 스테이지 Dockerfile 작성
2. Compose 스택 구축
3. GitHub Actions 구성
4. TrueNAS 가이드 작성
5. 배포 테스트
6. 모니터링 통합


