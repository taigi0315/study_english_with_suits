# LangFlix 기여 가이드

**버전:** 1.0  
**최종 업데이트:** 2025년 10월 19일

LangFlix에 기여해주시려는 관심에 감사드립니다! 이 가이드는 개발 프로세스, 코딩 표준, 기여 워크플로우를 시작하는 데 도움을 드릴 것입니다.

---

## 목차

1. [시작하기](#시작하기)
2. [개발 환경 설정](#개발-환경-설정)
3. [코드 스타일 및 표준](#코드-스타일-및-표준)
4. [테스팅 가이드라인](#테스팅-가이드라인)
5. [풀 리퀘스트 프로세스](#풀-리퀘스트-프로세스)
6. [이슈 보고](#이슈-보고)
7. [아키텍처 개요](#아키텍처-개요)
8. [일반적인 개발 작업](#일반적인-개발-작업)

---

## 시작하기

### 사전 요구사항

기여하기 전에 다음이 있는지 확인하세요:

- Python 3.9+ 설치됨
- Git 설치됨
- 비디오 처리 개념에 대한 기본 이해
- 머신러닝 API에 대한 친숙함 (특히 Google Gemini)

### 빠른 시작

1. **저장소 포크** (GitHub에서)
2. **포크 복제** (로컬에서):
   ```bash
   git clone https://github.com/YOUR_USERNAME/study_english_with_suits.git
   cd study_english_with_suits
   ```

3. **개발 환경 설정** ([개발 환경 설정](#개발-환경-설정) 참조)

4. **변경사항을 위한 새 브랜치 생성**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

---

## 개발 환경 설정

### 1. 가상 환경

```bash
# 가상 환경 생성
python3 -m venv venv

# 활성화
source venv/bin/activate  # Windows: venv\Scripts\activate

# pip 업그레이드
pip install --upgrade pip
```

### 2. 종속성 설치

```bash
# 프로젝트 종속성 설치
pip install -r requirements.txt

# 개발 종속성 설치
pip install pytest pytest-cov flake8 black isort mypy
```

### 3. 환경 설정

```bash
# 환경 템플릿 복사
cp env.example .env

# API 키와 설정으로 편집
nano .env
```

**개발에 필요한 환경 변수:**
```env
GEMINI_API_KEY=your_gemini_api_key_here
LANGFLIX_LOG_LEVEL=DEBUG
```

### 4. 설정 확인

```bash
# 기본 테스트 실행
python -m pytest tests/unit/

# 코드 스타일 확인
flake8 langflix/

# 임포트가 작동하는지 확인
python -c "import langflix; print('설정 성공!')"
```

---

## 코드 스타일 및 표준

### Python 코드 스타일

**PEP 8**을 따르되, 프로젝트별 수정사항이 있습니다:

#### 형식화
- **줄 길이**: 88자 (Black 표준)
- **들여쓰기**: 4칸 (탭 없음)
- **문자열 따옴표**: 독스트링은 큰따옴표, 코드는 가능한 한 작은따옴표

#### 명명 규칙
- **클래스**: `PascalCase` (예: `LangFlixPipeline`)
- **함수/변수**: `snake_case` (예: `process_episode`)
- **상수**: `UPPER_SNAKE_CASE` (예: `MAX_RETRIES`)
- **프라이빗 메서드**: 선행 밑줄 (예: `_process_chunk`)

### 코드 구성

#### 모듈 구조
```python
"""
모듈의 목적을 설명하는 모듈 독스트링
"""

# 표준 라이브러리 임포트
import os
from pathlib import Path
from typing import List, Optional

# 써드파티 임포트
import ffmpeg
from pydantic import BaseModel

# 로컬 임포트
from . import settings
from .models import ExpressionAnalysis
```

#### 함수 문서화
```python
def process_episode(file_path: str, options: Optional[Dict] = None) -> ProcessResult:
    """
    표현 추출을 위해 단일 에피소드를 처리합니다.
    
    Args:
        file_path: 에피소드 파일(.srt)의 경로
        options: 선택적 처리 설정
        
    Returns:
        추출된 표현과 메타데이터가 포함된 ProcessResult
        
    Raises:
        FileNotFoundError: 에피소드 파일이 존재하지 않는 경우
        ValueError: 파일 형식이 잘못된 경우
    """
    # 구현부
    pass
```

### 자동 코드 형식화

일관성을 보장하기 위해 자동화된 도구를 사용합니다:

```bash
# Black으로 코드 형식화
black langflix/ tests/

# isort로 임포트 정렬
isort langflix/ tests/

# 스타일 이슈 확인
flake8 langflix/ tests/

# mypy로 타입 검사
mypy langflix/
```

**사전 커밋 훅 설정:**
```bash
# pre-commit 설치
pip install pre-commit

# 훅 설정
pre-commit install
```

**`.pre-commit-config.yaml`:**
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.9

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

---

## 테스팅 가이드라인

### 테스트 구조

테스트는 `tests/` 디렉토리에 구성됩니다:

```
tests/
├── unit/           # 개별 컴포넌트용 단위 테스트
├── integration/    # 여러 컴포넌트용 통합 테스트
├── functional/     # 엔드투엔드 기능 테스트
└── step_by_step/   # 단계별 파이프라인 테스트
```

### 테스트 작성

#### 단위 테스트
개별 함수와 클래스를 독립적으로 테스트합니다:

```python
# tests/unit/test_expression_analyzer.py
import pytest
from langflix.expression_analyzer import analyze_chunk
from langflix.models import ExpressionAnalysis

def test_analyze_chunk_returns_expressions():
    """analyze_chunk가 예상된 구조를 반환하는지 테스트합니다."""
    chunk = [
        {"start_time": "00:01:25,657", "end_time": "00:01:28,200", "text": "테스트 대화"}
    ]
    
    result = analyze_chunk(chunk, language_code="ko")
    
    assert isinstance(result, list)
    assert all(isinstance(expr, ExpressionAnalysis) for expr in result)

def test_analyze_chunk_handles_empty_chunk():
    """빈 입력으로 동작을 테스트합니다."""
    result = analyze_chunk([])
    assert result == []
```

#### 통합 테스트
여러 컴포넌트 간의 상호작용을 테스트합니다:

```python
# tests/integration/test_pipeline.py
import pytest
from langflix.main import LangFlixPipeline

def test_full_pipeline_execution():
    """샘플 데이터로 전체 파이프라인을 테스트합니다."""
    pipeline = LangFlixPipeline(
        subtitle_file="tests/fixtures/sample.srt",
        video_dir="tests/fixtures/video",
        output_dir="tests/temp_output"
    )
    
    results = pipeline.run(max_expressions=2, dry_run=True)
    
    assert results["total_expressions"] > 0
    assert results["processed_expressions"] <= 2
```

#### 기능 테스트
엔드투엔드 기능을 테스트합니다:

```python
# tests/functional/test_end_to_end.py
def test_complete_workflow_with_real_files():
    """실제 자막 및 비디오 파일로 전체 워크플로우를 테스트합니다."""
    # 이 테스트는 실제 테스트 미디어 파일을 사용합니다
    pass
```

### 테스트 데이터

- 테스트 픽스처는 `tests/fixtures/`에 위치
- 작고 대표적인 샘플 파일 사용
- 큰 미디어 파일은 절대 커밋하지 말고 테스트 데이터 생성기 사용

### 테스트 실행

```bash
# 모든 테스트 실행
python -m pytest

# 특정 테스트 카테고리 실행
python -m pytest tests/unit/
python -m pytest tests/integration/

# 커버리지와 함께 실행
python -m pytest --cov=langflix --cov-report=html

# 상세 모드로 실행
python -m pytest -v
```

### 테스트 요구사항

- **커버리지**: 최소 80% 코드 커버리지 유지
- **속도**: 단위 테스트는 빠르게 실행되어야 함 (< 1초)
- **독립성**: 테스트는 서로 의존하지 않아야 함
- **결정성**: 테스트는 일관된 결과를 생성해야 함

---

## 풀 리퀘스트 프로세스

### 제출 전

1. **테스트 통과 확인**:
   ```bash
   python -m pytest
   ```

2. **코드 스타일 확인**:
   ```bash
   black --check langflix/ tests/
   flake8 langflix/ tests/
   ```

3. **문서 업데이트** (사용자 대상 기능에 영향을 주는 변경사항인 경우)

4. **샘플 데이터로 변경사항 테스트**

### 풀 리퀘스트 템플릿

PR 생성 시 이 템플릿을 사용하세요:

```markdown
## 설명
변경사항과 동기에 대한 간단한 설명

## 변경 유형
- [ ] 버그 수정
- [ ] 새로운 기능
- [ ] 호환성을 깨는 변경
- [ ] 문서 업데이트

## 테스팅
- [ ] 단위 테스트 추가/업데이트
- [ ] 통합 테스트 추가/업데이트
- [ ] 수동 테스팅 수행

## 체크리스트
- [ ] 코드가 프로젝트 스타일 가이드라인을 따름
- [ ] 자체 리뷰 완료
- [ ] 문서 업데이트 (필요한 경우)
- [ ] 테스트가 로컬에서 통과
```

### 리뷰 프로세스

1. **자동 검사** 통과 (CI/CD 파이프라인)
2. **코드 리뷰** (유지관리자)
3. **테스팅** (필요한 경우 유지관리자)
4. **승인** 및 머지

---

## 이슈 보고

### 버그 보고

버그 보고 시 다음을 포함하세요:

1. **환경 세부사항**:
   ```markdown
   - OS: [예: Ubuntu 20.04, macOS 13.0]
   - Python 버전: [예: 3.9.7]
   - LangFlix 버전: [예: 1.0.0]
   ```

2. **재현 단계**:
   ```markdown
   1. 명령 실행: `python -m langflix.main --subtitle example.srt`
   2. 오류 확인: [오류 메시지]
   ```

3. **예상 vs 실제 동작**

4. **로그** (사용 가능한 경우):
   ```bash
   # 관련 로그 출력 포함
   tail -n 50 langflix.log
   ```

### 기능 요청

기능 요청 시 다음을 포함하세요:

1. **사용 사례 설명**
2. **예상 동작**
3. **가능한 구현** (아이디어가 있는 경우)

---

## 아키텍처 개요

### 핵심 컴포넌트

```
langflix/
├── main.py              # 메인 파이프라인 오케스트레이터
├── models.py            # Pydantic 데이터 모델
├── settings.py          # 설정 관리
├── expression_analyzer.py # LLM 상호작용 및 분석
├── video_processor.py   # 비디오 파일 작업
├── video_editor.py      # 비디오 편집 및 효과
├── subtitle_parser.py   # 자막 파일 파싱
├── subtitle_processor.py # 자막 처리 유틸리티
├── prompts.py           # LLM 프롬프트 생성
├── output_manager.py    # 출력 디렉토리 관리
└── templates/           # 외부 프롬프트 템플릿
```

### 데이터 흐름

1. **입력**: SRT 자막 파일과 해당 비디오 파일
2. **파싱**: 자막이 파싱되고 청크로 분할됨
3. **분석**: LLM이 청크를 표현 분석함
4. **처리**: 비디오 클립이 추출되고 처리됨
5. **출력**: 자막과 슬라이드가 있는 교육용 비디오

### 주요 디자인 패턴

- **파이프라인 패턴**: 메인 워크플로우는 파이프라인 아키텍처를 따름
- **전략 패턴**: 다른 언어 수준은 다른 분석 전략을 사용
- **팩토리 패턴**: 출력 관리자가 적절한 디렉토리 구조를 생성

---

## 일반적인 개발 작업

### 새 언어 추가

1. **언어 설정 업데이트**:
   ```python
   # langflix/language_config.py
   LANGUAGE_CONFIGS = {
       # ... 기존 언어들
       "zh": {
           "name": "Chinese (Simplified)",
           "level_descriptions": {
               "beginner": "Beginner Chinese learning",
               # ...
           }
       }
   }
   ```

2. **CLI 선택 추가**:
   ```python
   # langflix/main.py
   parser.add_argument(
       "--language-code",
       choices=['ko', 'ja', 'zh', 'es', 'fr', 'zh'],  # 새 언어 추가
       default="ko"
   )
   ```

3. **샘플 데이터로 테스트**

### 새 비디오 코덱 추가

1. **비디오 프로세서 업데이트**:
   ```python
   # langflix/video_processor.py
   class VideoProcessor:
       def __init__(self, media_dir: str = "assets/media"):
           self.supported_formats = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.webm'}  # 새 형식 추가
   ```

2. **필요한 경우 FFmpeg 작업 업데이트**

### LLM 프롬프트 수정

1. **프롬프트 템플릿 업데이트**:
   ```bash
   # 템플릿 파일 편집
   nano langflix/templates/expression_analysis_prompt.txt
   ```

2. **프롬프트 변경사항 테스트**:
   ```python
   # langflix/prompts.py
   def get_prompt_for_chunk(subtitle_chunk, ...):
       # 프롬프트 형식화 로직
       pass
   ```

### 새 출력 형식 추가

1. **출력 관리자 확장**:
   ```python
   # langflix/output_manager.py
   def create_output_structure(subtitle_file, language_code, output_dir):
       # 새 디렉토리 또는 파일 구조 추가
       pass
   ```

2. **새 형식 지원을 위해 비디오 편집기 업데이트** (필요한 경우)

---

## 성능 고려사항

### 프로파일링

병목 지점을 식별하기 위해 프로파일링 도구를 사용하세요:

```python
import cProfile
import pstats

# 함수 프로파일링
profiler = cProfile.Profile()
profiler.enable()

# 코드 실행
your_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats()
```

### 메모리 관리

- 큰 비디오 객체를 즉시 정리
- 큰 데이터셋에 대한 제너레이터 사용
- 비디오 처리 중 메모리 사용량 모니터링

### API 최적화

- 적절한 재시도 로직 구현
- 적절한 경우 비싼 작업 캐싱
- 가능한 곳에서 작업 배치화

---

## 기여 체크리스트

기여를 제출하기 전에:

- [ ] 코드가 스타일 가이드라인을 따름 (`black`, `flake8`, `isort`)
- [ ] 테스트가 추가되거나 업데이트됨
- [ ] 테스트가 로컬에서 통과 (`pytest`)
- [ ] 필요시 문서가 업데이트됨
- [ ] 큰 파일이 커밋되지 않음
- [ ] 환경 변수가 커밋되지 않음
- [ ] 변경사항이 집중적이고 원자적임
- [ ] 커밋 메시지가 명확하고 설명적임

---

## 도움받기

- **문서**: `docs/` 디렉토리의 기존 문서 확인
- **이슈**: 새 이슈를 만들기 전에 기존 이슈 검색
- **토론**: 질문에 GitHub Discussions 사용
- **코드 리뷰**: PR 댓글에서 도움 요청

---

**LangFlix에 기여해주셔서 감사합니다! 여러분의 노력이 언어 학습을 더욱 접근 가능하고 효과적으로 만듭니다.**

**이 기여 가이드의 영어 버전은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참조하세요**

**관련 문서:**
- [API 참조](API_REFERENCE_KOR.md) - 코드베이스 이해
- [배포 가이드](DEPLOYMENT_KOR.md) - 환경 설정
- [문제 해결 가이드](TROUBLESHOOTING_KOR.md) - 일반적인 문제와 해결책
