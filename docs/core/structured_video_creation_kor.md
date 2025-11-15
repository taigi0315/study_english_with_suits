# 구조화된 비디오 생성 - 새로운 아키텍처

**날짜**: 2025-01-XX  
**브랜치**: `feature/multiple-expressions-per-context`  
**상태**: 구현 완료

---

## 요약

이 문서는 기존의 long-form/short-form 구분을 대체하는 새로운 구조화된 비디오 생성 아키텍처를 설명합니다. 시스템은 이제 다음을 생성합니다:

1. **구조화된 비디오**: 각 expression마다 개별 비디오 (형식: `[context → expression repeat (2x) → slide (expression audio 2x)]`)
2. **결합된 구조화된 비디오**: 모든 구조화된 비디오를 하나로 결합
3. **Short-form 비디오**: 구조화된 비디오에서 생성된 세로형 9:16 비디오 (특별한 레이아웃)

---

## 1. 아키텍처 개요

### 1.1 주요 변경사항

**이전 (구 아키텍처)**:
- Long-form 비디오: 나란히 또는 순차적 레이아웃
- Short-form 비디오: 상하 레이아웃 (vstack)
- Expression 그룹핑: 컨텍스트당 여러 expression (ExpressionGroup)

**이후 (신 아키텍처)**:
- **구조화된 비디오**: 각 expression마다 자체 구조화된 비디오 생성 (1:1 매핑)
- **Long-form/short-form 구분 없음**: 모든 비디오가 동일한 구조를 따름
- **개별 expression 처리**: 그룹핑 없음, 각 expression을 독립적으로 처리
- **Short-form 비디오**: 구조화된 비디오에서 9:16 레이아웃으로 생성

### 1.2 비디오 출력 구조

```
output/Series/Episode/translations/ko/
├── structured_videos/                    # 새 디렉토리
│   ├── structured_video_{expression_1}.mkv
│   ├── structured_video_{expression_2}.mkv
│   ├── ...
│   └── combined_structured_video_{episode}.mkv  # 모두 결합
└── short_form_videos/                    # Short-form 비디오
    ├── short_form_{expression_1}.mkv
    ├── short_form_{expression_2}.mkv
    ├── ...
    └── short-form_{episode}_{batch_01}.mkv  # 배치 비디오
```

---

## 2. 구조화된 비디오 생성

### 2.1 메서드: `create_structured_video()`

**파일**: `langflix/core/video_editor.py`  
**메서드**: `create_structured_video()`  
**라인**: ~540-727

**목적**: 다음 패턴을 따르는 단일 expression에 대한 구조화된 비디오 생성:
```
[Context Video] → [Expression Video (2x)] → [Educational Slide (Expression Audio 2x)]
```

**프로세스**:
1. 컨텍스트 비디오에서 expression 클립 추출
2. Expression 클립을 2번 반복
3. 연결: context → expression (2x)
4. Expression 오디오(2x)로 교육 슬라이드 생성
5. 연결: context+expression → slide
6. 최종 오디오 게인 적용

**주요 특징**:
- **전환 효과 없음**: 구조화된 비디오는 전환 효과를 포함하지 않음
- **16:9 또는 원본 비율**: 원본 비디오 종횡비 유지
- **Expression 오디오**: TTS가 아닌 비디오의 원본 expression 오디오 사용
- **2x 반복**: Expression 비디오와 오디오 모두 2번 반복

### 2.2 결합된 구조화된 비디오

**파일**: `langflix/main.py`  
**메서드**: `_create_combined_structured_video()`  
**라인**: ~1022-1006

**목적**: 모든 구조화된 비디오를 하나의 결합된 비디오로 연결

**프로세스**:
1. 모든 구조화된 비디오 수집
2. 비디오 파일 존재 및 유효성 검증
3. 모든 비디오 경로가 포함된 concat 파일 생성
4. FFmpeg concat demuxer를 사용하여 연결
5. `structured_videos/combined_structured_video_{episode}.mkv`로 출력

---

## 3. Short-form 비디오 생성

### 3.1 메서드: `create_short_form_from_structured()`

**파일**: `langflix/core/video_editor.py`  
**메서드**: `create_short_form_from_structured()`  
**라인**: ~737-1037

**목적**: 구조화된 비디오(16:9)를 특별한 레이아웃의 short-form 비디오(9:16)로 변환

**레이아웃 사양**:
- **대상 해상도**: 1080x1920 (9:16 세로형)
- **구조화된 비디오**: 
  - 화면 중앙에 배치
  - 높이: 960px (전체 높이의 절반)
  - 좌우 잘림 (스트레치 없음)
  - 원본 종횡비 유지
- **Expression 텍스트**: 
  - 상단에 표시 (구조화된 비디오 영역 외부)
  - 위치: 상단에서 y=50px
  - 색상: 노란색, 굵게, 중앙 정렬
  - 배경: 검은 화면
- **자막**: 
  - 하단에 표시 (구조화된 비디오 영역 외부)
  - 위치: MarginV=100 (하단에서 100px)
  - 색상: 흰색
  - 배경: 검은 화면

### 3.2 Short-form 배치

**파일**: `langflix/main.py`  
**메서드**: `_create_batched_short_videos_with_max_duration()`  
**라인**: ~957-1020

**목적**: 최대 지속 시간 제한으로 short-form 비디오 배치

**설정**:
- **기본 max_duration**: 180초 (설정 가능)
- **위치**: `langflix/config/default.yaml` → `short_video.max_duration`
- **UI 설정**: 사용자가 `short_form_max_duration` 파라미터로 설정 가능

**프로세스**:
1. Short-form 비디오를 순회
2. 비디오가 max_duration을 초과하는지 확인 → 초과 시 드롭
3. max_duration에 도달할 때까지 비디오를 배치에 추가
4. 제한에 도달하면 배치 비디오 생성
5. 다음 배치 계속

---

## 4. Expression 처리 변경사항

### 4.1 ExpressionGroup 제거

**이전**: Expression이 `ExpressionGroup`을 사용하여 컨텍스트별로 그룹화됨
- 여러 expression이 동일한 컨텍스트를 공유할 수 있음
- 그룹화된 expression이 함께 처리됨

**이후**: 각 expression이 개별적으로 처리됨
- **1 context → 1 expression** 규칙 (각 expression이 자체 컨텍스트를 가짐)
- 그룹핑 로직 없음
- 각 expression이 자체 구조화된 비디오를 가짐

### 4.2 컨텍스트 비디오 생성

**파일**: `langflix/main.py`  
**메서드**: `_process_expressions()`  
**라인**: ~650-724

**프로세스**:
1. 각 expression을 개별적으로:
   - 컨텍스트 시간 범위 추출
   - 컨텍스트 비디오 클립 생성
   - `temp_expression_{idx}_{name}.mkv`로 저장
2. 컨텍스트 그룹핑 또는 병합 없음
3. 각 expression이 독립적인 컨텍스트 비디오를 가짐

---

## 5. 설정

### 5.1 Short-form 최대 지속 시간

**위치**: `langflix/config/default.yaml`

```yaml
short_video:
  enabled: true
  resolution: "1080x1920"
  target_duration: 120
  duration_variance: 10
  max_duration: 180  # Short-form 배치의 최대 지속 시간 (초)
```

**접근**: `langflix/settings.py` → `get_short_video_max_duration()`

### 5.2 API 파라미터

**엔드포인트**: `POST /api/v1/jobs`

**새 파라미터**:
- `short_form_max_duration` (float, 기본값: 180.0)
  - Short-form 비디오 배치의 최대 지속 시간
  - 이 지속 시간을 초과하는 비디오는 드롭됨

---

## 6. 주요 기술 세부사항

### 6.1 비디오 스케일링 및 크롭

**Short-form 비디오 처리**:
1. 스케일 팩터 계산: `scale_factor = 960 / original_height`
2. 높이로 스케일: `scaled_width = original_width * scale_factor`
3. `scaled_width > 1080`인 경우: 중앙에서 크롭
   - `crop_x = (scaled_width - 1080) // 2`
   - 크롭: 중앙에서 `1080 x 960`

**스트레치 없음**: 비디오 종횡비 항상 유지

### 6.2 자막 위치

**Expression 텍스트 (상단)**:
- FFmpeg drawtext 필터
- 위치: `x='(w-text_w)/2'` (중앙), `y=50` (상단에서 50px)
- 스타일: 노란색, 굵게, 48px 폰트

**자막 (하단)**:
- ASS 자막 오버레이
- 스타일: `Alignment=2` (하단 중앙), `MarginV=100` (하단에서 100px)
- 색상: 흰색, 32px 폰트

---

**마지막 업데이트**: 2025-01-XX  
**유지보수**: 개발팀


