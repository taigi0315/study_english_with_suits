# 자막 동기화 가이드

## 개요

이 가이드는 LangFlix 파이프라인에서 정확한 동기화를 위해 비디오에 자막을 적용하는 올바른 방법을 설명합니다. 자막 동기화 문제는 비디오 처리 코드를 변경할 때 자주 발생하는 문제입니다.

## 핵심 원칙

### 1. Output Seeking vs Input Seeking

FFmpeg는 두 가지 유형의 seeking을 지원합니다:

- **Input Seeking** (`-i` 앞에 `-ss`): 빠르지만 덜 정확합니다. FFmpeg가 가장 가까운 키프레임으로 이동하므로 정확한 타임스탬프와 일치하지 않을 수 있습니다.
- **Output Seeking** (`-i` 뒤에 `-ss`): 느리지만 더 정확합니다. FFmpeg가 전체 비디오를 디코딩하고 정확한 타임스탬프로 이동합니다.

**자막 동기화를 위해서는 항상 output seeking을 사용하세요.**

### 2. 자막 동기화가 깨지는 이유

자막 동기화는 다음과 같은 경우에 깨질 수 있습니다:

1. **Output seeking 대신 input seeking 사용**: 비디오 클립을 추출할 때 `-i` 앞에 `-ss`를 사용하면 타이밍 불일치가 발생할 수 있습니다.
2. **타임스탬프 리셋 문제**: 클립을 추출할 때 `setpts` 필터를 사용하여 타임스탬프를 0부터 시작하도록 리셋해야 합니다.
3. **자막 파일 타임스탬프**: 자막 파일은 적용되는 비디오에 상대적인 타임스탬프를 가져야 합니다 (0부터 시작).

## 올바른 구현

### Context 비디오에서 Expression 클립 추출

Context 비디오에서 expression 클립을 추출할 때는 output seeking을 사용하세요:

```python
# ❌ 잘못된 방법: Input seeking (빠르지만 부정확)
input_stream = ffmpeg.input(str(context_with_subtitles), ss=relative_start, t=expression_duration)

# ✅ 올바른 방법: Output seeking (느리지만 정확)
input_stream = ffmpeg.input(str(context_with_subtitles))
# Input 후에 seeking 및 duration trimming 적용 (output seeking)
video_stream = ffmpeg.filter(input_stream['v'], 'setpts', 'PTS-STARTPTS')
audio_stream = ffmpeg.filter(input_stream['a'], 'asetpts', 'PTS-STARTPTS')

ffmpeg.output(
    video_stream,
    audio_stream,
    str(output_path),
    ss=relative_start,  # Output seeking: input 후에 적용하여 정확도 향상
    t=expression_duration  # Duration 제한
)
```

### Context 비디오에 자막 적용

Context 비디오에 자막을 적용할 때:

1. **자막 타임스탬프가 context 시작(0)에 상대적인지 확인**:
   - 자막 파일은 0부터 시작하는 타임스탬프를 가져야 합니다
   - 자막 파일이 원본 비디오에 상대적인 타임스탬프를 가지고 있다면, context 시작에 상대적으로 조정해야 합니다

2. **적절한 자막 오버레이 사용**:
   - 이중 자막(원본 + expression)의 경우 `apply_dual_subtitle_layers()` 사용
   - Expression 자막 타이밍이 context 비디오의 expression 세그먼트와 일치하는지 확인

### 원본 비디오에서 오디오 추출

교육용 슬라이드를 위해 원본 비디오에서 오디오를 추출할 때:

```python
# ✅ 올바른 방법: Expression 타임스탬프를 사용하여 output seeking으로 오디오 추출
expression_start_seconds = self._time_to_seconds(expression.expression_start_time)
expression_end_seconds = self._time_to_seconds(expression.expression_end_time)
expression_audio_duration = expression_end_seconds - expression_start_seconds

audio_input = ffmpeg.input(str(original_video_path))
audio_stream = audio_input['a']

ffmpeg.output(
    audio_stream,
    str(output_path),
    ss=expression_start_seconds,  # Output seeking: input 후에 적용하여 정확도 향상
    t=expression_audio_duration  # Duration 제한
)
```

## 코드 위치

### Expression 클립 추출

**파일**: `langflix/core/video_editor.py`  
**메서드**: `create_educational_sequence()`  
**라인**: ~179-208

```python
# 중요: 정확한 자막 동기화를 위해 output seeking 사용
input_stream = ffmpeg.input(str(context_with_subtitles))
video_stream = ffmpeg.filter(input_stream['v'], 'setpts', 'PTS-STARTPTS')
audio_stream = ffmpeg.filter(input_stream['a'], 'asetpts', 'PTS-STARTPTS')

ffmpeg.output(
    video_stream,
    audio_stream,
    str(expression_video_clip_path),
    ss=relative_start,  # Output seeking
    t=expression_duration
)
```

### Expression 오디오 추출

**파일**: `langflix/core/video_editor.py`  
**메서드**: `_create_educational_slide()`  
**라인**: ~1609-1649

```python
# Expression 타임스탬프를 사용하여 원본 expression 비디오에서 오디오 추출
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

### Expression Slicer

**파일**: `langflix/media/expression_slicer.py`  
**메서드**: `slice_expression()`  
**라인**: ~129-143

```python
# 중요: 정확한 seeking 및 자막 동기화를 위해 -ss를 -i 뒤에 배치
ffmpeg_cmd = [
    'ffmpeg',
    '-i', media_path,
    '-ss', str(start_time),  # 시작으로 이동 (정확도를 위한 output seeking)
    '-t', str(duration),  # Duration
    # ... 기타 옵션
]
```

## 피해야 할 일반적인 실수

### ❌ 자막 동기화에 Input Seeking 사용하지 않기

```python
# 잘못된 방법: Input seeking (자막 동기화 문제 발생)
input_stream = ffmpeg.input(str(video_path), ss=start_time, t=duration)
```

### ❌ 타임스탬프 리셋 잊지 않기

```python
# 잘못된 방법: 타임스탬프가 리셋되지 않음 (반복 클립에서 지연 발생)
video_stream = input_stream['v']
audio_stream = input_stream['a']
```

### ✅ 항상 Output Seeking과 타임스탬프 리셋 사용

```python
# 올바른 방법: 타임스탬프 리셋과 함께 output seeking 사용
input_stream = ffmpeg.input(str(video_path))
video_stream = ffmpeg.filter(input_stream['v'], 'setpts', 'PTS-STARTPTS')
audio_stream = ffmpeg.filter(input_stream['a'], 'asetpts', 'PTS-STARTPTS')

ffmpeg.output(
    video_stream,
    audio_stream,
    str(output_path),
    ss=start_time,  # Output seeking
    t=duration
)
```

## 자막 동기화 테스트

자막 동기화를 확인하려면:

1. **출력 비디오에서 자막 타이밍 확인**:
   ```bash
   ffprobe -v error -show_entries frame=pkt_pts_time -select_streams v:0 output.mkv
   ```

2. **출력 비디오에서 자막 추출**:
   ```bash
   ffmpeg -i output.mkv -map 0:s:0 output.srt
   ```

3. **원본 자막 파일과 비교**:
   - 텍스트 에디터에서 두 자막 파일 열기
   - 타임스탬프가 비디오 콘텐츠와 일치하는지 확인

## 참고 자료

- [FFmpeg Seeking 문서](https://trac.ffmpeg.org/wiki/Seeking)
- [FFmpeg Filter 문서](https://ffmpeg.org/ffmpeg-filters.html)
- `langflix/core/video_editor.py` - 메인 비디오 편집 로직
- `langflix/media/expression_slicer.py` - 적절한 seeking을 사용한 expression slicing
- `langflix/subtitles/overlay.py` - 자막 오버레이 함수

## 요약

**핵심 포인트**:

1. **자막 동기화를 위해 항상 output seeking 사용** (`-i` 뒤에 `-ss`)
2. **클립 추출 시 타임스탬프 리셋** `setpts` 필터 사용
3. **자막 타임스탬프 확인** 적용되는 비디오에 상대적(0부터 시작)
4. **원본 비디오에서 오디오 추출** output seeking으로 expression 타임스탬프 사용
5. **비디오 처리 코드 변경 후 자막 동기화 테스트**

의심스러울 때는 속도보다 정확도를 선택하세요. 자막 동기화 문제는 느린 처리 시간보다 디버깅하기 어렵습니다.






