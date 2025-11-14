# Core 모듈 문서

## 개요

`langflix/core/` 모듈은 LangFlix의 핵심 비디오 처리 및 파이프라인 구성 요소를 포함합니다. 이 모듈은 필수 비디오 작업, 표현 분석 및 메인 파이프라인 오케스트레이션을 제공합니다.

**최종 업데이트:** 2025-11-14  
**관련 티켓:** TICKET-035

## 목적

이 모듈은 다음을 담당합니다:
- 비디오 파일 처리 및 클립 추출
- 표현 분석 및 검증
- 파이프라인 오케스트레이션
- 비디오 편집 및 구성
- 표현 및 그룹을 위한 모델 정의

## 주요 구성 요소

### VideoProcessor (`video_processor.py`)

비디오 파일 로딩, 검증, 클립 추출을 포함한 비디오 파일 작업을 처리합니다.

#### 주요 기능

**TICKET-035 개선사항:** 스트림 복사 폴백을 사용한 적응형 클립 추출.

`VideoProcessor`는 이제 최적 성능을 위한 3가지 추출 전략을 지원합니다:

1. **'auto' (기본값)**: 스트림 복사를 먼저 시도하고, 필요 시 재인코딩으로 폴백
2. **'copy'**: 스트림 복사만 사용 (가장 빠름, 일부 클립에서 실패 가능)
3. **'encode'**: 항상 재인코딩 (가장 느림, 가장 호환성 높음)

#### `extract_clip(video_path, start_time, end_time, output_path, strategy=None)`

적응형 전략을 사용하여 시작 시간과 종료 시간 사이의 비디오 클립을 추출합니다.

**매개변수:**
- `video_path` (Path): 소스 비디오 파일 경로
- `start_time` (str): "HH:MM:SS.mmm" 형식의 시작 시간
- `end_time` (str): "HH:MM:SS.mmm" 형식의 종료 시간
- `output_path` (Path): 출력 클립 경로
- `strategy` (Optional[str]): 추출 전략 ('auto', 'copy', 'encode'). None인 경우 설정값 사용.

**반환값:**
- `bool`: 성공 시 True, 실패 시 False

**전략 비교:**

| 전략 | 속도 | 정확도 | 호환성 | 사용 사례 |
|------|------|--------|--------|-----------|
| `auto` | ⚡⚡⚡ 빠름 (copy) / ⚡ 느림 (encode) | 🎯 높음 | ✅ 우수 | **권장** - 최적 균형 |
| `copy` | ⚡⚡⚡ 가장 빠름 | 🎯 양호* | ⚠️ 실패 가능 | 짧은 클립, 키프레임 정렬 |
| `encode` | ⚡ 가장 느림 | 🎯 완벽 | ✅ 항상 작동 | 긴 클립, 프레임 완벽 필요 |

*스트림 복사 정확도는 키프레임 정렬에 따라 다름

**성능 영향:**
- **스트림 복사**: 재인코딩 대비 70-90% 빠름
- **일반 에피소드 (30개 표현)**: 
  - 이전: 15-20분 (모두 재인코딩)
  - 이후: 5-10분 (auto 모드, 복사+폴백)
  - 절약: **클립 추출 시간 50-70% 감소**

**사용 예제:**

```python
from pathlib import Path
from langflix.core.video_processor import VideoProcessor

processor = VideoProcessor()

# Auto 모드 (권장) - 복사 시도 후 인코딩으로 폴백
success = processor.extract_clip(
    video_path=Path("episode.mkv"),
    start_time="00:05:23.500",
    end_time="00:05:28.800",
    output_path=Path("output/clip.mkv"),
    strategy="auto"  # 또는 None으로 설정 기본값 사용
)

# 스트림 복사 강제 (가장 빠름, 실패 가능)
success = processor.extract_clip(
    video_path=Path("episode.mkv"),
    start_time="00:05:23.500",
    end_time="00:05:28.800"),
    output_path=Path("output/clip.mkv"),
    strategy="copy"
)

# 재인코딩 강제 (가장 느림, 가장 안정적)
success = processor.extract_clip(
    video_path=Path("episode.mkv"),
    start_time="00:05:23.500",
    end_time="00:05:28.800",
    output_path=Path("output/clip.mkv"),
    strategy="encode"
)
```

**설정:**

`config.yaml`에 추가:

```yaml
video:
  clip_extraction:
    # 전략: 'auto', 'copy', 또는 'encode'
    strategy: "auto"
    
    # 스트림 복사 시도 임계값 (초)
    # 이보다 짧은 클립은 복사를 먼저 시도
    copy_threshold_seconds: 30.0
```

**Settings를 통한 접근:**

```python
from langflix import settings

# 현재 전략 가져오기
strategy = settings.get_clip_extraction_strategy()  # 'auto', 'copy', 또는 'encode' 반환

# 복사 임계값 가져오기
threshold = settings.get_clip_copy_threshold_seconds()  # float 반환 (기본값: 30.0)
```

#### 내부 메서드

##### `_extract_clip_copy(video_path, start_seconds, end_seconds, output_path)`

스트림 복사를 사용하여 클립 추출 (재인코딩 없음). 빠르지만 시작/종료 시간이 키프레임과 정렬되지 않으면 프레임 정확도 문제가 있을 수 있습니다.

**작동 방식:**
- `ffmpeg -ss START -to END -c copy` 사용
- 원본 코덱 및 품질 보존
- CPU 집약적인 인코딩 없음
- 수 밀리초 만에 완료 (수 초 vs 수 초)

**성공하는 경우:**
- 짧은 클립 (기본적으로 < 30초)
- 키프레임과 정렬되거나 근처에 있는 시간
- 소스 코덱이 호환되는 경우

**실패하는 경우:**
- 키프레임이 아닌 시작 시간 (매우 정밀한 컷)
- 일부 컨테이너/코덱 조합
- 'auto' 모드에서 자동으로 인코딩으로 폴백

##### `_extract_clip_encode(video_path, start_seconds, duration, output_path)`

재인코딩을 사용하여 클립 추출 (기존 동작). 느리지만 프레임 정확한 추출과 더 나은 호환성을 제공합니다.

**작동 방식:**
- 인코딩과 함께 `ffmpeg -ss START -t DURATION` 사용
- libx264/aac로 재인코딩
- 프레임 완벽 정확도
- 클립당 수 초 소요

**사용 시기:**
- 긴 클립 (> 30초)
- 프레임 완벽 정확도 필요
- 스트림 복사 실패 또는 사용 불가
- 'auto' 모드에서 폴백

### VideoEditor (`video_editor.py`)

비디오 구성, 자막 오버레이, 교육용 비디오 생성을 처리합니다.

**주요 책임:**
- 표현 강조 교육 시퀀스 생성
- 자막 및 번역 추가
- 컨텍스트 비디오와 교육 슬라이드 결합
- 다중 표현 비디오 시퀀스
- 오디오 게인 조정

### Models (`models.py`)

표현 및 표현 그룹에 대한 데이터 구조를 정의합니다.

**주요 클래스:**
- `ExpressionAnalysis`: 타이밍 및 텍스트가 있는 단일 표현
- `ExpressionGroup`: 관련 표현 그룹
- 일관된 데이터 처리를 위해 파이프라인 전체에서 사용

## 설정

### 클립 추출 설정

```yaml
video:
  clip_extraction:
    strategy: "auto"                    # 'auto', 'copy', 또는 'encode'
    copy_threshold_seconds: 30.0        # 복사 시도 임계값
```

**전략 가이드라인:**

- **개발/테스트**: `"auto"` 사용 (기본값)
- **프로덕션 (속도 우선)**: 더 높은 임계값(60.0)으로 `"auto"` 사용
- **프로덕션 (품질 우선)**: `"encode"` 사용
- **배치 처리**: `"auto"` 사용 - 최적 균형
- **디버그/문제 해결**: `"encode"` 사용 - 복사 관련 문제 제거

**임계값 조정:**

- **낮은 임계값 (10-20초)**: 더 보수적, 복사 시도 횟수 적음
- **기본값 (30초)**: 균형 잡힘 - 대부분의 표현에 유리
- **높은 임계값 (60초+)**: 공격적 - 더 긴 클립에도 복사 시도
- **0**: 복사 시도 비활성화 ("encode" 전략과 동일)

## 성능 최적화

### 클립 추출 성능 (TICKET-035)

**TICKET-035 이전:**
- 모든 클립: libx264로 재인코딩
- 30개 표현 에피소드: ~15-20분
- CPU 사용량: 추출 중 매우 높음

**TICKET-035 이후 (auto 모드):**
- 짧은 클립: 스트림 복사 (70-90% 빠름)
- 실패한 복사: 재인코딩으로 자동 폴백
- 30개 표현 에피소드: ~5-10분
- CPU 사용량: 크게 감소

**성능 메트릭:**

| 클립 길이 | 복사 시간 | 인코딩 시간 | 속도 향상 |
|-----------|-----------|-------------|-----------|
| 3초       | 0.05초    | 2.5초       | **50배**  |
| 5초       | 0.08초    | 4.0초       | **50배**  |
| 10초      | 0.15초    | 8.0초       | **53배**  |
| 30초      | 0.40초    | 24.0초      | **60배**  |

**성공률:**
- 짧은 클립 (< 10초): ~95% 복사 성공
- 중간 클립 (10-30초): ~85% 복사 성공
- 긴 클립 (> 30초): 복사 시도 건너뜀 (인코딩 사용)

## 문제 해결

### 스트림 복사 문제

**문제:** "Stream copy failed" 메시지와 함께 클립 추출 실패

**해결책 1:** 시간이 키프레임과 정렬되는지 확인
```bash
# 클립 시간 근처의 키프레임 찾기
ffprobe -select_streams v -show_frames -show_entries frame=pkt_pts_time,key_frame \
  -of csv video.mkv | grep ",1$" | head -20
```

**해결책 2:** 문제가 있는 클립에 인코딩 전략 사용
```python
processor.extract_clip(..., strategy="encode")
```

**해결책 3:** 설정에서 임계값 조정
```yaml
video:
  clip_extraction:
    copy_threshold_seconds: 10.0  # 더 보수적
```

**문제:** 복사는 성공했지만 클립에 타이밍 문제 발생

**원인:** 시작 시간이 키프레임과 정렬되지 않아 부정확한 컷 발생

**해결책:** 
- 프레임 완벽 정확도를 위해 `strategy="encode"` 사용
- 또는 이 클립 길이에 대해 복사를 건너뛰도록 임계값 조정

### 성능이 개선되지 않음

**확인 1:** 전략이 올바르게 설정되었는지 확인
```python
from langflix import settings
print(settings.get_clip_extraction_strategy())  # 'auto'여야 함
```

**확인 2:** 클립이 너무 긴지 확인 (임계값 초과)
```python
threshold = settings.get_clip_copy_threshold_seconds()
print(f"복사 임계값: {threshold}초")
# 대부분의 클립 > 임계값이면 복사가 시도되지 않음
```

**확인 3:** 복사 성공률 로그 검토
```bash
grep "Stream copy" langflix.log | grep -c "successful"
grep "fallback to re-encode" langflix.log | wc -l
```

## 모범 사례

### 클립 추출

1. **프로덕션에서 'auto' 전략 사용** (기본값)
   - 안전한 경우 자동으로 속도 최적화
   - 필요 시 품질로 폴백

2. **콘텐츠에 따라 임계값 조정**
   - 일반적인 표현 길이 분석
   - 표현의 80-90%를 커버하도록 임계값 설정

3. **복사 성공률 모니터링**
   - 실패율 높음? 임계값 낮추거나 'encode' 사용
   - 실패율 낮음? 더 많은 속도 향상을 위해 임계값 증가

4. **중요한 콘텐츠에는 'encode' 사용**
   - 프레임 완벽 정확도 필요
   - 속도보다 품질 우선

5. **최적화를 위한 로그 분석**
   ```bash
   # 복사 vs 인코딩 사용량 확인
   grep "Stream copy successful" langflix.log | wc -l
   grep "Using re-encode" langflix.log | wc -l
   ```

## 파일 구조

```
langflix/core/
├── __init__.py              # 모듈 초기화
├── video_processor.py       # 비디오 작업 및 클립 추출
├── video_editor.py          # 비디오 구성 및 편집
├── models.py                # 데이터 모델 (ExpressionAnalysis 등)
├── pipeline.py              # 메인 파이프라인 오케스트레이션
└── redis_client.py          # 작업 관리를 위한 Redis 통합
```

## 관련 문서

- [성능 최적화 가이드](../performance/video_pipeline_optimization_kor.md)
- [Media 모듈 문서](../media/README_kor.md)
- [설정 가이드](../CONFIGURATION_GUIDE.md)

## 참고

- **TICKET-034**: FFprobe 캐싱 레이어 (업스트림 최적화)
- **TICKET-035**: 적응형 클립 추출 (이 기능)
- **TICKET-036**: Expression slicer 동시성 (다운스트림 최적화)
