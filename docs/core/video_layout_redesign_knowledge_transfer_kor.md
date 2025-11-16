# 비디오 레이아웃 리디자인 - 지식 전달 문서

**날짜**: 2025-01-XX  
**브랜치**: `feature/TICKET-038-039-040-video-layout-redesign`  
**상태**: 진행 중 (자막 동기화 이슈 해결 중)

---

## 요약

이 문서는 비디오 레이아웃 리디자인 프로젝트에 대한 포괄적인 지식 전달을 제공합니다:
- **TICKET-038**: 롱폼 순차 레이아웃 (전체 화면 비디오 → 전환 → 슬라이드)
- **TICKET-039**: 숏폼 중앙 정렬 비디오 (레터박싱 포함)
- **TICKET-040**: 이중 자막 레이어 (하단 원본 + 상단 표현)

**현재 상태**: 핵심 기능 구현 완료, 자막 동기화 이슈 지속적으로 해결 중

---

## 1. 프로젝트 목표

### 1.1 롱폼 비디오 레이아웃 (TICKET-038)

**목표**: 나란히 배치 레이아웃에서 순차 전체 화면 레이아웃으로 변경

**이전**:
- 나란히 배치: `[비디오 | 교육 슬라이드]` (동시에 보임)
- 레이아웃: `hstack` (수평 스택)

**이후**:
- 순차: `비디오 (전체 화면) → 전환 → 교육 슬라이드 (전체 화면)`
- 레이아웃: 전환 비디오를 포함한 순차 연결
- 비디오는 원본 비율 유지, 전체 화면
- 교육 슬라이드는 전환 후 전체 화면

**주요 변경사항**:
- `hstack_keep_height()`를 순차 `concat_filter_with_explicit_map()`로 교체
- 전환 비디오 생성 추가 (`_create_transition_video()`)
- 전환은 설정된 이미지와 사운드 효과 사용

### 1.2 숏폼 비디오 레이아웃 (TICKET-039)

**목표**: 상하 배치에서 중앙 정렬 비디오(레터박싱)로 변경

**이전**:
- 상하 배치: `[비디오 | 교육 슬라이드]` (동시에 보임)
- 레이아웃: `vstack` (수직 스택)

**이후**:
- 중앙 정렬 비디오: 화면 중앙의 비디오 (수직 비율) 레터박싱 포함
- 순차: `비디오 (중앙) → 전환 → 교육 슬라이드 (전체 화면)`
- 비디오는 원본 비율 유지, 검은 막대(레터박싱)로 중앙 정렬
- 교육 슬라이드는 전환 후 전체 화면

**주요 변경사항**:
- `vstack_keep_width()`를 `center_video_with_letterbox()`로 교체
- 전환을 포함한 순차 연결 추가
- 레터박싱으로 원본 비디오 비율 보존

### 1.3 이중 자막 레이어 (TICKET-040)

**목표**: 원본 자막에 추가로 상단에 표현 자막 오버레이(노란색) 추가

**이전**:
- 하단 원본 자막만 (이중 언어: 영어 + 한국어)

**이후**:
- 하단 원본 자막 (변경 없음)
- 상단 표현 자막 (노란색, 굵게) 표현 세그먼트 동안만 표시
- 표현 자막은 컨텍스트 비디오의 표현 세그먼트 동안만 표시

**주요 변경사항**:
- `SubtitleProcessor`에 `generate_expression_subtitle_srt()` 추가
- `subtitle/overlay.py`에 `apply_dual_subtitle_layers()` 추가
- 표현 자막 ASS 스타일: `Alignment=8` (상단 중앙), `MarginV=50` (상단에서 50px)

---

## 2. 구현 세부사항

### 2.1 롱폼 순차 레이아웃

**파일**: `langflix/core/video_editor.py`  
**메서드**: `create_educational_sequence()`  
**라인**: ~333-450

**프로세스**:
1. 컨텍스트 비디오에서 표현 클립 추출 (자막 포함)
2. 표현 클립 반복 (설정된 반복 횟수)
3. 왼쪽 측면 생성: 컨텍스트 비디오 → 표현 반복 (컨텍스트 건너뛰기 안 함)
4. 전환 비디오 생성 (1초, 이미지 및 사운드 효과 포함)
5. 표현 오디오로 교육 슬라이드 생성 (TTS 아님)
6. 순차 연결: 왼쪽 측면 → 전환 → 슬라이드

**핵심 코드**:
```python
# 순차 연결 (hstack 대체)
concat_filter_with_explicit_map(
    str(left_side_path),
    str(transition_video),
    str(temp_video_transition)
)
concat_filter_with_explicit_map(
    str(temp_video_transition),
    str(educational_slide),
    str(sequential_temp_path)
)
```

### 2.2 숏폼 중앙 정렬 비디오

**파일**: `langflix/core/video_editor.py`  
**메서드**: `create_short_format_video()`  
**라인**: ~635-750

**프로세스**:
1. 컨텍스트 + 표현 반복 추출 및 연결
2. 레터박싱으로 비디오 중앙 정렬 (원본 비율 유지)
3. 전환 비디오 생성
4. 교육 슬라이드 생성
5. 순차 연결: 레터박싱 비디오 → 전환 → 슬라이드

**핵심 코드**:
```python
# 레터박싱으로 비디오 중앙 정렬 (vstack 대체)
center_video_with_letterbox(
    str(concatenated_video_path),
    target_width=1080,
    target_height=1920,
    out_path=str(letterboxed_video_path)
)
```

**레터박싱 함수**: `langflix/media/ffmpeg_utils.py::center_video_with_letterbox()`
- 대상 해상도에 맞게 스케일링 계산
- 비디오를 너비 또는 높이에 맞게 스케일 (더 작은 쪽)
- 비디오 중앙에 검은 패딩(레터박싱) 추가
- 결과: 상하 또는 좌우에 검은 막대가 있는 중앙 정렬 비디오

### 2.3 이중 자막 레이어

**파일**: `langflix/core/video_editor.py`  
**메서드**: `_add_subtitles_to_context()`  
**라인**: ~1273-1375

**프로세스**:
1. 표현 자막 SRT 생성 (표현 세그먼트만)
2. 이중 자막 레이어 적용:
   - 하단 원본 자막 (기존)
   - 상단 표현 자막 (노란색, 굵게)

**핵심 코드**:
```python
# 표현 자막 SRT 생성
expression_subtitle_content = self.subtitle_processor.generate_expression_subtitle_srt(
    expression,
    expression_start_relative,  # 컨텍스트에서 표현 시작 시점
    expression_end_relative     # 컨텍스트에서 표현 종료 시점
)

# 이중 자막 레이어 적용
subs_overlay.apply_dual_subtitle_layers(
    str(video_path),
    str(temp_sub),  # 원본 자막 파일
    str(expression_subtitle_path),  # 표현 자막 파일
    str(output_path),
    expression_start_relative,
    expression_end_relative
)
```

**자막 스타일**:
- 표현: `Alignment=8` (상단 중앙), `MarginV=50` (상단에서 50px), 노란색 (`#FFFF00`), 굵게
- 원본: `Alignment=2` (하단 중앙), 흰색, 일반 굵기

---

## 3. 주요 이슈 및 해결책

### 3.1 자막 동기화 (진행 중 이슈)

**문제**: 컨텍스트 비디오에서 표현 클립을 추출할 때 자막이 동기화되지 않음

**근본 원인**:
- 컨텍스트 비디오에 자막이 이미 비디오 스트림에 렌더링됨
- 표현 클립 추출 시 자막 타임스탬프와 정확히 일치해야 함
- `trim` 필터는 프레임 단위로 작동하여 타임스탬프와 정렬되지 않음

**구현된 해결책**:
- **Output seeking 사용** (`ss`/`t` in output) - `trim` 필터 대신
- Output seeking은 전체 비디오를 디코딩하고 정확한 타임스탬프로 이동
- 두 단계 프로세스:
  1. Output seeking으로 클립 추출 (`ss`/`t` in output)
  2. `setpts` 필터로 타임스탬프 리셋 (반복 클립에 필요)

**핵심 코드** (현재 구현):
```python
# 1단계: Output seeking으로 추출 (정확한 타임스탬프 기반 추출)
ffmpeg.output(
    video_stream,
    audio_stream,
    str(expression_video_clip_path),
    ss=relative_start,  # Output seeking: input 후에 적용하여 정확도 향상
    t=expression_duration
)

# 2단계: 타임스탬프 리셋 (반복 클립에 필요)
reset_input = ffmpeg.input(str(expression_video_clip_path))
reset_video = ffmpeg.filter(reset_input['v'], 'setpts', 'PTS-STARTPTS')
reset_audio = ffmpeg.filter(reset_input['a'], 'asetpts', 'PTS-STARTPTS')
```

**왜 두 단계인가?**:
- Output seeking은 먼저 실행되어야 자막 동기화 정확도 확보
- 타임스탬프 리셋은 추출 후 실행되어야 반복 클립이 작동
- 단일 단계로 결합하면 자막 동기화가 깨짐

**참고**: `langflix/media/expression_slicer.py`도 동일한 접근 방식 사용 (output seeking)

**상태**: ⚠️ **진행 중** - 여전히 동기화 이슈 발생, 추가 개선 필요

### 3.2 표현 자막 위치

**문제**: 표현 자막이 잘못된 위치에 표시됨 (상단 중앙이 아님)

**해결책**:
- 표현 자막 스타일에 `MarginV=50` 추가
- `MarginV`는 정렬 위치에서 수직 여백 제어
- `Alignment=8` (상단 중앙)의 경우, `MarginV=50`은 상단 가장자리에서 50픽셀 의미

**핵심 코드**:
```python
expression_style = (
    "Alignment=8,"  # 상단 중앙
    "PrimaryColour=&H00FFFF00,"  # 노란색
    "MarginV=50"  # 상단 가장자리에서 50픽셀
)
```

**상태**: ✅ **해결됨**

### 3.3 표현 오디오 불일치

**문제**: 교육 슬라이드 재생 중 표현 오디오가 표현과 일치하지 않음

**근본 원인**:
- 컨텍스트에서 추출한 클립에서 오디오를 추출함
- 컨텍스트에서 추출한 클립에 타이밍 문제가 있을 수 있음

**해결책**:
- 원본 `expression_video_path`에서 오디오 추출 (컨텍스트에서 추출한 클립 아님)
- 정확한 추출을 위해 표현 타임스탬프 (`expression_start_time`, `expression_end_time`) 사용
- 정확한 오디오 추출을 위해 output seeking 사용

**핵심 코드**:
```python
# 표현 타임스탬프를 사용하여 원본 표현 비디오에서 오디오 추출
expression_start_seconds = self._time_to_seconds(expression.expression_start_time)
expression_end_seconds = self._time_to_seconds(expression.expression_end_time)
expression_audio_duration = expression_end_seconds - expression_start_seconds

audio_input = ffmpeg.input(str(original_video_path))
audio_stream = audio_input['a']

ffmpeg.output(
    audio_stream,
    str(output_path),
    ss=expression_start_seconds,  # Output seeking
    t=expression_audio_duration
)
```

**상태**: ✅ **해결됨** (로깅 개선 포함)

---

## 4. 주요 기술 개념

### 4.1 Output Seeking vs Input Seeking

**Input Seeking** (`-i` 앞에 `-ss`):
- 빠르지만 덜 정확함
- 가장 가까운 키프레임으로 이동
- 정확한 타임스탬프와 일치하지 않을 수 있음
- ❌ **자막 동기화에 부적합**

**Output Seeking** (`-i` 뒤에 `-ss`):
- 느리지만 더 정확함
- 전체 비디오를 디코딩하고 정확한 타임스탬프로 이동
- ✅ **자막 동기화에 필수**

**참고**: 자세한 설명은 `docs/core/subtitle_sync_guide_kor.md` 참조

### 4.2 자막 타임스탬프 계산

**컨텍스트 비디오**:
- 타임스탬프 0에서 시작
- 자막은 컨텍스트 시작(0)에 상대적인 타임스탬프를 가져야 함

**표현 클립 추출**:
- 표현은 컨텍스트 비디오에서 `relative_start` 초에 시작
- 표현은 컨텍스트 비디오에서 `relative_end` 초에 종료
- 표현 지속 시간: `relative_end - relative_start`

**표현 자막**:
- 컨텍스트 비디오의 표현 세그먼트 동안만 표시되어야 함
- 타임스탬프: `expression_start_relative` ~ `expression_end_relative` (컨텍스트 시작에 상대적)

### 4.3 전환 비디오 생성

**설정**: `langflix/config/default.yaml`
```yaml
context_to_slide_transition:
  enabled: true
  duration: 1.0  # 1초 전환
  image_path_16_9: "assets/transition_16_9.png"  # 롱폼용
  image_path_9_16: "assets/transition_9_16.png"  # 숏폼용
  sound_effect_path: "assets/sound_effect.mp3"
  sound_effect_volume: 0.5
```

**프로세스**:
1. 전환 이미지에서 비디오 생성 (대상 지속 시간)
2. 사운드 효과 추가 (설정된 경우)
3. 비디오 세그먼트와 연결

### 4.4 레터박싱

**목적**: 원본 비율을 유지하면서 수직 프레임에 비디오 중앙 정렬

**프로세스**:
1. 대상 해상도에 맞게 스케일링 계산
2. 비디오를 너비 또는 높이에 맞게 스케일 (더 작은 쪽)
3. 비디오 중앙에 검은 패딩(레터박싱) 추가
4. 결과: 상하 또는 좌우에 검은 막대가 있는 중앙 정렬 비디오

**함수**: `langflix/media/ffmpeg_utils.py::center_video_with_letterbox()`

---

## 5. 파일 구조

### 5.1 수정된 파일

**핵심 비디오 편집**:
- `langflix/core/video_editor.py`
  - `create_educational_sequence()` - 롱폼 순차 레이아웃
  - `create_short_format_video()` - 숏폼 중앙 레이아웃
  - `_add_subtitles_to_context()` - 이중 자막 레이어
  - `_create_educational_slide()` - 표현 오디오 추출

**자막 처리**:
- `langflix/core/subtitle_processor.py`
  - `generate_expression_subtitle_srt()` - 표현 전용 자막 생성

**자막 오버레이**:
- `langflix/subtitles/overlay.py`
  - `apply_dual_subtitle_layers()` - 이중 자막 레이어 적용

**FFmpeg 유틸리티**:
- `langflix/media/ffmpeg_utils.py`
  - `center_video_with_letterbox()` - 레터박싱 함수

**설정**:
- `langflix/config/default.yaml`
  - `context_to_slide_transition` - 전환 설정

**메인 파이프라인**:
- `langflix/main.py`
  - `subtitle_processor`와 함께 `VideoEditor` 초기화

### 5.2 새로운 함수

1. `center_video_with_letterbox()` - 숏폼 비디오용 레터박싱
2. `generate_expression_subtitle_srt()` - 표현 자막 SRT 생성
3. `apply_dual_subtitle_layers()` - 이중 자막 레이어 적용
4. `_create_transition_video()` - 전환 비디오 생성 (없는 경우)

---

## 6. 일반적인 함정 및 해결책

### 6.1 자막 동기화 이슈

**함정**: 표현 클립 추출에 `trim` 필터 사용
- **이유**: `trim`은 프레임 단위로 작동하여 정렬되지 않음
- **해결책**: Output seeking (`ss`/`t` in output) 사용

**함정**: Output seeking 전에 `setpts` 적용
- **이유**: Output seeking 정확도 손상
- **해결책**: 먼저 추출, 그 다음 타임스탬프 리셋

**함정**: Input seeking (`-i` 앞에 `-ss`) 사용
- **이유**: 가장 가까운 키프레임으로 이동, 정확한 타임스탬프 아님
- **해결책**: 자막 동기화에는 항상 output seeking 사용

### 6.2 표현 오디오 이슈

**함정**: 컨텍스트에서 추출한 클립에서 오디오 추출
- **이유**: 클립에 타이밍 문제가 있을 수 있음
- **해결책**: 표현 타임스탬프를 사용하여 원본 비디오에서 추출

**함정**: 오디오 추출에 output seeking 미사용
- **이유**: 잘못된 세그먼트 추출 가능
- **해결책**: Output seeking (`ss`/`t` in output) 사용

### 6.3 자막 위치 이슈

**함정**: `MarginV` 없이 `Alignment=8`만 사용
- **이유**: 자막이 최상단 가장자리에 나타날 수 있음
- **해결책**: 적절한 간격을 위해 `MarginV=50` 추가

---

## 7. 테스트 및 검증

### 7.1 수동 테스트 체크리스트

**롱폼 비디오**:
- [ ] 비디오가 전체 화면으로 재생됨 (나란히 배치 아님)
- [ ] 비디오와 슬라이드 사이에 전환 표시
- [ ] 교육 슬라이드가 전체 화면
- [ ] 슬라이드 재생 중 표현 오디오 재생
- [ ] 자막이 동기화됨

**숏폼 비디오**:
- [ ] 비디오가 레터박싱으로 중앙 정렬됨
- [ ] 원본 비율이 보존됨
- [ ] 비디오와 슬라이드 사이에 전환 표시
- [ ] 교육 슬라이드가 전체 화면
- [ ] 자막이 동기화됨

**이중 자막**:
- [ ] 원본 자막이 하단에 표시됨
- [ ] 표현 자막이 상단에 표시됨 (노란색, 굵게)
- [ ] 표현 자막은 표현 세그먼트 동안만 표시됨
- [ ] 두 자막 레이어가 동기화됨

### 7.2 자막 동기화 검증

**방법 1**: 시각적 검사
- 비디오를 재생하고 자막이 대화와 일치하는지 확인
- 표현 자막은 표현이 말해질 때 정확히 나타나야 함

**방법 2**: 자막 추출 및 비교
```bash
ffmpeg -i output.mkv -map 0:s:0 output.srt
# 원본 자막 파일과 타임스탬프 비교
```

**방법 3**: 표현 클립 추출 확인
- 표현 클립이 컨텍스트 비디오에서 올바른 시간에 시작하는지 확인
- 표현 클립의 자막이 표현 세그먼트와 일치하는지 확인

---

## 8. 알려진 이슈 및 제한사항

### 8.1 진행 중 이슈

**자막 동기화**:
- ⚠️ **상태**: 여전히 동기화 이슈 발생
- **영향**: 자막이 대화와 약간 어긋날 수 있음
- **임시 해결책**: 현재 없음
- **다음 단계**: 추가 조사 필요

### 8.2 성능 고려사항

**두 단계 인코딩**:
- 표현 클립 추출에는 두 단계 필요 (추출 + 타임스탬프 리셋)
- 이는 표현 클립의 인코딩 시간을 두 배로 늘림
- **트레이드오프**: 속도보다 정확도 (자막 동기화에 필요)

**Output Seeking**:
- Input seeking보다 느림 (전체 비디오 디코딩)
- **트레이드오프**: 속도보다 정확도 (자막 동기화에 필요)

### 8.3 제한사항

**전환 이미지**:
- 설정에서 제공되어야 함
- 롱폼(16:9)과 숏폼(9:16)에 다른 이미지
- 누락 시 전환 실패 가능

**레터박싱**:
- 항상 검은 막대 추가 (모든 비디오에 원하는 것은 아님)
- 비율은 보존되지만 비디오가 더 작게 보일 수 있음

---

## 9. 향후 개선사항

### 9.1 자막 동기화

**잠재적 해결책**:
1. 프레임 정확한 추출 방법 조사
2. 타임스탬프 조건과 함께 `select` 필터 고려
3. 자막 스트림 추출 및 재적용 탐색

### 9.2 성능 최적화

**잠재적 개선사항**:
1. 표현 클립 캐싱하여 재추출 방지
2. 두 단계 인코딩 최적화 (아마도 단계 결합)
3. 가능한 경우 하드웨어 가속 사용

### 9.3 설정

**잠재적 향상**:
1. 표현 자막 위치 설정 가능하게
2. 표현 자막 색상 설정 가능하게
3. 전환 애니메이션 옵션 추가

---

## 10. 참고 자료

### 10.1 문서

- `docs/core/subtitle_sync_guide_eng.md` - 자막 동기화 가이드
- `docs/core/subtitle_sync_guide_kor.md` - 자막 동기화 가이드 (한글)
- `tickets/review-required/TICKET-038-longform-sequential-layout.md`
- `tickets/review-required/TICKET-039-shortform-centered-letterbox.md`
- `tickets/review-required/TICKET-040-expression-subtitle-overlay.md`

### 10.2 코드 참고

- `langflix/core/video_editor.py` - 메인 비디오 편집 로직
- `langflix/media/expression_slicer.py` - 표현 슬라이싱 (output seeking 참고)
- `langflix/subtitles/overlay.py` - 자막 오버레이 함수
- `langflix/media/ffmpeg_utils.py` - FFmpeg 유틸리티 함수

### 10.3 외부 리소스

- [FFmpeg Seeking 문서](https://trac.ffmpeg.org/wiki/Seeking)
- [FFmpeg Filter 문서](https://ffmpeg.org/ffmpeg-filters.html)
- [ASS 자막 형식](https://github.com/libass/libass/wiki/ASS-Subtitle-Format)

---

## 11. 연락처 및 지원

**이슈의 경우**:
- 자막 동기화 문제 해결을 위해 `docs/core/subtitle_sync_guide_kor.md` 확인
- 최근 수정사항은 커밋 기록 검토
- FFmpeg 오류는 로그 확인

**질문의 경우**:
- 먼저 이 문서 검토
- `langflix/core/video_editor.py`의 코드 주석 확인
- `tickets/review-required/`의 티켓 문서 참조

---

**최종 업데이트**: 2025-01-XX  
**문서 버전**: 1.0  
**상태**: 활성 개발 중



