# Implementation Roadmap
**Generated:** 2025-01-30
**Architect:** Architect Agent

## Executive Summary
- Total tickets approved: 7
- Estimated timeline: 4-6 weeks (2-3 sprints) + Phase 0 (1-2 days)
- Critical path: TICKET-007 → TICKET-008 → TICKET-013
- Key milestones: Parallel processing (Week 2), Multi-expression support (Week 4), Production deployment (Week 6)

## Strategic Context
This implementation plan addresses:
1. **API Infrastructure** - TICKET-010, TICKET-011 (2 tickets)
2. **Performance Optimization** - TICKET-007 (1 ticket)
3. **Feature Enhancement** - TICKET-008 (1 ticket)
4. **Bug Fixes** - TICKET-013 (1 ticket)
5. **Operations** - TICKET-009, TICKET-012 (2 tickets)

### Architectural Vision
Where we're headed:
- **Performance**: 3-5x faster expression analysis through parallel processing
- **Richness**: Multiple expressions per context for richer educational content
- **Reliability**: Production-grade deployment with Docker, CI/CD, and monitoring

### Expected Outcomes
After completing this roadmap:
- **Performance**: Expression analysis 3-5x faster
- **Content Quality**: Richer educational content with multiple expressions per context
- **Deployment**: Consistent, reproducible production environments
- **Automation**: CI/CD pipeline for reliable releases

---

## Phase 1: Sprint 1 (Weeks 1-2)
**Focus:** Performance optimization - parallel LLM processing
**Duration:** 2 weeks
**Dependencies:** None

### TICKET-007: Implement Parallel LLM Request Processing
- **Priority:** High
- **Effort:** 2-3 days
- **Why first:** Performance foundation, unblocks larger expression sets for TICKET-008
- **Owner:** Senior engineer

**Key Deliverables:**
- `ExpressionBatchProcessor` extended to support `save_output` parameter
- `LangFlixPipeline._analyze_expressions` uses parallel processing
- Configuration for enabling/disabling parallel processing
- Rate limiting and error handling
- Performance benchmarks (3x+ improvement verified)

**Success Criteria:**
- [ ] Parallel processing actually works (no sequential loops!)
- [ ] 3x+ performance improvement for 10+ chunks
- [ ] Rate limit handling with circuit breaker
- [ ] Graceful degradation on partial failures
- [ ] All existing tests pass

**Phase 1 Risks:**
- Risk: Gemini API rate limits
  - Mitigation: Conservative default (max 5 workers), auto-adjust
- Risk: Implementation bug (sequential loop)
  - Mitigation: Code review, integration tests

---

## Phase 2: Sprint 2 (Weeks 3-4)
**Focus:** Feature enhancement - multiple expressions per context
**Duration:** 2 weeks
**Dependencies:** Phase 1 complete (helps with larger expression sets)

### TICKET-008: Support Multiple Expressions Per Context
- **Priority:** High
- **Effort:** 4-5 days (Phase 1: separate mode) + 3-4 days (Phase 2: combined mode) = 7-9 days total
- **Why now:** Builds on parallel processing, enables richer content
- **Owner:** Senior engineer

**Key Deliverables:**
- `ExpressionGroup` model (backward compatible)
- Expression grouping logic
- Shared context clip reuse
- Separate mode (default, backward compatible)
- Optional combined mode (Phase 2)

**Success Criteria:**
- [ ] ExpressionGroup model working
- [ ] Grouping logic handles edge cases
- [ ] Separate mode fully backward compatible
- [ ] Video clip caching/reuse verified
- [ ] Integration tests pass

**Phase 2 Risks:**
- Risk: Breaking existing workflows
  - Mitigation: Separate mode default, single expressions = groups of 1
- Risk: Video processing complexity
  - Mitigation: Start with separate mode, add combined later

---

## Phase 3: Sprint 3+ (Weeks 5-6+)
**Focus:** Production deployment infrastructure
**Duration:** 2+ weeks
**Dependencies:** Core features stable (Phase 1-2)

### TICKET-009: Production Dockerization & TrueNAS Deployment
- **Priority:** High
- **Effort:** 4-5 days (simplified without Celery)
- **Why now:** Production readiness after core features stable
- **Owner:** DevOps engineer or senior backend engineer

**Key Deliverables:**
- Multi-stage Dockerfile (builder, runtime, api)
- Docker Compose for TrueNAS (API + Redis + optional PostgreSQL)
- GitHub Actions CI/CD pipeline
- Health checks and monitoring
- Security hardening (non-root, secrets)
- Deployment documentation

**Success Criteria:**
- [ ] Docker images build successfully (< 500MB)
- [ ] Services start correctly (API + Redis)
- [ ] Health checks passing
- [ ] CI/CD pipeline working
- [ ] Security scan passes
- [ ] TrueNAS deployment tested

**Phase 3 Risks:**
- Risk: Over-engineering
  - Mitigation: Simplified stack (no Celery unless needed)
- Risk: Complex deployment
  - Mitigation: Phased rollout, comprehensive docs

---

## Dependency Graph
```
TICKET-007 (Phase 1)
  └─> TICKET-008 (Phase 2) - parallel processing helps with larger expression sets
  
TICKET-009 (Phase 3)
  └─> Independent (can proceed after core features stable)
```

## Critical Path
The longest dependency chain:
1. TICKET-007 → TICKET-008
   Total: ~4 weeks

**Timeline Impact:**
Cannot start TICKET-008 before TICKET-007 complete (helps with performance).

---

## Resource Requirements
**Skills needed:**
- Senior engineer: 2 weeks (TICKET-007, TICKET-008)
- DevOps engineer: 1 week (TICKET-009)
- Or: Senior backend engineer: 1 week (TICKET-009)

**Infrastructure needs:**
- None for Phase 1-2
- Docker, GitHub Actions for Phase 3

---

## Risk Management

### High-Risk Items
1. **TICKET-007:** Implementation bug (sequential loop defeats parallelization)
   - Impact: No performance improvement
   - Mitigation: Code review, integration tests, performance benchmarks
   
2. **TICKET-008:** Breaking backward compatibility
   - Impact: Existing workflows fail
   - Mitigation: Default to separate mode, single expressions = groups of 1

3. **TICKET-009:** Over-engineering with unused services
   - Impact: Complex deployment, maintenance burden
   - Mitigation: Simplified stack (API + Redis only, optional DB)

### Rollback Strategy
- **Phase 1:** Disable parallel processing via config (`parallel_processing.enabled: false`)
- **Phase 2:** Feature flag to disable grouping (falls back to single-expression)
- **Phase 3:** Keep existing deployment method, Docker as additional option

---

## Success Metrics

### Short-term (After Phase 1)
- Expression analysis 3x+ faster
- Parallel processing stable (no rate limit issues)
- Memory usage acceptable

### Medium-term (After Phase 2)
- Multiple expressions per context working
- Video processing efficient (no duplicate clips)
- Backward compatibility maintained

### Long-term (After Phase 3)
- Production deployment automated
- Consistent environments (dev/staging/prod)
- CI/CD pipeline reduces manual errors

---

## Review Checkpoints
**After Phase 1:** Verify performance improvement, check rate limit handling
**After Phase 2:** Test backward compatibility, verify video clip reuse
**After Phase 3:** Validate deployment process, check security scan results

---

## Notes for Engineering Team

### Critical Implementation Notes

**TICKET-007 - CRITICAL FIX:**
The proposed Step 2 implementation has a **bug** - it still uses a sequential loop! Must use `ExpressionBatchProcessor.analyze_expression_chunks()` directly. See ticket for corrected code.

**TICKET-008 - Phased Approach:**
- Phase 1: ExpressionGroup + separate mode (backward compatible)
- Phase 2: Combined mode (optional, can defer)

**TICKET-009 - Simplified Stack:**
- Remove Celery from initial implementation (use FastAPI background tasks)
- Essential: API + Redis
- Optional: PostgreSQL (if DB enabled)
- Add Celery later if distributed workers needed

### Coordination Points
- TICKET-007 & TICKET-008: Parallel processing helps with larger expression sets
- All tickets: Maintain backward compatibility where possible

### Testing Strategy
- **TICKET-007:** Performance benchmarks required
- **TICKET-008:** Backward compatibility tests critical
- **TICKET-009:** Integration tests with Docker Compose

---

## Next Steps
1. **Week 1-2:** Execute TICKET-007 (parallel processing)
2. **Week 3-4:** Execute TICKET-008 (multi-expression support)
3. **Week 5-6+:** Execute TICKET-009 (production deployment)
4. **Ongoing:** Monitor performance, adjust as needed

---

**Roadmap Status:** ✅ Ready for implementation
**Review Date:** 2025-01-30
**Next Review:** After Phase 1 completion

---

## Phase 0: Immediate (API Infrastructure) - 2025-01-30 New
**Focus:** API infrastructure foundation
**Duration:** 1-2 days
**Dependencies:** None

### TICKET-011: Add Database Session Context Manager
- **Priority:** High
- **Effort:** < 1 day
- **Why first:** Context manager 패턴 제공, TICKET-010에 활용
- **Owner:** 중급+ engineer

**Key Deliverables:**
- `DatabaseManager.session()` context manager 추가
- `langflix/main.py` 수동 세션 관리 → context manager 리팩토링
- 기존 `get_session()` 유지 (하위 호환)
- 문서 업데이트 (context manager 권장)

**Success Criteria:**
- [ ] Context manager 자동 commit/rollback/close 동작
- [ ] 기존 코드 리팩토링 완료
- [ ] 모든 테스트 통과
- [ ] 문서 업데이트
- [ ] 리소스 누수 없음

### TICKET-010: Implement API Dependencies for DB & Storage
- **Priority:** High
- **Effort:** 1-2 days
- **Why now:** FastAPI 의존성 주입 완성, DB/Storage 사용 API 활성화
- **Owner:** 중급+ engineer

**Key Deliverables:**
- `get_db()` FastAPI dependency 구현 (TICKET-011의 context manager 활용)
- `get_storage()` FastAPI dependency 구현
- `lifespan()` DB connection pool 관리
- Health check endpoint 업데이트

**Success Criteria:**
- [ ] FastAPI `Depends(get_db)` 동작
- [ ] FastAPI `Depends(get_storage)` 동작
- [ ] Health check 실제 상태 확인
- [ ] 모든 테스트 통과
- [ ] API 문서 업데이트

**Phase 0 Risks:**
- Risk: DB connection pool 관리 충돌
  - Mitigation: 단일 DatabaseManager 인스턴스
- Risk: 스토리지 초기화 성능
  - Mitigation: 가벼운 백엔드, 영향 미미

---

## Phase 1: Sprint 1 Additions (Operations)
**Focus:** 프로덕션 모니터링
**Duration:** < 1 day
**Dependencies:** Phase 0 완료

### TICKET-012: Comprehensive Health Checks
- **Priority:** Medium
- **Effort:** < 1 day
- **Why now:** Phase 0 완료 후 DB health check 가능
- **Owner:** 중급+ engineer

**Key Deliverables:**
- `SystemHealthChecker` 구현/확장
- DB, Storage, Redis, TTS health check
- 개별 health check 엔드포인트

**Success Criteria:**
- [ ] 모든 컴포넌트 health check 동작
- [ ] 프로덕션 모니터링 통합 가능
- [ ] 부하 영향 없음
- [ ] 모든 테스트 통과

**Phase 1 Risks:**
- Risk: Health check 부하 증가
  - Mitigation: 가벼운 쿼리, 간단한 체크만

### TICKET-013: Fix Multiple Expression Video Bugs
- **Priority:** High
- **Effort:** 2-3 days
- **Why now:** TICKET-008 완료 후 안정화
- **Owner:** 중급+ backend engineer(FFmpeg 경험)

**Key Deliverables:**
- Bug 1: 타임스탬프 수정(`avoid_negative_ts` 추가)
- Bug 2: 자막 그룹 파일 사용(`group_id` 활용)
- Bug 3: `temp_*` 패턴 매칭 정리

**Success Criteria:**
- [ ] 두 번째 이상 표현식 비디오 정상 재생
- [ ] 각 표현식에 올바른 자막 표시
- [ ] 임시 파일 자동 정리
- [ ] 단일 표현식 영향 없음

**Phase 1 Risks:**
- Risk: FFmpeg 복잡도
  - Mitigation: 기존 패턴 유지, 검증 강화

---

## Updated Implementation Sequence

**Phase 0 (즉시):**
1. TICKET-011 (context manager)
2. TICKET-010 (API dependencies)

**Phase 1 (Sprint 1):**
1. TICKET-012 (health checks)
2. TICKET-007 (parallel processing)
3. TICKET-008 (multi-expression)
4. TICKET-013 (multi-expression bug fixes)

**Phase 2-3:** 기존 계획대로

---

## Overall Progress
- **Completed Phases:** None
- **Current Phase:** Phase 0 (Immediate)
- **Total Tickets Approved:** 7 (TICKET-007, 008, 009, 010, 011, 012, 013)
- **Estimated Timeline:** Phase 0 (1-2 days) → Phase 1 (2 weeks) → Phase 2-3 (계속)

---

**Roadmap Status:** ✅ Updated with new tickets
**Last Updated:** 2025-01-30
**Next Steps:** Start Phase 0 immediately
