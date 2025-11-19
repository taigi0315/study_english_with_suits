# 슬라이드 모듈

## 개요

`langflix/slides/` 모듈은 LangFlix를 위한 교육용 슬라이드 생성 기능을 제공합니다. 표현식 정보, 번역, 유사 표현식 및 교육 콘텐츠가 포함된 텍스트 오버레이가 있는 비디오 슬라이드를 생성합니다.

**목적:**
- 표현식 콘텐츠가 있는 교육용 슬라이드 생성
- 오디오가 없는 또는 오디오가 있는 슬라이드 비디오 생성
- 적절한 스타일링으로 텍스트 오버레이 적용
- 여러 슬라이드 템플릿 유형 지원
- 교육 콘텐츠를 위한 비디오 파이프라인과 통합

**사용 시기:**
- 표현식에 대한 교육용 슬라이드를 생성할 때
- 텍스트 오버레이가 있는 슬라이드 비디오를 생성할 때
- 슬라이드 템플릿 및 레이아웃을 사용자 정의할 때

## 파일 목록

### `generator.py`
FFmpeg를 사용한 메인 슬라이드 생성 모듈입니다.

**주요 함수:**
- `create_silent_slide()` - 오디오 없는 슬라이드 비디오 생성
- `_get_background_input()` - 배경 이미지 또는 색상 가져오기
- `_clean_for_draw()` - drawtext 필터용 텍스트 정리
- `_esc_draw()` - drawtext용 특수 문자 이스케이프
- `_font_size()` - 설정에서 폰트 크기 가져오기

### `slide_templates.py`
다양한 슬라이드 유형에 대한 템플릿 관리입니다.

**슬라이드 유형:**
- `EXPRESSION` - 메인 표현식 슬라이드
- `USAGE` - 사용 예제 슬라이드
- `CULTURAL` - 문화적 맥락 슬라이드
- `GRAMMAR` - 문법 설명 슬라이드
- `PRONUNCIATION` - 발음 가이드 슬라이드
- `SIMILAR` - 유사 표현식 슬라이드

## 주요 구성 요소

### SlideText 데이터클래스

슬라이드 텍스트 콘텐츠를 위한 데이터 구조입니다.

### 무음 슬라이드 생성

텍스트 오버레이가 있는 무음 슬라이드 비디오를 생성합니다.

**기능:**
- 배경 이미지 또는 단색 사용
- 여러 텍스트 오버레이 적용
- 설정에서 구성 가능한 폰트 크기
- FFmpeg를 위한 적절한 텍스트 정리 및 이스케이프

## 구현 세부사항

### 텍스트 처리

텍스트는 FFmpeg drawtext 필터를 위해 정리되고 이스케이프됩니다.

### 폰트 구성

폰트 크기는 설정에서 검색됩니다.

## 의존성

**외부 라이브러리:**
- `ffmpeg-python` - 비디오 처리 및 텍스트 오버레이
- `Pillow` (PIL) - 이미지 렌더링

**필수 에셋:**
- `assets/education_slide_background.png` (선택사항)
- 폰트 파일

## 일반적인 작업

### 간단한 슬라이드 생성

```python
from langflix.slides.generator import create_silent_slide, SlideText
from pathlib import Path

text = SlideText(
    dialogue="I need to break the ice with the new client.",
    expression="break the ice",
    dialogue_trans="새 고객과 분위기를 깨야 해요.",
    expression_trans="분위기를 깨다"
)

output = create_silent_slide(
    text=text,
    duration=5.0,
    output_path=Path("slide.mkv")
)
```

## 주의사항 및 참고사항

### 중요 고려사항

1. **텍스트 길이:**
   - 텍스트는 필드당 100자로 제한됩니다
   - 더 긴 텍스트는 잘립니다
   - 특수 문자는 FFmpeg 호환성을 위해 제거됩니다

2. **배경 이미지:**
   - JPG보다 PNG를 선호합니다
   - 이미지를 찾을 수 없으면 단색으로 폴백합니다
   - 기본 색상: 어두운 청회색 (0x1a1a2e)

3. **폰트 파일:**
   - 설정에서 폰트 파일 경로
   - 찾을 수 없으면 시스템 기본값으로 폴백
   - FFmpeg가 접근할 수 있어야 합니다

## 관련 문서

- [Core Module](../core/README_eng.md) - 표현식 처리 및 비디오 편집
- [Config Module](../config/README_eng.md) - 폰트 및 스타일링 설정
- [Media Module](../media/README_eng.md) - FFmpeg 유틸리티

