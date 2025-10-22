# ADR-013: Expression Configuration Architecture

## Status
Accepted

## Context

LangFlix 프로젝트에서 Expression-based Learning Feature를 구현하기 위해 Configuration 시스템을 확장해야 합니다. 기존 시스템은 기본적인 비디오 처리와 자막 생성에 중점을 두고 있었지만, 새로운 기능에서는 표현식 추출, 교육적 가치 분석, 학습 난이도 분류 등의 고급 기능이 필요합니다.

### 요구사항
- 표현식 기반 학습을 위한 설정 관리
- 자막 스타일링 (기본/강조 스타일)
- 비디오 재생 설정 (반복 횟수, 딜레이)
- 레이아웃 설정 (landscape/portrait)
- LLM 및 WhisperX 통합 설정
- 데이터베이스 스키마 확장

### 기존 시스템
- YAML 기반 설정 시스템 (`ConfigLoader`)
- SQLAlchemy ORM 모델
- Pydantic 모델 (LLM 출력)
- Alembic 마이그레이션

## Decision

Expression-based Learning Feature를 위한 Configuration 아키텍처를 다음과 같이 설계합니다:

### 1. Configuration Dataclass 구조

```python
@dataclass
class SubtitleStylingConfig:
    default: Dict[str, Any]
    expression_highlight: Dict[str, Any]

@dataclass  
class PlaybackConfig:
    expression_repeat_count: int
    context_play_count: int
    repeat_delay_ms: int
    transition_effect: str
    transition_duration_ms: int

@dataclass
class LayoutConfig:
    landscape: Dict[str, Any]
    portrait: Dict[str, Any]

@dataclass
class ExpressionConfig:
    subtitle_styling: SubtitleStylingConfig
    playback: PlaybackConfig
    layout: LayoutConfig
    llm: Dict[str, Any]
    whisper: Dict[str, Any]
```

### 2. 설정 파일 구조

`default.yaml`에 `expression` 섹션 추가:
```yaml
expression:
  subtitle_styling:
    default: { color: '#FFFFFF', font_size: 24, ... }
    expression_highlight: { color: '#FFD700', font_size: 28, ... }
  playback:
    expression_repeat_count: 2
    context_play_count: 1
    repeat_delay_ms: 200
  layout:
    landscape: { resolution: [1920, 1080], ... }
    portrait: { resolution: [1080, 1920], ... }
  llm: { provider: gemini, model: gemini-1.5-pro, ... }
  whisper: { model_size: base, device: cpu, ... }
```

### 3. Database Schema 확장

기존 `Expression` 테이블에 5개 필드 추가:
```sql
ALTER TABLE expressions ADD COLUMN difficulty INTEGER;
ALTER TABLE expressions ADD COLUMN category VARCHAR(50);
ALTER TABLE expressions ADD COLUMN educational_value TEXT;
ALTER TABLE expressions ADD COLUMN usage_notes TEXT;
ALTER TABLE expressions ADD COLUMN score FLOAT;
```

### 4. Pydantic 모델 확장

`ExpressionAnalysis` 모델에 새 필드 추가:
```python
class ExpressionAnalysis(BaseModel):
    # ... 기존 필드들 ...
    difficulty: Optional[int] = Field(default=5, ge=1, le=10)
    category: Optional[str] = Field(default="general")
    educational_value: Optional[str] = Field(default="")
    usage_notes: Optional[str] = Field(default="")
```

### 5. Settings 접근자 추가

`settings.py`에 expression 설정 접근자 추가:
```python
def get_expression_config() -> Dict[str, Any]:
    return _config_loader.get_section('expression') or {}

def get_expression_subtitle_styling() -> Dict[str, Any]:
    return _config_loader.get('expression', 'subtitle_styling', default={})
# ... 기타 접근자들
```

## Consequences

### 장점

1. **일관된 설정 관리**: 기존 `ConfigLoader` 패턴을 재사용하여 일관성 유지
2. **타입 안전성**: Dataclass를 통한 타입 안전한 설정 관리
3. **확장성**: 새로운 설정 섹션을 쉽게 추가할 수 있는 구조
4. **검증**: Pydantic 모델을 통한 데이터 검증
5. **마이그레이션**: Alembic을 통한 안전한 스키마 변경

### 단점

1. **복잡성 증가**: 설정 구조가 복잡해짐
2. **학습 곡선**: 새로운 개발자가 설정 구조를 이해하는데 시간 필요
3. **마이그레이션 위험**: 데이터베이스 스키마 변경으로 인한 잠재적 위험

### 위험 완화

1. **단계적 구현**: Phase 1에서 Configuration만 구현하여 위험 최소화
2. **테스트 커버리지**: 단위/통합 테스트로 안정성 보장
3. **백워드 호환성**: 기존 설정과의 호환성 유지
4. **문서화**: ADR과 User Manual을 통한 명확한 문서화

## Implementation Details

### 파일 구조
```
langflix/
├── config/
│   ├── expression_config.py      # 새로운 설정 클래스들
│   └── default.yaml              # 확장된 기본 설정
├── db/
│   ├── models.py                 # 확장된 Expression 모델
│   └── migrations/versions/
│       └── 0002_add_expression_fields.py
├── core/
│   └── models.py                 # 확장된 ExpressionAnalysis
└── settings.py                   # 새로운 접근자들
```

### 테스트 구조
```
tests/
├── unit/
│   └── test_expression_config.py
└── integration/
    └── test_expression_db_migration.py
```

### 문서화
```
docs/
├── adr/
│   └── ADR-013-expression-configuration-architecture.md
├── en/
│   └── USER_MANUAL.md            # 영문 사용자 매뉴얼
└── ko/
    └── USER_MANUAL_KOR.md        # 한글 사용자 매뉴얼
```

## Alternatives Considered

### 1. 별도 설정 파일
- **장점**: 기존 설정과 분리
- **단점**: 설정 관리 복잡성 증가, 일관성 부족

### 2. 환경 변수만 사용
- **장점**: 간단한 설정
- **단점**: 복잡한 구조화된 설정 불가능

### 3. JSON 설정
- **장점**: 프로그래밍 언어 독립적
- **단점**: YAML 대비 가독성 부족, 주석 지원 부족

## References

- [north-start-doc.md](../north-start-doc.md) - 전체 개발 계획
- [ConfigLoader 패턴](../langflix/config/config_loader.py) - 기존 설정 시스템
- [SQLAlchemy ORM](../langflix/db/models.py) - 데이터베이스 모델
- [Pydantic 모델](../langflix/core/models.py) - LLM 출력 모델