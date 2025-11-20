# 다중 언어 비디오 생성 아키텍처

**최종 업데이트:** 2025-01-30  
**상태:** ✅ 구현 완료

## 개요

이 문서는 여러 언어로 동시에 비디오를 생성하는 아키텍처와 구현 계획을 설명합니다. 핵심 혁신은 비용이 많이 드는 작업(LLM 분석, 비디오 슬라이싱)을 모든 대상 언어에서 재사용하고, 텍스트 요소만 번역하는 것입니다.

## 문제 진술

현재 여러 언어(예: 한국어, 일본어, 중국어)로 비디오를 생성하려면 파이프라인을 여러 번 실행해야 합니다:
- 각 실행마다 비용이 많이 드는 LLM 분석 수행
- 각 실행마다 비디오 슬라이스 추출
- 총 시간 = N × 단일 언어 시간

**목표**: N개 언어에 대한 비디오를 단일 언어와 거의 동일한 시간에 생성 (번역 시간 제외).

## 아키텍처 원칙

### 1. 언어 독립적 작업 재사용

**재사용할 항목:**
- **LLM 표현 분석**: 표현 추출, 타이밍, 컨텍스트 경계, 장면 분석
- **비디오 슬라이스**: 컨텍스트 클립, 표현 클립 (소스 비디오의 동일한 시간 슬라이스)
- **파이프라인 구조**: 표현 처리 로직, 비디오 조립 로직

**번역할 항목:**
- 대화 번역 (`ExpressionAnalysis.translation[]`)
- 표현 번역 (`expression_translation`, `expression_dialogue_translation`)
- 캐치 키워드 (`catchy_keywords[]`)
- 유사 표현 (`similar_expressions[]`)
- 교육용 슬라이드 내용 (텍스트 오버레이)
- 자막 파일 (비디오 오버레이용 SRT 파일)

### 2. 관심사 분리

- **분석 단계**: 표현 추출 (언어 독립적)
- **번역 단계**: 텍스트 요소를 대상 언어로 번역
- **생성 단계**: 번역된 내용을 사용하여 각 언어에 대한 비디오 생성

## 구현 아키텍처

### 1단계: 번역 서비스

**새 파일**: `langflix/core/translator.py`

**목적**: 언어 독립적 데이터를 보존하면서 `ExpressionAnalysis` 객체를 여러 대상 언어로 번역합니다.

**주요 메서드**:
```python
def translate_expression_to_languages(
    expression: ExpressionAnalysis,
    target_languages: List[str]
) -> Dict[str, ExpressionAnalysis]:
    """
    표현 텍스트 요소를 여러 언어로 번역합니다.
    
    재사용 (원본에서 복사):
    - expression (영어 텍스트)
    - context_start_time, context_end_time
    - expression_start_time, expression_end_time
    - scene_type, difficulty, category
    - educational_value, usage_notes
    
    번역 (언어별 새 값):
    - dialogues → 번역된 대화
    - translation → 번역된 대화 번역
    - expression_translation → 번역된 표현
    - expression_dialogue_translation → 번역된 표현 대화
    - catchy_keywords → 번역된 키워드
    - similar_expressions → 번역된 유사 표현
    """
```

**번역 프롬프트 설계** (`langflix/templates/translation_prompt.txt`):

프롬프트는 **직역(직역)**보다 **의역(의역)**을 강조합니다:

```
다음 영어 학습 콘텐츠를 {target_language}로 번역하세요.
의미와 감정을 포착하는 자연스러운, 맥락적 번역(의역)을 제공하되,
단어별 직역(직역)은 피하세요.

컨텍스트:
- 표현: {expression}
- 전체 대화: {expression_dialogue}
- 장면 컨텍스트: {dialogues}
- 장면 유형: {scene_type}
- 캐치 키워드: {catchy_keywords}
- 유사 표현: {similar_expressions}

번역:
1. 모든 대화 라인 (동일한 개수 유지, 타이밍 보존)
2. 표현 번역 (자연스럽고 맥락적)
3. 표현 대화 번역 (자연스럽고 맥락적)
4. 캐치 키워드 (각 3-6단어, 대상 언어로 자연스럽게)
5. 유사 표현 (대상 언어로 자연스러운 대안)

중요:
- 장면의 감정적 톤과 컨텍스트 유지
- 원어민이 사용할 자연스러운 표현 사용
- 교육적 가치와 기억에 남는 특성 보존
```

### 2단계: 파이프라인 수정

**파일**: `langflix/main.py::LangFlixPipeline`

#### `__init__` 변경:
```python
def __init__(
    self,
    subtitle_file: str,
    video_dir: str,
    output_dir: str = "output",
    language_code: str = "ko",
    target_languages: Optional[List[str]] = None,  # 신규
    ...
):
    self.language_code = language_code
    self.target_languages = target_languages or [language_code]  # 기본값: 단일 언어
```

#### `run()` 변경:
```python
def run(
    self,
    max_expressions: int = None,
    target_languages: Optional[List[str]] = None,  # 신규
    ...
):
    # 제공된 경우 덮어쓰기
    if target_languages:
        self.target_languages = target_languages
```

#### 수정된 `_analyze_expressions()`:
- **현재**: 대상 언어로 번역을 포함한 LLM 분석 실행
- **신규**: LLM 분석을 한 번 실행 (프롬프트에 첫 번째 언어 사용, 또는 영어)
- 기본 `ExpressionAnalysis` 객체 저장 (원본 언어 번역 포함)
- **재사용**: 모든 대상 언어에 대해 이 객체 사용

#### 신규 메서드: `_translate_expressions_to_languages()`
```python
def _translate_expressions_to_languages(
    self,
    expressions: List[ExpressionAnalysis],
    target_languages: List[str]
) -> Dict[str, List[ExpressionAnalysis]]:
    """
    표현을 모든 대상 언어로 번역합니다.
    
    반환:
        language_code를 번역된 ExpressionAnalysis 객체 리스트에 매핑하는 Dict
    """
    from langflix.core.translator import translate_expression_to_languages
    
    translated_expressions = {}
    
    for lang in target_languages:
        if lang == self.language_code:
            # 원본 사용 (분석 중 이미 번역됨)
            translated_expressions[lang] = expressions
        else:
            # 대상 언어로 번역
            lang_expressions = []
            for expr in expressions:
                translated = translate_expression_to_languages(expr, [lang])
                lang_expressions.append(translated[lang])
            translated_expressions[lang] = lang_expressions
    
    return translated_expressions
```

#### 수정된 `_process_expressions()`:
- **현재**: 단일 언어에 대한 자막 파일 생성
- **신규**: 
  - 표현당 비디오 슬라이스를 한 번 추출 (언어 독립적)
  - 임시 위치에 슬라이스 저장
  - 각 대상 언어에 대한 자막 파일 생성
  - **재사용**: 동일한 비디오 슬라이스, 다른 자막 파일

#### 수정된 `_create_educational_videos()`:
- **현재**: 단일 언어에 대한 비디오 생성
- **신규**:
  - 대상 언어 반복
  - 각 언어에 대해:
    - 번역된 `ExpressionAnalysis` 객체 사용
    - 사전 추출된 비디오 슬라이스 재사용
    - 언어별 자막 파일 적용
    - 언어별 출력 디렉토리에 비디오 생성

### 3단계: 자막 생성

**파일**: `langflix/core/subtitle_processor.py`

**신규 메서드**:
```python
def create_subtitle_file_for_language(
    self,
    expression: ExpressionAnalysis,
    language_code: str,
    output_path: Path
) -> Path:
    """
    특정 언어에 대한 번역된 대화가 포함된 SRT 파일을 생성합니다.
    
    재사용: 기본 표현의 타이밍 정보
    번역: ExpressionAnalysis의 대화 텍스트 및 번역
    """
```

**현재 위치**: `_process_expressions()`의 자막 파일 생성 (라인 ~649-700)
- 이 로직을 `SubtitleProcessor` 메서드로 추출
- 언어별 `ExpressionAnalysis` 객체 수락

### 4단계: 비디오 에디터 수정

**파일**: `langflix/core/video_editor.py::create_long_form_video()`

#### 변경사항:
1. **비디오 슬라이스 재사용**:
   - 선택적 `pre_extracted_context_clip: Optional[Path]` 매개변수 수락
   - 제공된 경우 재사용, 그렇지 않으면 추출 (하위 호환성)

2. **언어별 자막**:
   - `language_code: str` 매개변수 수락
   - 언어에 적절한 자막 파일 로드
   - 동일한 비디오 슬라이스에 적용

3. **언어별 슬라이드 내용**:
   - 슬라이드 생성에 번역된 `ExpressionAnalysis` 사용
   - 메서드: `_create_educational_slide()`는 이미 표현 데이터 사용

### 5단계: 출력 구조

**파일**: `langflix/services/output_manager.py`

**현재 구조**: `output/Series/Episode/{language_code}/expressions/`, `shorts/`, `long/`

**다중 언어 구조**: 각 대상 언어에 대한 디렉토리 생성
```
output/
└── Series/
    └── Episode/
        ├── ko/
        │   ├── expressions/
        │   ├── shorts/
        │   └── long/
        ├── ja/
        │   ├── expressions/
        │   ├── shorts/
        │   └── long/
        └── zh/
            ├── expressions/
            ├── shorts/
            └── long/
```

**수정**: `create_language_structure()`를 여러 언어 처리하도록 수정
- 각 대상 언어에 대해 호출
- 처리 전에 모든 언어에 대한 구조 생성

### 6단계: API 통합

**파일**: `langflix/api/routes/jobs.py`, `langflix/services/video_pipeline_service.py`

#### 변경사항:
1. **API 엔드포인트에 `target_languages` 매개변수 추가**
   - 기본값: 하위 호환성을 위해 `[language_code]`
   - 수락: 언어 코드 리스트 `['ko', 'ja', 'zh']` 또는 쉼표로 구분된 문자열

2. **수정**: `VideoPipelineService.process_video()`
   - `target_languages: List[str]` 매개변수 수락
   - `LangFlixPipeline`에 전달

3. **진행 상황 업데이트**:
   - 처리 중인 각 언어에 대한 진행 상황 업데이트
   - 예: "ko에 대한 비디오 생성 중 (1/3)", "ja에 대한 비디오 생성 중 (2/3)"

## 데이터 흐름

### 현재 흐름 (단일 언어):
```
자막 파싱 → 청크 → LLM 분석 (번역 포함) → 
표현 처리 → 비디오 생성
```

### 신규 흐름 (다중 언어):
```
자막 파싱 → 청크 → LLM 분석 (한 번, 언어 독립적) →
언어로 번역 → 비디오 슬라이스 추출 (한 번) →
각 언어에 대해:
  - 자막 파일 생성
  - 비디오 생성 (슬라이스 재사용, 언어 자막 적용)
```

## 성능 이점

### 시간 절약:
- **LLM 분석**: Nx 대신 1x (N = 언어 수)
- **비디오 추출**: 표현당 Nx 대신 1x
- **총 시간**: N개 언어에 대해 약 1/N (번역 시간 제외)

### 비용 절약:
- **LLM API 호출**: Nx 대신 1x
- **처리 리소스**: 언어 간 공유

### 예시:
- **이전**: 3개 언어 × 10분 = 30분
- **이후**: 1회 분석 (10분) + 3회 번역 (2분) + 3회 비디오 생성 (6분) = 약 18분
- **절약**: 약 40% 시간 감소

## 구현 단계

### 1단계: 번역 서비스 생성
- `langflix/core/translator.py` 생성
- 번역 프롬프트 템플릿 `langflix/templates/translation_prompt.txt` 생성
- `translate_expression_to_languages()` 메서드 구현
- 단일 표현, 여러 언어로 테스트

### 2단계: 다중 언어를 위한 파이프라인 수정
- `LangFlixPipeline`에 `target_languages` 매개변수 추가
- `_analyze_expressions()`를 한 번 실행하도록 수정
- `_translate_expressions_to_languages()` 구현
- 기존 표현으로 번역 테스트

### 3단계: 비디오 슬라이스 재사용
- `_process_expressions()`를 슬라이스를 한 번 추출하도록 수정
- 임시 위치에 슬라이스 저장
- `create_long_form_video()`를 사전 추출된 슬라이스를 수락하도록 수정
- 비디오 슬라이스 재사용 테스트

### 4단계: 언어별 자막 생성
- 자막 생성 로직을 `SubtitleProcessor`로 추출
- `create_subtitle_file_for_language()` 구현
- 여러 언어에 대한 자막 생성 테스트

### 5단계: 언어별 비디오 생성
- `_create_educational_videos()`를 언어 반복하도록 수정
- 비디오 슬라이스 재사용, 언어별 자막 적용
- 여러 언어에 대한 비디오 생성 테스트

### 6단계: 출력 구조 업데이트
- 모든 언어에 대한 구조를 생성하도록 `OutputManager` 수정
- 다중 언어 출력을 위한 경로 관리 업데이트
- 출력 구조 생성 테스트

### 7단계: API 통합
- `target_languages`를 수락하도록 API 엔드포인트 업데이트
- `VideoPipelineService`를 파이프라인에 언어를 전달하도록 업데이트
- 여러 언어로 API 테스트

### 8단계: 테스트 및 검증
- 2-3개 언어로 동시에 테스트
- 비디오 슬라이스가 재사용되는지 확인 (파일 시스템 확인)
- 번역이 자연스러운지 확인 (의역)
- 모든 언어가 올바른 비디오를 생성하는지 확인
- 성능 테스트 (순차보다 빠를 것)

## 주요 설계 결정

### 1. 번역 타이밍
**결정**: LLM 분석 후, 비디오 처리 전
- **근거**: 모든 언어에 대한 병렬 비디오 생성 가능
- **이점**: 비용이 많이 드는 LLM 호출 재사용

### 2. 비디오 슬라이스 재사용
**결정**: 한 번 추출, 여러 번 자막 적용
- **근거**: 상당한 처리 시간 절약
- **이점**: 모든 언어에 대해 동일한 비디오 품질

### 3. 하위 호환성
**결정**: 단일 언어로 기본값 설정 (`[language_code]`)
- **근거**: 기존 코드가 계속 작동
- **이점**: 점진적 마이그레이션 경로

### 4. 번역 품질
**결정**: 맥락 인식 번역(의역) 사용
- **근거**: 직역보다 더 나은 학습 경험
- **이점**: 자연스럽고 기억에 남는 번역

## 위험 완화

1. **번역 품질**
   - 각 언어에 대해 원어민으로 테스트
   - 필요시 직역으로 폴백 제공
   - 수동 번역 검토/편집 허용

2. **비디오 슬라이스 저장**
   - 적절한 정리와 함께 임시 디렉토리 사용
   - 디스크 공간 사용 모니터링
   - 모든 언어 처리 후 슬라이스 정리

3. **메모리 사용**
   - 메모리가 제한된 경우 언어를 순차적으로 처리
   - 배치로 언어 처리 옵션

4. **오류 처리**
   - 한 언어가 실패해도 다른 언어 계속 진행
   - 언어별 오류 로깅
   - 일부 언어가 성공하면 부분 결과 반환

5. **성능**
   - 번역 API 속도 제한 모니터링
   - 동일한 콘텐츠가 요청되면 번역 캐싱
   - 배치 번역 호출 최적화

## 테스트 전략

### 단위 테스트
- 여러 언어로 번역 서비스
- 다른 언어에 대한 자막 생성
- 비디오 슬라이스 재사용 로직

### 통합 테스트
- 비디오 슬라이스가 재사용되는지 확인 (파일 시스템 확인)
- 번역이 자연스러운지 확인 (의역) 직역 아님
- 모든 언어가 올바른 비디오를 생성하는지 확인

### 엔드투엔드 테스트
- 2-3개 언어로 동시에 비디오 생성
- 언어 간 출력 품질 비교
- 출력 구조가 올바른지 확인

### 성능 테스트
- 3개 언어에 대한 시간을 3회 순차 실행과 비교
- LLM 호출 횟수 측정 (1x여야 함)
- 비디오 추출 횟수 측정 (표현당 1x여야 함)

## 향후 개선 사항

1. **번역 캐싱**: 동일한 콘텐츠를 다시 번역하지 않도록 번역 캐싱
2. **점진적 번역**: 기존 비디오를 다시 처리하지 않고 언어 추가
3. **번역 품질 메트릭**: 자동 품질 점수 매기기
4. **병렬 번역**: 여러 언어를 병렬로 번역
5. **사용자 정의 번역 모델**: 언어별로 다른 번역 모델 지원

## 참고 자료

- 관련 문서:
  - `docs/core/structured_video_creation_eng.md` - 현재 비디오 생성 아키텍처
  - `docs/core/subtitle_sync_guide_eng.md` - 자막 처리 세부사항
  - `langflix/templates/expression_analysis_prompt*.txt` - 현재 LLM 프롬프트

- 코드 참조:
  - `langflix/main.py::LangFlixPipeline` - 메인 파이프라인 클래스
  - `langflix/core/expression_analyzer.py` - LLM 분석
  - `langflix/core/video_editor.py` - 비디오 생성
  - `langflix/core/subtitle_processor.py` - 자막 처리

