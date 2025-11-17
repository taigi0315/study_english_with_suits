# [TICKET-052] YouTube 업로드 다중 타임슬롯 스케줄링(08:00/14:00/20:00, 슬롯당 2개, 일일 6개 한도)

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [x] Feature
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [x] Technical Debt (기존 스케줄러 일반화 필요)

## Impact Assessment
**Business Impact:**
- 원하는 시간대에 안정적으로 업로드되도록 자동 분배(08:00/14:00/20:00).
- 슬롯당 최대 2개 보장, 하루 최대 6개 업로드 제한으로 계정 정책/리스크 관리.
- 많은 영상을 한 번에 예약 입력해도 다음날 이후로 자연스럽게 분산 업로드.

**Technical Impact:**
- 스케줄링 정책을 “시간대 단위 슬롯(capacity)” 기반으로 일반화 필요.
- UI의 배치 스케줄 API는 이미 “다음 가용 슬롯”을 순차 탐색하지만, 슬롯 용량/타임테이블이 명확히 반영돼야 함.
- 구성값(config)으로 시간대/슬롯당 용량/일일 최대 개수 관리.

**Effort Estimate:**
- Medium (1–3 days)

## Problem Description
### Current State
**Locations:**
```12:88:langflix/youtube/schedule_manager.py
class YouTubeScheduleManager:
    def get_next_available_slot(self, video_type: str, preferred_date: Optional[date] = None) -> datetime:
        # Finds next time with daily type limits and preferred posting times
```
```1209:1261:langflix/youtube/web_ui.py
@self.app.route('/api/upload/batch/schedule', methods=['POST'])
def batch_upload_schedule():
    # Schedules sequentially via schedule_manager.get_next_available_slot(...)
```
```98:124:langflix/db/models.py
class YouTubeSchedule(Base):
    scheduled_publish_time = Column(DateTime(timezone=True), nullable=False)
```
- 현재 스케줄러는 “일일 타입별 한도 + 선호 시간대”를 고려해 다음 슬롯을 찾지만, “타임슬롯 단위 용량(슬롯당 2개)” 개념이 명확히 모델링되어 있지 않음.
- 사용자가 8개를 예약하면 요구사항대로 “하루 3개 슬롯(08/14/20시) × 슬롯당 2개 = 하루 6개”를 채우고, 남은 2개는 다음날 동일한 규칙으로 분배되어야 함.

### Root Cause Analysis
- 구성/코드에 “슬롯 용량(capacity per slot)”과 “일일 최대 업로드 수(total per day)”가 명시적으로 반영되지 않아, 다량 예약 시 원하는 분배 규칙을 100% 보장하기 어렵다.
- 일부 로직은 타입별(‘final’, ‘short’) 쿼터 중심이라 “슬롯별 용량”과 “고정 타임슬롯” 개념을 확장해야 한다.

## Proposed Solution
### Approach
1. 스케줄 구성 일반화
   - `ScheduleConfig`(또는 동등 역할 구성)에 아래 항목 추가:
     - `time_slots`: [“08:00”, “14:00”, “20:00”] (기본값)
     - `slot_capacity`: 2
     - `daily_max_total`: 6
     - (유지) 타입별 일일 한도는 현행 유지하거나 6에 맞춰 합산 제약 제공
2. 슬롯 가용성 계산 로직
   - `YouTubeScheduleManager._get_available_times_for_date()`를 확장:
     - 해당 날짜의 `time_slots` 각 시간에 대해 DB에서 같은 `scheduled_publish_time` “시:분” 매칭(또는 동일 시각 정확 매칭)으로 예약 수를 카운트
     - `count < slot_capacity`면 가용
   - 일일 총 업로드 수(`daily_max_total`)가 이미 찼으면 다음 날짜로 넘김.
3. `get_next_available_slot()` 강화
   - 날짜를 증가시키며:
     - 일일 총량 < `daily_max_total`인지 확인
     - 슬롯 순서대로 빈 슬롯 탐색(최대 `slot_capacity - 현재예약수`까지 수용)
   - 7일 이내 없으면 경고 후 7일 뒤 08:00 리턴(현행 fallback 유지/개선)
4. 배치 스케줄 API는 기존대로 “순차적으로 다음 가용 슬롯” 호출
   - 현 UI는 순차 호출이므로, 위 스케줄러 로직만 강화되면 요구사항을 자동 충족.
5. 구성/문서 반영
   - `config.default.yaml` 또는 전용 스케줄 설정 문서에 값 노출
   - `docs/youtube/` 가이드에 새 정책 설명

### Implementation Details
```python
# Pseudocode for slot selection inside schedule_manager
for days_ahead in range(max_days):  # e.g., 14
    d = start_date + timedelta(days=days_ahead)
    if daily_total(d) >= daily_max_total:
        continue
    for slot in time_slots:  # ["08:00", "14:00", "20:00"]
        dt = combine(d, slot)
        if count_scheduled(dt) < slot_capacity:
            return dt
```

## Alternative Approaches Considered
- 큐 처리기(백그라운드)로 자체 업로드 타이머 운용: YouTube `publishAt`을 쓰는 현재 아키텍처 방향과 상충될 수 있으므로 보류.
- 슬롯을 DB 테이블로 사전 생성 후 예약 시점에 consume: 단순하지만 운영/마이그레이션 복잡도 증가.

## Benefits
- 명확한 타임슬롯 정책 준수(08/14/20시, 슬롯당 2개).
- 대량 예약에도 자동 분산 → 운영 편의성/채널 품질 유지.
- 구성으로 시간대/용량을 손쉽게 변경 가능.

## Risks & Considerations
- 기존 타입별 한도와 총량 한도를 함께 운영할 때의 우선순위 정의 필요(총량 우선 권장).
- 타임존 이슈(서버/사용자): 모든 스케줄 시간을 채널/서버 표준 타임존으로 일관 처리.
- 과거 시각 스케줄 방지(당일 08:00 이전이라면 14:00부터 시작 등).

## Testing Strategy
- Unit
  - 하루에 1~6개: 각 슬롯으로 2개씩 채워지는지 검증.
  - 8개 예약: 6개는 D(오늘) 08/14/20 각 2개, 나머지 2개는 D+1 08부터.
  - 경계: 당일 08시가 이미 지났을 때 첫 가용 슬롯이 14:00인지.
  - 일일 총량 초과 시 다음날로 넘어가는지.
- Integration
  - `/api/upload/batch/schedule`로 2·6·8·15개 등 다양한 케이스 전송 후 DB 상태 검증.
  - UI가 표시하는 스케줄 결과(팝업/리스트)가 정책대로 분배되는지.

## Files Affected
- `langflix/youtube/schedule_manager.py`
  - `ScheduleConfig`(혹은 동등 구조) 확장 및 로직 업데이트
  - `get_next_available_slot`, `_get_available_times_for_date`, `check_daily_quota` 보강
- `langflix/youtube/web_ui.py`
  - 추가 파라미터가 필요 없도록 유지(스케줄러 내부 일반화)하되, 결과 표시 정렬/포맷 보완
- `docs/youtube/` (새 정책 설명 / 구성 키)
- `tests/integration/` `tests/unit/` (새 케이스 추가)

## Dependencies
- None

## References
- `tickets/done/TICKET-018-implement-scheduled-youtube-upload-processor.md` (publishAt 기반)

## Architect Review Questions
1. 타입별 한도와 일일 총량이 충돌 시 총량 우선으로 확정해도 될까요?
2. 타임슬롯 기본값(08/14/20)과 용량(2), 일일 최대(6)를 글로벌 기본으로 두고, 채널별 override가 필요할까요?
3. 탐색 범위(현재 7일)를 14일로 늘리는 것에 대한 의견?

## Success Criteria
- [ ] 8개 예약 시 D: 6개(08/14/20 각 2개), D+1: 2개(08부터)로 정확히 분배
- [ ] 슬롯당 최대 2개/일일 최대 6개가 DB 상 보장
- [ ] UI 배치 스케줄 호출만으로 정책 자동 반영
- [ ] 구성값으로 시간대/용량/총량 변경 가능
- [ ] 유닛/통합 테스트 추가 및 통과


