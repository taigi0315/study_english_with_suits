# 비디오 파이프라인 최적화 계획
최종 업데이트: 2025-11-14  
작성자: GPT-5 Codex (Solution Architect)

## 개요
- LangFlix는 동일한 원본 영상에서 컨텍스트, 교육용, 쇼트폼 영상을 모두 생성합니다.
- 각 산출물이 여러 번의 FFmpeg 호출, 무거운 디스크 I/O, 반복적인 프로빙을 유발하여 단일 호스트 환경에서 총 처리 시간이 길어집니다.
- 본 문서는 현재 워크플로를 요약하고, 핵심 병목을 식별하며, 출력 품질을 유지한 채 처리 시간을 단축하기 위한 최적화 로드맵을 제시합니다.
- 범위: 수평 확장이 불가능한 CPU 기반 단일 서버, 기존 Python/FFmpeg 툴체인 내부의 결정적 성능 개선에 집중합니다.

## 현재 워크플로 요약
1. `LangFlixPipeline.run()`이 자막 파싱, 표현 분석, 그룹화, 미디어 생성을 순차적으로 오케스트레이션합니다.
2. `_process_expressions()`는 그룹별 컨텍스트 클립을 추출하고, 표현별 자막 파일을 생성하며, 이후 단계를 위해 컨텍스트 클립을 디스크에 캐시합니다.
3. `_create_educational_videos()`는 캐시된 컨텍스트 클립을 재사용하여 표현 반복, 슬라이드 오버레이, 롱폼 영상을 조립합니다.
4. `_create_short_videos()`는 레이아웃만 다른 유사한 절차로 쇼트폼 영상을 만듭니다.
5. `ExpressionMediaSlicer`는 외부 호출(API 일괄 슬라이싱 등) 시 원본 영상을 비동기로 분할합니다.

그룹 루프와 그룹별 클립 추출 방식을 보여주는 핵심 코드 일부:

```615:704:langflix/main.py
    def _process_expressions(self):
        """Process each expression group (shared context clip + individual subtitles)"""
        from langflix.utils.temp_file_manager import get_temp_manager
        temp_manager = get_temp_manager()
        ...
        context_clip_cache: Dict[str, Path] = {}
        
        for group_idx, expression_group in enumerate(self.expression_groups):
            ...
            success = self.video_processor.extract_clip(
                video_file,
                expression_group.context_start_time,
                expression_group.context_end_time,
                video_output
            )
            ...
            for expr_idx, expression in enumerate(expression_group.expressions):
                subtitle_success = self.subtitle_processor.create_dual_language_subtitle_file(
                    expression,
                    str(subtitle_output)
                )
```

## 확인된 병목 지점

- **매 표현마다 반복되는 재인코딩**  
  `VideoProcessor.extract_clip()`은 항상 `libx264` + `aac`로 재인코딩합니다. 단순 슬라이싱이나 이후 단계에서 다시 인코딩할 예정인 경우에도 동일하게 동작하여 불필요한 비용이 발생합니다.

  ```185:193:langflix/core/video_processor.py
            ffmpeg
            .input(str(video_path), ss=start_seconds, t=duration)
            .output(
                str(output_path),
                vcodec='libx264',
                acodec='aac',
                preset='fast',
                crf=23,
                avoid_negative_ts='make_zero'
            )
            .overwrite_output()
            .run(quiet=True)
  ```

- **캐시 없는 과도한 FFprobe 호출**  
  `get_duration_seconds()`와 같은 헬퍼가 호출될 때마다 새 `ffprobe` 프로세스를 띄웁니다. `_create_educational_videos()`와 스택 유틸리티 내에서 표현마다 여러 번 호출되어 누적 비용이 큽니다.

  ```228:236:langflix/media/ffmpeg_utils.py
  def get_duration_seconds(path: str) -> float:
      try:
          probe = run_ffprobe(path)
          dur = probe.get("format", {}).get("duration")
          if dur is None:
              return 0.0
          return float(dur)
      except Exception:
          return 0.0
  ```

- **반복 구간 생성 시 매번 임시 파일 작성**  
  `repeat_av_demuxer()`는 매 표현마다 concat 리스트 파일을 디스크에 작성하고 전체 인코딩을 수행하여 불필요한 디스크 부하가 발생합니다.

  ```587:639:langflix/media/ffmpeg_utils.py
  def repeat_av_demuxer(input_path: str, repeat_count: int, out_path: Path | str) -> None:
      repeat_count = max(1, int(repeat_count))
      ...
      with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
          f.write(concat_content)
          concat_file = f.name
      try:
          (
              ffmpeg
              .input(concat_file, format='concat', safe=0)
              .output(
                  str(out_path),
                  **make_video_encode_args_from_source(input_path),
                  **make_audio_encode_args_copy()
              )
              .overwrite_output()
              .run(capture_stdout=True, capture_stderr=True)
          )
      finally:
          if os.path.exists(concat_file):
              os.unlink(concat_file)
  ```

- **병렬 슬라이서 버그 및 자원 제어 부재**  
  `slice_multiple_expressions()`가 매개변수 대신 `aligned_expressions`를 참조하고, `asyncio.gather`가 제한 없이 FFmpeg 작업을 동시에 실행하여 자원 고갈 위험이 있습니다.

  ```170:201:langflix/media/expression_slicer.py
  async def slice_multiple_expressions(..., expressions: List[dict], ...):
      tasks = []
      for expression in aligned_expressions:
          task = self.slice_expression(media_path, expression, media_id)
          tasks.append(task)
      results = await asyncio.gather(*tasks, return_exceptions=True)
  ```

- **중간 산출물 난립**  
  `_create_educational_videos()` 및 쇼트폼 생성 과정은 최종 산출물을 만들기 전에 여러 개의 임시 MKV 파일을 생성하여 디스크 I/O와 캐시 무효화 비용을 키웁니다.

## 최적화 전략

### Phase 0 – 관측 기반 마련
1. 파이프라인 주요 단계(`_process_expressions`, `_create_educational_videos`, `_create_short_videos`)에 `time.perf_counter()` 기반 구간 측정과 구조화 로그를 추가합니다.
2. CLI/API에 `--profile` 플래그를 도입하여 JSON 형태의 단계별 소요 시간, FFmpeg 호출 수를 기록합니다.
3. 대표 입력으로 파이프라인을 실행하고 베이스라인을 저장하는 경량 프로파일러(`tools/profile_video_pipeline.py`)를 제공합니다.

### Phase 1 – 저위험 효율 개선
1. **FFprobe 캐싱**: `ffmpeg_utils.run_ffprobe`에 절대 경로 + mtime을 키로 하는 LRU 캐시를 추가하여 중복 프로브를 제거합니다.
2. **적응형 클립 추출**: `VideoProcessor.extract_clip`이 키프레임 근접 여부와 후속 필터 필요성에 따라 스트림 복사(`-c copy`) 또는 재인코딩을 선택하도록 개선합니다.
3. **제어된 동시성**: `aligned_expressions` 오타를 수정하고, `asyncio.Semaphore(cpu_count // 2 or 1)`를 도입하여 FFmpeg 작업 동시 실행 수를 제한합니다.
4. **임시 파일 재사용**: concat 리스트 파일을 메모리(StringIO)로 처리하거나 프로세스 단위로 재사용하여 temp 파일 생성 비용을 줄입니다.
5. **FFmpeg 프리셋 정렬**: 단계별 인코딩 프리셋/CRF를 설정값과 일치시키고 숨겨진 느린 기본값을 제거합니다.

### Phase 2 – 구조적 변경
1. **배치 트리밍**: 단일 FFmpeg `-filter_complex`로 모든 표현 구간을 한 번에 잘라내는 `build_trim_plan(expressions)` 헬퍼를 구현하여 원본 파일의 반복 디코딩을 없앱니다.
2. **그래프 기반 조립**: 컨텍스트 추출, 자막 오버레이, 반복, hstack을 그룹당 한 번의 FFmpeg 호출로 통합하여 여러 차례의 인코드/디코드 사이클을 제거합니다.
3. **공유 자산 캐시**: 컨텍스트+자막 영상과 슬라이드(TTS 포함)를 롱폼/쇼트폼 생성이 공유하도록 메모이즈합니다.
4. **단계형 파이프라인 컨트롤러**: 작업 DAG를 사용해 디스크 I/O가 적은 작업(자막 생성, TTS)을 FFmpeg 대기 시간과 겹치되 자원 한계를 넘지 않도록 조율합니다.

### Phase 3 – 고급 개선
1. **순차 스트리밍 출력**: 네임드 파이프 또는 `ffmpeg -f segment`를 이용해 최종 결과를 직접 대상 스토리지로 스트리밍해 중간 파일을 줄입니다.
2. **하드웨어 가속 후크**: 가용 시 `vaapi`/`nvenc`를 사용할 수 있도록 구성 옵션을 제공하되 기본 경로는 유지합니다.
3. **품질 보증 게이팅**: 새로운 경로가 시각적 품질을 유지하는지 확인하기 위해 일부 표현에 대해 SSIM/PSNR 샘플링을 추가합니다.

## 구현 로드맵
| Phase | 주요 작업 | 선행 조건 | 기대 효과 |
| --- | --- | --- | --- |
| 0 | 계측 추가, 프로파일링 CLI, 베이스라인 실행 | 없음 | 기준 지표 확보 |
| 1A | ffprobe 캐시 데코레이터, 무효화 노출 | Phase 0 | 프로브 오버헤드 30~40% 감소 |
| 1B | `extract_clip` 복사/인코딩 모드 및 테스트 | 0 | 키프레임 활용 시 슬라이스 시간 단축 |
| 1C | 슬라이서 버그 수정, 세마포어 적용 | 0 | 배치 슬라이싱 안정화 |
| 2A | 배치 트리밍 플래너 + 단위 테스트 | 1B | 반복 디코딩 제거 |
| 2B | 그룹당 단일 필터 그래프 조립 | 2A | 전체 시간 35~45% 감소 |
| 3 | 스트리밍 출력, HW 가속 후크 (선택) | 2B | 향후 확장성 확보 |

### 공통 고려 사항
- 신규 설정 항목(최대 동시 FFmpeg 작업 수, 복사 모드 임계값, 프로브 캐시 TTL)을 설정 스키마에 반영합니다.
- 구현 이후 `docs/media`, `docs/services` 문서를 업데이트합니다.
- 기능 플래그 뒤에 신규 경로를 배치하고, 전환 전에 자동화 테스트로 구 버전/신 버전을 모두 검증합니다.

## 테스트 계획 (전후 시간 비교)

### 목표
- 각 최적화 단계 전후의 전체 파이프라인 시간과 단계별 소요 시간을 정량화합니다.
- 출력 일관성(재생 길이, 해상도, 코덱, 반복 실행 시 체크섬)을 검증합니다.
- 최적화가 안정성을 해치지 않는지 CPU 사용률, 디스크 I/O 대기 등 자원 지표를 확인합니다.

### 도구
1. **프로파일링 스크립트:** `tools/profile_video_pipeline.py`  
   - 입력 영상/자막, 출력 디렉터리, 프로파일 모드(`--profile`)를 받아 실행합니다.  
   - 단계별 시간, FFmpeg 호출 횟수, 평균 인코딩 시간, 캐시 히트율이 포함된 JSON 보고서를 출력합니다.
2. **지표 수집기:** `--emit-metrics <path>` 옵션을 추가하여 Prometheus 노출 형식 또는 CSV로 기록합니다.
3. **로그 확장:** `PROFILE_STAGE` 구조화 로그에 단계 이름, 소요 시간, 호출 횟수를 남깁니다.

### 테스트 데이터
- 대표 콘텐츠: 표현 30개 내외의 20~25분 분량 에피소드(기존 QA 자산).
- 보조 샘플: 5분 길이의 짧은 영상으로 소형 워크로드를 검증합니다.

### 절차
1. 현재 메인 브랜치 상태에서 프로파일링을 활성화한 베이스라인을 실행하고 JSON, 시스템 지표(`pidstat`/`iostat`)를 `profiles/baseline/`에 저장합니다.
2. Phase 1 변경 후 동일한 명령을 `profiles/phase1/`에 저장하고 비교합니다(목표: FFprobe 호출 ≥20% 감소, 총 시간 ≤10% 개선).
3. Phase 2 변경 후 반복 실행하여 총 시간 ≥30% 감소, 출력 길이 편차 ≤5%를 검증합니다.
4. 매 실행 이후 자동 회귀 테스트를 실행해 기능적인 회귀가 없는지 확인합니다.

### 추적 지표
- 전체 실행 시간.
- 단계별 소요 시간(파싱, 그룹화, 컨텍스트 추출, 교육용 조립, 쇼트 생성).
- 단계별 FFmpeg 호출 수 및 평균 지속 시간.
- FFprobe 캐시 히트율.
- 실행당 디스크 쓰기량(`psutil` 또는 `iostat`).

### 성공 기준
- Phase 1: 출력 변동 없이 전체 시간 ≥10% 감소.
- Phase 2: 전체 시간 ≥35% 감소, 결정적 구간에서 영상/오디오 체크섬 일치, 실패율 증가 없음.
- Phase 3(선택): 옵트인 기능 제공, 기본 경로 회귀 없음.

## 리스크 및 대응
- **복잡한 FFmpeg 그래프의 실패 가능성 증가** → 단계별 테스트를 구축하고, 안정화 전까지 기존 경로를 기능 플래그로 유지합니다.
- **캐시 정합성 문제** → (경로, mtime, size) 튜플을 캐시 키로 사용하고 불일치 시 즉시 실시간 프로브로 회귀합니다.
- **동시성 과잉** → CPU 수 기반 세마포어로 제한하고, 설정으로 조정 가능하게 합니다.
- **출력 드리프트(타이밍/자막)** → 신규 경로를 기본값으로 전환하기 전에 타임스탬프와 자막을 비교하는 자동 검증을 추가합니다.

## 다음 단계
1. 로드맵 항목별 티켓을 생성하고 본 문서를 참조로 연결합니다.
2. 코드가 변하기 전에 Phase 0 계측을 구현하여 베이스라인을 확보합니다.
3. Phase 1 개선을 단계적으로 적용하고, 변경 후마다 프로파일링을 반복합니다.
4. 결과를 리뷰하고 잔존 병목이 발견되면 Phase 2 설계를 조정합니다.


