# ADR-015: 오디오 안정성과 원본 품질 유지를 위한 FFmpeg 파이프라인 표준화

## 상태
Accepted

## 배경
- concat/stack 단계 이후 간헐적으로 오디오가 사라지는 문제가 발생했습니다.
- 표현 반복(expression repeating) 세그먼트가 필터 기반 concat 후 오디오가 없어지는 현상 발생.
- 요구사항: 가능한 한 원본 비디오 포맷(코덱/해상도)을 유지하고, 중간 파이프라인에서는 오디오를 수정하지 않습니다.

## 결정
**1단계 (초기):**
- 명시적 스트림 매핑과 오디오 표준화를 보장하는 FFmpeg 유틸을 중앙집중화합니다.
- 필터가 적용되지 않는 구간은 비디오 스트림을 복사(stream copy)하고, 필터가 필요한 경우에만 재인코딩합니다.
- 입력 파라미터가 다를 경우 filter-concat(v=1,a=1)와 명시적 매핑을 사용합니다.
- concat/stack 경계에서 오디오를 ac=2, ar=48000으로 정규화합니다.
- 720p/1080p 같은 하드코딩된 스케일을 제거하고, 원본 해상도를 유지하며 필요 시 동적으로 스케일을 계산합니다.

**2단계 (오디오 드랍 수정 - TICKET-001):**
- **Demuxer 우선 접근**: 필터 기반 반복을 concat demuxer(`repeat_av_demuxer`)로 교체.
- **표준화된 레이아웃**: 
  - Long-form: hstack (왼쪽=AV, 오른쪽=slide), slide가 전체 시간 동안 표시
  - Short-form: vstack (위=AV, 아래=slide), slide가 전체 시간 동안 표시
- **별도 최종 gain 패스**: 오디오 볼륨 증가(+25%)를 filter_complex 내부가 아닌 별도 최종 단계로 적용.
- **중간 파이프라인 오디오 변환 없음**: 최종 gain 적용 전까지 오디오를 그대로 유지.
- **견고한 fallback**: Filter concat 실패 시 demuxer concat으로 자동 전환.
- **검증**: `tools/verify_media_pipeline.py`에 ffprobe 기반 체크를 추가하여 오디오 존재 확인.

**3단계 (Short-form 로직 단순화 - TICKET-001, 2025-01-30):**
- **문제**: Short-form이 불필요한 오디오 추출/처리 로직으로 인해 과도하게 복잡했고 (~180줄), A-V sync 문제를 발생시켰습니다.
- **근본 원인**: Short-form이 오디오를 별도로 추출하고 처리하며, 비디오 대신 오디오에서 duration을 계산했습니다.
- **해결책**: Short-form을 long-form 패턴과 완전히 동일하게 단순화:
  - 불필요한 오디오 추출/처리 로직 제거
  - 중복된 expression 처리 블록 제거
  - Duration 계산을 오디오 기반에서 비디오 기반으로 변경 (long-form과 동일)
  - 단순화된 흐름: context_with_subtitles → expression clip → repeat → concat → vstack → final gain
  - Short-form이 이제 long-form과 정확히 동일한 패턴을 따름 (유일한 차이: vstack vs hstack)
- **결과**: 0.5초 A-V sync 지연 문제 해결, 코드가 훨씬 간단하고 유지보수 가능해짐.
- **핵심 인사이트**: Short-form과 long-form은 동일한 로직을 사용해야 함 - 유일한 차이는 레이아웃 (수직 vs 수평).

## 결과
**긍정적:**
- 명시적 매핑, demuxer 우선 접근, 견고한 fallback으로 오디오 드랍 문제가 완화됩니다.
- 오디오 손실 없이 더 안정적인 표현 반복.
- 관심사 분리 명확화 (AV 빌드 → 레이아웃 → 최종 gain).
- `media/ffmpeg_utils.py`, `audio/timeline.py`, `subtitles/overlay.py`, `slides/generator.py` 도입으로 모듈화와 유지보수성이 향상됩니다.

**트레이드오프:**
- 필터로 인한 재인코딩이 필요한 경우 CPU 비용이 소폭 증가할 수 있습니다.
- 2-패스 최종화(비디오 레이아웃 + 오디오 gain)는 IO를 증가시키지만 안정성을 향상시킵니다.
- Demuxer concat은 균일한 파라미터를 필요로 하며, 그렇지 않으면 filter concat으로 fallback합니다.

## 구현 세부사항
### 주요 함수
- `repeat_av_demuxer()`: concat demuxer를 사용하여 AV 세그먼트를 안정적으로 반복.
- `concat_demuxer_if_uniform()`: 파라미터 프로빙과 함께 demuxer 기반 연결.
- `hstack_keep_height()`: Long-form 레이아웃용 수평 스택.
- `vstack_keep_width()`: Short-form 레이아웃용 수직 스택.
- 향상된 `concat_filter_with_explicit_map()`: 필터 실패 시 demuxer로 자동 fallback.

### 검증
`python tools/verify_media_pipeline.py`를 실행하여 다음 사항 확인:
1. Demuxer 기반 AV 반복이 오디오를 보존
2. 연결이 오디오를 유지
3. 스택이 오디오를 보존
4. 레이아웃이 spec과 일치 (hstack/vstack)
5. 오디오 파라미터가 유효함

## 참고
- `langflix/media/ffmpeg_utils.py` - 중앙집중화된 FFmpeg 유틸리티
- `langflix/core/video_editor.py` - 새로운 유틸을 사용하는 비디오 편집 파이프라인
- `tools/verify_media_pipeline.py` - 파이프라인 검증 스크립트
- `tests/integration/test_media_pipeline_audio.py` - 통합 테스트
- `docs/TROUBLESHOOTING_GUIDE.md`
