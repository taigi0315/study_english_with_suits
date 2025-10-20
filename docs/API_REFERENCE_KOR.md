# LangFlix API 참조 문서

**버전:** 1.0  
**최종 업데이트:** 2025년 10월 19일

이 문서는 LangFlix의 모든 공개 클래스와 메서드에 대한 포괄적인 API 문서를 제공합니다. 프로그래밍 방식 접근 및 통합에 사용하세요.

---

## 목차

1. [핵심 파이프라인](#핵심-파이프라인)
2. [데이터 모델](#데이터-모델)
3. [비디오 처리](#비디오-처리)
4. [자막 처리](#자막-처리)
5. [표현 분석](#표현-분석)
6. [설정](#설정)
7. [유틸리티 함수](#유틸리티-함수)

---

## 핵심 파이프라인

### `LangFlixPipeline`

전체 LangFlix 워크플로우를 조정하는 메인 오케스트레이터 클래스입니다.

#### 생성자

```python
LangFlixPipeline(
    subtitle_file: str,
    video_dir: str = "assets/media",
    output_dir: str = "output",
    language_code: str = "ko"
)
```

**매개변수:**
- `subtitle_file` (str): 자막 파일 경로 (.srt)
- `video_dir` (str): 비디오 파일이 포함된 디렉토리 (기본값: "assets/media")
- `output_dir` (str): 출력 파일 디렉토리 (기본값: "output")
- `language_code` (str): 대상 언어 코드 (기본값: "ko")

#### 메서드

##### `run(max_expressions=None, dry_run=False, language_level=None, save_llm_output=False, test_mode=False, no_shorts=False) -> Dict[str, Any]`

전체 LangFlix 파이프라인을 실행합니다.

**매개변수:**
- `max_expressions` (int, 선택사항): 처리할 최대 표현 수. None이면 발견된 모든 표현을 처리합니다.
- `dry_run` (bool): True이면 비디오 파일을 만들지 않고 분석만 수행 (기본값: False)
- `language_level` (str, 선택사항): 대상 언어 수준 ("beginner", "intermediate", "advanced", "mixed"). None이면 설정에서 기본값 사용.
- `save_llm_output` (bool): True이면 검토를 위해 LLM 응답을 파일에 저장 (기본값: False)
- `test_mode` (bool): True이면 테스트를 위해 첫 번째 청크만 처리 (기본값: False)
- `no_shorts` (bool): True이면 숏폼 비디오 생성을 건너뜀 (기본값: False, 숏폼 비디오는 기본적으로 생성됨)

**반환값:**
- 처리 결과가 포함된 딕셔너리:
  ```python
  {
      "total_subtitles": int,
      "total_chunks": int,
      "total_expressions": int,
      "processed_expressions": int,
      "output_directory": str,
      "series_name": str,
      "episode_name": str,
      "language_code": str,
      "timestamp": str
  }
  ```

**예제:**
```python
from langflix.main import LangFlixPipeline

pipeline = LangFlixPipeline(
    subtitle_file="assets/media/Suits/Suits.S01E01.srt",
    video_dir="assets/media",
    output_dir="output",
    language_code="ko"
)

results = pipeline.run(
    max_expressions=5,
    language_level="intermediate",
    dry_run=False
)

print(f"처리된 표현 수: {results['processed_expressions']}")
```

---

## 데이터 모델

### `ExpressionAnalysis`

단일 분석된 표현을 나타내는 Pydantic 모델입니다.

```python
class ExpressionAnalysis(BaseModel):
    dialogues: List[str]
    translation: List[str]
    expression: str
    expression_translation: str
    context_start_time: str
    context_end_time: str
    expression_start_time: Optional[str] = None
    expression_end_time: Optional[str] = None
    similar_expressions: List[str]
```

**필드:**
- `dialogues` (List[str]): 장면의 전체 대화 라인
- `translation` (List[str]): 모든 대화 라인의 번역 (동일한 순서)
- `expression` (str): 학습할 메인 표현/구문
- `expression_translation` (str): 메인 표현의 번역
- `context_start_time` (str): 대화 컨텍스트가 시작되어야 하는 타임스탬프 (형식: "HH:MM:SS,mmm")
- `context_end_time` (str): 대화 컨텍스트가 끝나야 하는 타임스탬프 (형식: "HH:MM:SS,mmm")
- `expression_start_time` (str, 선택사항): 표현 구문이 시작되는 정확한 타임스탬프
- `expression_end_time` (str, 선택사항): 표현 구문이 끝나는 정확한 타임스탬프
- `similar_expressions` (List[str]): 1-3개의 유사한 표현 또는 대안

**예제:**
```python
from langflix.models import ExpressionAnalysis

expr = ExpressionAnalysis(
    dialogues=["I'm paying you millions,", "and you're telling me I'm gonna get screwed?"],
    translation=["나는 당신에게 수백만 달러를 지불하고 있는데,", "당신은 내가 속임을 당할 것이라고 말하고 있나요?"],
    expression="I'm gonna get screwed",
    expression_translation="속임을 당할 것 같아요",
    context_start_time="00:01:25,657",
    context_end_time="00:01:32,230",
    similar_expressions=["I'm going to be cheated", "I'm getting the short end of the stick"]
)
```

### `ExpressionAnalysisResponse`

여러 표현 분석을 담는 컨테이너입니다.

```python
class ExpressionAnalysisResponse(BaseModel):
    expressions: List[ExpressionAnalysis]
```

---

## 비디오 처리

### `VideoProcessor`

비디오 파일 로딩, 검증, 클립 추출을 포함한 비디오 파일 작업을 처리합니다.

#### 생성자

```python
VideoProcessor(media_dir: str = "assets/media")
```

**매개변수:**
- `media_dir` (str): 비디오 파일이 포함된 디렉토리

#### 메서드

##### `find_video_file(subtitle_file_path: str) -> Optional[Path]`

자막 파일에 해당하는 비디오 파일을 찾습니다.

**매개변수:**
- `subtitle_file_path` (str): 자막 파일 경로

**반환값:**
- `Optional[Path]`: 해당하는 비디오 파일의 경로, 없으면 None

##### `extract_clip(video_path: str, start_time: str, end_time: str, output_path: str) -> bool`

지정된 타임스탬프 간의 비디오 클립을 추출합니다.

**매개변수:**
- `video_path` (str): 소스 비디오 파일 경로
- `start_time` (str): 시작 타임스탬프 (형식: "HH:MM:SS,mmm")
- `end_time` (str): 끝 타임스탬프 (형식: "HH:MM:SS,mmm")
- `output_path` (str): 출력 클립 경로

**반환값:**
- `bool`: 추출이 성공하면 True, 그렇지 않으면 False

##### `get_video_info(video_path: str) -> Dict[str, Any]`

비디오 파일 메타데이터 및 속성을 가져옵니다.

**매개변수:**
- `video_path` (str): 비디오 파일 경로

**반환값:**
- 비디오 정보를 포함한 딕셔너리 (지속시간, 해상도, 코덱 등)

**예제:**
```python
from langflix.video_processor import VideoProcessor

processor = VideoProcessor("assets/media")

# 비디오 파일 찾기
video_path = processor.find_video_file("assets/media/Suits/Suits.S01E01.srt")
if video_path:
    # 클립 추출
    success = processor.extract_clip(
        str(video_path),
        "00:01:25,657",
        "00:01:32,230",
        "output/clip.mkv"
    )
    
    # 비디오 정보 가져오기
    info = processor.get_video_info(str(video_path))
    print(f"지속시간: {info.get('duration')}")
```

---

## 자막 처리

### `SubtitleProcessor`

자막 파일 작업 및 처리를 담당합니다.

#### 생성자

```python
SubtitleProcessor(subtitle_file: str)
```

**매개변수:**
- `subtitle_file` (str): 자막 파일 경로 (.srt)

#### 메서드

##### `find_expression_timing(expression_text: str, start_time: str, end_time: str) -> Dict[str, str]`

시간 범위 내에서 표현의 정확한 타이밍을 찾습니다.

**매개변수:**
- `expression_text` (str): 타이밍을 찾을 표현 텍스트
- `start_time` (str): 검색 범위 시작
- `end_time` (str): 검색 범위 끝

**반환값:**
- `start_time`과 `end_time` 키를 포함한 딕셔너리. 정확한 타임스탬프를 담고 있습니다.

##### `create_dual_language_subtitle_file(expression: ExpressionAnalysis, output_path: str) -> bool`

표현에 대한 이중 언어 자막 파일을 생성합니다.

**매개변수:**
- `expression` (ExpressionAnalysis): 대화와 번역을 포함한 표현 데이터
- `output_path` (str): 출력 자막 파일 경로

**반환값:**
- `bool`: 성공하면 True, 그렇지 않으면 False

**예제:**
```python
from langflix.subtitle_processor import SubtitleProcessor
from langflix.models import ExpressionAnalysis

processor = SubtitleProcessor("assets/media/Suits/Suits.S01E01.srt")

# 표현 타이밍 찾기
timing = processor.find_expression_timing(
    "I'm gonna get screwed",
    "00:01:25,657",
    "00:01:32,230"
)

# 이중 언어 자막 생성
success = processor.create_dual_language_subtitle_file(
    expression,
    "output/expression_subtitles.srt"
)
```

---

## 표현 분석

### `analyze_chunk`

LLM으로 자막 청크를 분석하는 함수입니다.

```python
def analyze_chunk(
    subtitle_chunk: List[dict],
    language_level: str = None,
    language_code: str = "ko",
    max_retries: int = 3
) -> List[ExpressionAnalysis]
```

**매개변수:**
- `subtitle_chunk` (List[dict]): 'start_time', 'end_time', 'text' 키를 포함한 자막 딕셔너리 목록
- `language_level` (str, 선택사항): 대상 언어 수준
- `language_code` (str): 대상 언어 코드 (기본값: "ko")
- `max_retries` (int): API 호출 최대 재시도 횟수 (기본값: 3)

**반환값:**
- `List[ExpressionAnalysis]`: 분석된 표현 목록

**예제:**
```python
from langflix.expression_analyzer import analyze_chunk

chunk = [
    {"start_time": "00:01:25,657", "end_time": "00:01:28,200", "text": "I'm paying you millions,"},
    {"start_time": "00:01:28,200", "end_time": "00:01:32,230", "text": "and you're telling me I'm gonna get screwed?"}
]

expressions = analyze_chunk(
    chunk,
    language_level="intermediate",
    language_code="ko"
)

for expr in expressions:
    print(f"표현: {expr.expression}")
    print(f"번역: {expr.expression_translation}")
```

---

## 설정

### `settings`

애플리케이션 설정에 대한 접근을 제공하는 설정 관리 모듈입니다.

#### 함수

##### `get_generation_config() -> Dict[str, Any]`

LLM 생성 설정을 가져옵니다.

**반환값:**
- 생성 매개변수가 포함된 딕셔너리 (temperature, top_p, top_k)

##### `get_min_expressions_per_chunk() -> int`

청크당 최소 표현 제한을 가져옵니다.

**반환값:**
- 청크당 추출할 최소 표현 수

##### `get_max_expressions_per_chunk() -> int`

청크당 최대 표현 제한을 가져옵니다.

**반환값:**
- 청크당 추출할 최대 표현 수

##### `get_max_retries() -> int`

API 호출 최대 재시도 횟수를 가져옵니다.

**반환값:**
- 재시도 횟수

**예제:**
```python
from langflix import settings

# 설정 값 가져오기
gen_config = settings.get_generation_config()
min_expr = settings.get_min_expressions_per_chunk()
max_expr = settings.get_max_expressions_per_chunk()

print(f"Temperature: {gen_config['temperature']}")
print(f"표현 범위: {min_expr}-{max_expr}")
```

### `ConfigLoader`

YAML 기반 설정용 설정 로더입니다.

```python
from langflix.config.config_loader import ConfigLoader

loader = ConfigLoader()
config = loader.get('llm')  # LLM 설정 섹션 가져오기
```

---

## 유틸리티 함수

### 자막 파싱

```python
from langflix.subtitle_parser import parse_srt_file, chunk_subtitles

# SRT 파일 파싱
subtitles = parse_srt_file("path/to/subtitle.srt")

# 처리용 자막 청킹
chunks = chunk_subtitles(subtitles)
```

**반환값:**
- `parse_srt_file()`: 자막 딕셔너리 목록
- `chunk_subtitles()`: 청킹된 자막 목록의 목록

### 출력 관리

```python
from langflix.output_manager import create_output_structure

# 구성된 출력 디렉토리 구조 생성
paths = create_output_structure(
    subtitle_file="assets/media/Suits/Suits.S01E01.srt",
    language_code="ko",
    output_dir="output"
)
```

**반환값:**
- 다양한 파일 유형에 대한 구성된 출력 경로가 포함된 딕셔너리

### 프롬프트 생성

```python
from langflix.prompts import get_prompt_for_chunk

# 자막 청크에 대한 LLM 프롬프트 생성
prompt = get_prompt_for_chunk(
    subtitle_chunk,
    language_level="intermediate",
    language_code="ko"
)
```

**반환값:**
- LLM 처리용 형식화된 프롬프트 문자열

---

## 오류 처리

### 예외 유형

**`ValueError`**: 잘못된 입력 매개변수, 누락된 파일, 또는 처리 실패에 대해 발생됩니다.

**`FileNotFoundError`**: 필요한 파일(비디오, 자막)을 찾을 수 없을 때 발생됩니다.

**`APIError`**: LLM API 관련 실패(타임아웃, 할당량 초과 등)에 대해 발생됩니다.

### 예제 오류 처리

```python
from langflix.main import LangFlixPipeline
import logging

logger = logging.getLogger(__name__)

try:
    pipeline = LangFlixPipeline("subtitle.srt")
    results = pipeline.run()
except ValueError as e:
    logger.error(f"잘못된 입력: {e}")
except FileNotFoundError as e:
    logger.error(f"파일을 찾을 수 없음: {e}")
except Exception as e:
    logger.error(f"예상치 못한 오류: {e}")
```

---

## 모범 사례

### 1. 리소스 관리

비디오 처리에 항상 컨텍스트 매니저 또는 적절한 정리를 사용하세요:

```python
# 좋은 예: 파이프라인이 자동으로 정리하도록 함
pipeline = LangFlixPipeline("subtitle.srt")
results = pipeline.run(max_expressions=5)

# 수동 처리를 위해 적절한 정리 보장
try:
    processor = VideoProcessor()
    success = processor.extract_clip(video_path, start, end, output)
finally:
    # 필요시 정리
    pass
```

### 2. 설정

하드코딩된 값 대신 설정 시스템을 사용하세요:

```python
# 좋은 예: 설정 사용
from langflix import settings

max_retries = settings.get_max_retries()
gen_config = settings.get_generation_config()

# 피해야 할 것: 하드코딩된 값
max_retries = 3  # 나쁨
```

### 3. 오류 처리

잠재적인 실패를 항상 우아하게 처리하세요:

```python
processor = VideoProcessor()
video_path = processor.find_video_file("subtitle.srt")

if video_path is None:
    logger.error("비디오 파일을 찾을 수 없음")
    return False

try:
    success = processor.extract_clip(str(video_path), start, end, output)
    if not success:
        logger.error("비디오 추출 실패")
except Exception as e:
    logger.error(f"추출 중 예상치 못한 오류: {e}")
```

### 4. 로깅

디버깅을 위해 구조화된 로깅을 사용하세요:

```python
import logging

logger = logging.getLogger(__name__)

# 중요한 작업 로깅
logger.info(f"{len(expressions)}개 표현 처리 중")
logger.debug(f"표현 세부사항: {expression.expression}")
logger.error(f"표현 처리 실패: {error}")
```

---

## 통합 예제

### 기본 파이프라인 통합

```python
from langflix.main import LangFlixPipeline
from langflix.models import ExpressionAnalysis

def process_episode(subtitle_path: str, max_expressions: int = 10):
    """단일 에피소드를 처리하고 결과를 반환합니다."""
    pipeline = LangFlixPipeline(
        subtitle_file=subtitle_path,
        language_code="ko"
    )
    
    results = pipeline.run(
        max_expressions=max_expressions,
        language_level="intermediate",
        dry_run=False
    )
    
    return {
        "success": results["processed_expressions"] > 0,
        "expressions_count": results["processed_expressions"],
        "output_dir": results["output_directory"]
    }

# 사용법
result = process_episode("assets/media/Suits/Suits.S01E01.srt")
```

### 사용자 정의 표현 처리

```python
from langflix.expression_analyzer import analyze_chunk
from langflix.video_processor import VideoProcessor
from langflix.subtitle_processor import SubtitleProcessor

def custom_expression_processing(subtitle_path: str, video_dir: str):
    """사용자 정의 처리 워크플로우."""
    # 프로세서 초기화
    video_processor = VideoProcessor(video_dir)
    subtitle_processor = SubtitleProcessor(subtitle_path)
    
    # 파싱 및 분석 (간소화됨)
    from langflix.subtitle_parser import parse_srt_file, chunk_subtitles
    
    subtitles = parse_srt_file(subtitle_path)
    chunks = chunk_subtitles(subtitles)
    
    all_expressions = []
    for chunk in chunks:
        expressions = analyze_chunk(chunk)
        all_expressions.extend(expressions)
    
    return all_expressions
```

---

**이 API 참조 문서의 영어 버전은 [API_REFERENCE.md](API_REFERENCE.md)를 참조하세요**

**관련 문서:**
- [사용자 매뉴얼](USER_MANUAL_KOR.md) - 완전한 사용 가이드
- [문제 해결 가이드](TROUBLESHOOTING_KOR.md) - 일반적인 문제와 해결책

---

*이 API 참조 문서는 각 릴리스마다 자동으로 업데이트됩니다. 최신 정보는 항상 코드베이스의 버전을 참조하세요.*
