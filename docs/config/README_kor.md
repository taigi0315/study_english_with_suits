# Configuration 모듈 문서

## 개요

`langflix/config/` 모듈은 LangFlix를 위한 설정 관리를 제공하며, 환경 변수 오버라이드와 표현식 기반 학습 설정을 포함한 YAML 설정 파일을 처리합니다.

**최종 업데이트:** 2025-01-30

## 목적

이 모듈의 주요 역할:
- 여러 소스에서 설정 로드 및 병합
- 표현식 기반 학습 설정 관리
- 플랫폼별 폰트 감지를 위한 폰트 유틸리티 제공
- 설정 캐스케이딩 처리 (기본값 → 사용자 → 환경 변수)

## 주요 구성 요소

### ConfigLoader

**위치:** `langflix/config/config_loader.py`

우선순위를 가진 설정 로딩 관리:
1. 기본 설정 (`langflix/config/default.yaml`)
2. 사용자 설정 (프로젝트 루트의 `config.yaml`)
3. 환경 변수 오버라이드 (`LANGFLIX_SECTION_KEY` 형식)

**주요 메서드:**

```python
def get(self, *keys, default: Any = None) -> Any:
    """
    점 표기법 또는 여러 키를 사용하여 설정 값 가져오기.
    
    예시:
        config.get('llm', 'max_input_length')
        config.get('llm.max_input_length')
        config.get('video', 'codec', default='libx264')
    """
```

```python
def get_section(self, section: str) -> Dict[str, Any]:
    """전체 설정 섹션 가져오기."""
```

**환경 변수 오버라이드:**

환경 변수는 다음 형식이어야 함: `LANGFLIX_SECTION_KEY`

예시: `LANGFLIX_LLM_MAX_INPUT_LENGTH=5000`

로더는 자동으로:
- 중첩 키 파싱 (예: `LANGFLIX_LLM_MAX_INPUT_LENGTH`)
- 문자열 값을 적절한 타입으로 변환 (int, float, bool)
- 기존 설정과 병합

**사용 예시:**

```python
from langflix.config.config_loader import ConfigLoader

loader = ConfigLoader()
max_length = loader.get('llm', 'max_input_length', default=4000)
llm_config = loader.get_section('llm')
```

### ExpressionConfig

**위치:** `langflix/config/expression_config.py`

표현식 기반 학습 기능을 위한 데이터클래스 기반 설정입니다.

**설정 클래스:**

```python
@dataclass
class SubtitleStylingConfig:
    """표현식용 자막 스타일링 설정"""
    default: Dict[str, Any]
    expression_highlight: Dict[str, Any]
```

```python
@dataclass
class PlaybackConfig:
    """표현식용 비디오 재생 설정"""
    expression_repeat_count: int = 2
    context_play_count: int = 1
    repeat_delay_ms: int = 200
    transition_effect: str = 'fade'
    transition_duration_ms: int = 150
```

```python
@dataclass
class LayoutConfig:
    """다양한 비디오 포맷을 위한 레이아웃 설정"""
    landscape: Dict[str, Any]
    portrait: Dict[str, Any]
```

**사용 예시:**

```python
from langflix.config.expression_config import ExpressionConfig

config_dict = {
    'subtitle_styling': {...},
    'playback': {'expression_repeat_count': 3},
    'layout': {...}
}

expr_config = ExpressionConfig.from_dict(config_dict)
repeat_count = expr_config.playback.expression_repeat_count
```

### FontUtils

**위치:** `langflix/config/font_utils.py`

플랫폼별 폰트 감지 및 선택 유틸리티입니다.

**주요 함수:**

```python
def get_platform_default_font() -> str:
    """
    플랫폼에 따라 적절한 기본 폰트 가져오기.
    
    Returns:
        플랫폼별 기본 폰트 경로, 없으면 빈 문자열
        
    지원 플랫폼:
    - macOS: /System/Library/Fonts/AppleSDGothicNeo.ttc
    - Linux: 일반적인 한국어 폰트 시도 (NanumGothic, DejaVuSans, NotoSansCJK)
    - Windows: Malgun Gothic, Arial 시도
    """
```

```python
def get_font_file_for_language(language_code: Optional[str] = None) -> str:
    """
    주어진 언어 또는 기본값에 대한 폰트 파일 경로 가져오기.
    
    Args:
        language_code: 선택적 언어 코드 (예: 'ko', 'ja', 'zh', 'es')
        
    Returns:
        적절한 폰트 파일 경로
    """
```

**사용 예시:**

```python
from langflix.config.font_utils import get_font_file_for_language

font_path = get_font_file_for_language('ko')
# 플랫폼별 한국어 폰트 경로 반환

default_font = get_font_file_for_language()
# 플랫폼 기본 폰트 반환
```

## 설정 구조

### 기본 설정 (`default.yaml`)

기본 설정에는 다음이 포함됩니다:

```yaml
expression:
  subtitle_styling:
    default:
      color: '#FFFFFF'
      font_size: 24
      font_weight: 'normal'
      background_color: '#000000'
    expression_highlight:
      color: '#FFD700'
      font_size: 28
      font_weight: 'bold'
      
  playback:
    expression_repeat_count: 2
    context_play_count: 1
    repeat_delay_ms: 200
    
  layout:
    landscape:
      resolution: [1920, 1080]
      expression_video:
        width_percent: 50
    portrait:
      resolution: [1080, 1920]
      context_video:
        height_percent: 75

llm:
  max_input_length: 4000
  temperature: 0.7
```

## 구현 세부사항

### 설정 병합

`ConfigLoader`는 재귀적 딕셔너리 병합을 사용합니다:

1. **기본 설정**: `default.yaml`에서 로드
2. **사용자 오버라이드**: 사용자 `config.yaml` 병합 (존재하는 경우)
3. **환경 변수 오버라이드**: `LANGFLIX_` 접두사가 있는 환경 변수 적용

중첩된 딕셔너리는 재귀적으로 병합되고, 간단한 값은 교체됩니다.

### 환경 변수 파싱

환경 변수는 다음과 같이 파싱됩니다:

1. `LANGFLIX_` 접두사 제거
2. 나머지를 `_`로 분할하여 섹션 경로 얻기
3. 중첩 섹션으로 이동
4. 최종 키 값 설정
5. 타입 자동 변환 (int, float, bool, string)

예시: `LANGFLIX_LLM_MAX_INPUT_LENGTH=5000`
- 다음이 됨: `config['llm']['max_input_length'] = 5000`

### 폰트 감지

폰트 감지는 다음 방식으로 작동:
1. 플랫폼별 폰트 위치 확인
2. 파일 존재 여부 확인
3. 시스템 기본값으로 폴백
4. 언어별 폰트의 경우 `LanguageConfig` 모듈 확인

## 의존성

- `yaml`: YAML 파일 파싱
- `pathlib`: 경로 처리
- `os`: 환경 변수 접근
- `platform`: 플랫폼 감지
- `langflix.core.language_config`: 언어별 폰트 설정

## 일반적인 작업

### 설정 로드

```python
from langflix.config.config_loader import ConfigLoader

loader = ConfigLoader(user_config_path="custom_config.yaml")
value = loader.get('section', 'key', default='default_value')
```

### 환경 변수로 오버라이드

```bash
# 환경 변수 설정
export LANGFLIX_LLM_MAX_INPUT_LENGTH=6000

# 설정이 이 값을 사용함
python your_script.py
```

### 표현식 설정 가져오기

```python
from langflix.config.expression_config import ExpressionConfig

# ConfigLoader에서 로드
loader = ConfigLoader()
expr_config_dict = loader.get_section('expression')

# ExpressionConfig 객체 생성
expr_config = ExpressionConfig.from_dict(expr_config_dict)
repeat_count = expr_config.playback.expression_repeat_count
```

### 폰트 경로 가져오기

```python
from langflix.config.font_utils import get_font_file_for_language

# 언어별 폰트 가져오기
font_path = get_font_file_for_language('ko')

# 또는 플랫폼 기본값
default_font = get_font_file_for_language()
```

### 사용자 설정 저장

```python
loader = ConfigLoader()
config = loader.config.copy()
config['llm']['max_input_length'] = 5000
loader.save_user_config(config)
```

## 설정 파일

### 프로젝트 구조

```
project_root/
├── config.yaml              # 사용자 설정 (선택사항)
├── langflix/
│   └── config/
│       ├── default.yaml     # 기본 설정
│       ├── config_loader.py
│       ├── expression_config.py
│       └── font_utils.py
```

### 설정 우선순위

1. **환경 변수** (최우선)
2. **사용자 설정** (`config.yaml`)
3. **기본 설정** (`default.yaml`) (최하위)

## 주의사항

1. **환경 변수 형식**: `LANGFLIX_` 접두사로 시작해야 함
2. **타입 변환**: 환경 변수는 자동 변환됨 (int, float, bool)
3. **중첩 키**: 중첩 섹션 구분에 밑줄 사용 (`LANGFLIX_SECTION_SUBSECTION_KEY`)
4. **폰트 경로**: 폰트 유틸리티는 폰트를 찾지 못하면 빈 문자열 반환 - 사용 전 확인 필요
5. **설정 재로드**: 파일에서 설정을 다시 로드하려면 `loader.reload()` 호출
6. **플랫폼 폰트**: 폰트 감지는 플랫폼마다 다르며, 일부 시스템에서는 빈 문자열 반환 가능

## 관련 모듈

- `langflix.settings`: ConfigLoader를 래핑하는 전역 설정
- `langflix.core.language_config`: 언어별 폰트 설정
- `langflix/core/`: 비디오 처리를 위한 설정 사용

