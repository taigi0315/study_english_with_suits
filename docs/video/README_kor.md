# 비디오 모듈

## 개요

`langflix/video/` 모듈은 LangFlix를 위한 비디오 품질 향상 기능을 제공합니다. 지능형 비디오 업스케일링, 프레임 보간, 색상 보정, 안정화 및 품질 향상 기능을 제공합니다.

**목적:**
- 교육 콘텐츠를 위한 비디오 품질 향상
- 비디오를 대상 해상도로 업스케일링
- 흔들리는 비디오 영상 안정화
- 색상, 대비 및 선명도 개선
- 노이즈 및 아티팩트 감소

**사용 시기:**
- 소스 비디오 품질을 개선해야 할 때
- 비디오를 더 높은 해상도로 업스케일링할 때
- 흔들리는 영상을 안정화할 때
- 색상을 향상하거나 노이즈를 줄일 때

## 파일 목록

### `video_enhancer.py`
비디오 품질 향상 작업을 위한 메인 모듈입니다.

**주요 클래스:**
- `VideoEnhancer` - 메인 향상 클래스
- `VideoQualityMetrics` - 비디오 품질 측정 데이터클래스
- `VideoEnhancementConfig` - 구성 데이터클래스

## 주요 구성 요소

### VideoEnhancer 클래스

고급 비디오 품질 향상 시스템입니다.

### 향상 수준

향상기는 세 가지 품질 수준을 지원합니다:

**낮은 향상:**
- 기본 선명화
- 표준 인코딩
- 빠른 처리

**중간 향상:**
- 선명화 + 색상 향상
- 선택적 안정화
- 더 나은 품질

**높은 향상:**
- 선명화 + 색상 향상 + 노이즈 감소
- 선택적 안정화 및 프레임 보간
- 최고 품질

## 구현 세부사항

### 비디오 분석

향상기는 FFprobe를 사용하여 비디오 품질을 분석합니다.

### 향상 필터

다양한 FFmpeg 필터를 사용합니다:
- 선명화
- 색상 향상
- 노이즈 감소
- 안정화
- 프레임 보간

## 의존성

**필수 FFmpeg 필터:**
- `unsharp` - 선명화
- `eq` - 색상 보정
- `hqdn3d` - 노이즈 감소
- `vidstabdetect` / `vidstabtransform` - 안정화
- `minterpolate` - 프레임 보간
- `scale` - 해상도 스케일링

## 일반적인 작업

### 기본 비디오 향상

```python
from langflix.video.video_enhancer import VideoEnhancer

enhancer = VideoEnhancer()
metrics = enhancer.enhance_video(
    input_path="input.mkv",
    output_path="enhanced.mkv",
    enhancement_level="medium"
)
```

### 비디오 업스케일링

```python
enhancer = VideoEnhancer()
output = enhancer.upscale_video(
    input_path="720p.mkv",
    output_path="1080p.mkv",
    target_resolution=(1920, 1080),
    upscale_quality="high"
)
```

## 주의사항 및 참고사항

### 중요 고려사항

1. **처리 시간:**
   - 높은 향상 수준은 상당히 더 오래 걸립니다
   - 안정화는 두 번의 패스가 필요합니다 (감지 + 변환)
   - 프레임 보간은 계산 집약적입니다

2. **품질 vs 속도:**
   - 낮음: 빠름, 기본 품질
   - 중간: 균형잡힌 품질과 속도
   - 높음: 최고 품질, 가장 느린 처리

3. **안정화:**
   - 두 번의 패스 처리가 필요합니다
   - 현재 디렉토리에 `transforms.trf` 파일 생성
   - 비디오 가장자리를 약간 자를 수 있습니다

## 관련 문서

- [Media Module](../media/README_eng.md) - FFmpeg 유틸리티 및 미디어 처리
- [Core Module](../core/README_eng.md) - 비디오 편집 및 파이프라인 로직

