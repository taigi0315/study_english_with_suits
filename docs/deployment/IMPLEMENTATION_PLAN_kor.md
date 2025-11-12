# TICKET-009 구현 계획 (한국어)

## 개요

이 문서는 TICKET-009 (Production Dockerization & TrueNAS Deployment)의 구현 계획을 상세히 설명합니다.

## 구현 단계

### Phase 1: 기본 Docker 인프라 ✅ (진행 중)

#### 1.1 Production Dockerfile 생성
- **파일:** `Dockerfile` (루트 디렉토리)
- **타겟:** Multi-stage build (builder, runtime, api)
- **요구사항:**
  - Python 3.11-slim 기반
  - FFmpeg 설치
  - Non-root 사용자 (langflix:1000)
  - Health check 포함
  - 이미지 크기 < 500MB 목표

#### 1.2 docker-compose.truenas.yml 업데이트
- **파일:** `deploy/docker-compose.truenas.yml`
- **변경사항:**
  - Celery 관련 서비스 제거 (worker, beat, flower)
  - PostgreSQL optional 설정
  - Redis 필수 유지
  - 환경 변수로 DB 활성화 제어

#### 1.3 .dockerignore 생성
- **파일:** `.dockerignore`
- **목적:** 빌드 컨텍스트 최소화
- **제외 항목:**
  - Git 파일
  - Python 캐시
  - 가상환경
  - 테스트 파일
  - 대용량 미디어 파일
  - 문서 (일부 제외)

### Phase 2: Health Checks & Monitoring ✅ (완료)

#### 2.1 Health Check 엔드포인트
- **상태:** 이미 구현됨
- **엔드포인트:**
  - `/health` - 기본 헬스 체크
  - `/health/detailed` - 상세 컴포넌트 체크
  - `/health/redis` - Redis 상태
  - `/health/database` - DB 상태 (optional)
  - `/health/storage` - 스토리지 상태

### Phase 3: CI/CD 파이프라인 📋 (예정)

#### 3.1 GitHub Actions 기본 설정
- **파일:** `.github/workflows/ci.yml`
- **Phase 1 (초기):**
  - Lint 검사
  - 테스트 실행
  - 이미지 빌드 (push 안 함)
  
#### 3.2 이미지 빌드 및 푸시
- **Phase 2 (추후):**
  - GitHub Container Registry에 푸시
  - 태그 관리 (branch, sha, version)

#### 3.3 배포 자동화
- **Phase 3 (추후):**
  - TrueNAS SSH 배포
  - 자동 재시작

### Phase 4: 문서화 ✅ (완료)

#### 4.1 TrueNAS 배포 가이드
- **파일:** `docs/deployment/TRUENAS_DEPLOYMENT_GUIDE_kor.md`
- **파일:** `docs/deployment/TRUENAS_DEPLOYMENT_GUIDE_eng.md`
- **내용:** 
  - 단계별 배포 가이드
  - 문제 해결
  - 유지보수

### Phase 5: 개발 도구 📋 (예정)

#### 5.1 Makefile 업데이트
- **파일:** `Makefile`
- **추가 명령:**
  - `make docker-build` - 이미지 빌드
  - `make docker-up` - 서비스 시작
  - `make docker-down` - 서비스 중지
  - `make docker-logs` - 로그 확인
  - `make docker-shell` - 컨테이너 쉘 접근

## 구현 우선순위

### High Priority (즉시)
1. ✅ TrueNAS 배포 가이드 문서
2. 🔄 Production Dockerfile
3. 🔄 docker-compose.truenas.yml 업데이트
4. 📋 .dockerignore

### Medium Priority (다음)
5. 📋 Makefile 업데이트
6. 📋 CI/CD 파이프라인 (Phase 1)

### Low Priority (나중)
7. 📋 CI/CD 배포 자동화
8. 📋 모니터링 도구 통합

## 기술 결정사항

### Celery 제외 이유
- **현재 상태:** FastAPI BackgroundTasks + QueueProcessor 사용
- **Celery 코드:** 존재하지만 실제 사용되지 않음
- **결정:** Celery 제외, 필요 시 나중에 추가 가능

### PostgreSQL Optional
- **이유:** 데이터베이스는 선택적 기능
- **구현:** `DATABASE_ENABLED` 환경 변수로 제어
- **기본값:** false (DB 없이도 동작 가능)

### Redis 필수
- **이유:** 작업 큐 및 상태 관리에 필수
- **구현:** 필수 서비스로 포함

### Multi-stage Build
- **이유:** 이미지 크기 최소화
- **Stages:**
  1. builder: 의존성 빌드
  2. runtime: 런타임 환경
  3. api: API 서버

## 파일 구조

```
.
├── Dockerfile                    # [생성 예정] Production Dockerfile
├── .dockerignore                 # [생성 예정] 빌드 제외 파일
├── Makefile                      # [수정 예정] Docker 명령 추가
├── deploy/
│   └── docker-compose.truenas.yml  # [수정 예정] Celery 제거
├── .github/
│   └── workflows/
│       └── ci.yml                # [생성 예정] CI/CD 파이프라인
└── docs/
    └── deployment/
        ├── TRUENAS_DEPLOYMENT_GUIDE_kor.md  # [완료]
        ├── TRUENAS_DEPLOYMENT_GUIDE_eng.md  # [완료]
        └── IMPLEMENTATION_PLAN_kor.md        # [현재 파일]
```

## 테스트 계획

### 로컬 테스트
1. Dockerfile 빌드 테스트
2. docker-compose up 테스트
3. Health check 엔드포인트 테스트
4. 서비스 간 통신 테스트

### TrueNAS 테스트
1. 실제 TrueNAS 서버에 배포
2. 미디어 파일 접근 테스트
3. 출력 디렉토리 쓰기 테스트
4. 성능 및 리소스 사용량 확인

## 성공 기준

- [x] TrueNAS 배포 가이드 문서 완성
- [ ] Dockerfile 빌드 성공 (< 500MB)
- [ ] docker-compose로 모든 서비스 시작 성공
- [ ] Health check 엔드포인트 정상 동작
- [ ] TrueNAS 실제 배포 성공
- [ ] CI/CD 파이프라인 통과 (Phase 1)

## 참고 자료

- [TICKET-009](../tickets/approved/TICKET-009-production-dockerization-trunas-deployment.md)
- [TrueNAS 배포 가이드](TRUENAS_DEPLOYMENT_GUIDE_kor.md)
- [Docker 문서](https://docs.docker.com/)
- [FastAPI 배포](https://fastapi.tiangolo.com/deployment/)

---

**마지막 업데이트:** 2025-01-30

