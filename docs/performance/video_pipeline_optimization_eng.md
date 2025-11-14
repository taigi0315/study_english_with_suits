# Video Pipeline Optimization Plan
Last Updated: 2025-11-14  
Author: GPT-5 Codex (Solution Architect)

## Overview
- LangFlix currently generates multiple deliverables (context, educational, short-form videos) from the same source footage.
- Each deliverable triggers several FFmpeg invocations, heavy disk I/O, and repeated probing, which stretch total turnaround time on a fixed-resource box.
- This document summarizes the present workflow, pinpoints the dominant hotspots, and proposes an optimization roadmap that preserves output fidelity while lowering wall-clock time.
- Scope: CPU-only single-host deployments (no horizontal scaling), focusing on deterministic performance wins inside the existing Python/FFmpeg toolchain.

## Current Workflow Snapshot
1. `LangFlixPipeline.run()` orchestrates subtitle parsing, expression analysis, grouping, and media production.
2. `_process_expressions()` extracts context clips per group, then generates per-expression subtitle files and caches context clips on disk for later stages.
3. `_create_educational_videos()` replays the cached context clips, repeats expressions, overlays slides, and assembles long-form videos.
4. `_create_short_videos()` repeats similar steps with a different layout to produce short-form outputs.
5. `ExpressionMediaSlicer` slices raw footage asynchronously when invoked externally (e.g., API batch slicing).

Key excerpt illustrating the sequential group loop and per-group clip extraction:

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

## Observed Bottlenecks

- **Repeated re-encoding for every context slice**  
  `VideoProcessor.extract_clip()` always re-encodes with `libx264` + `aac`, even when we only need a direct copy or when downstream filters will re-encode again.

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

- **Excessive FFprobe usage without caching**  
  Helpers like `get_duration_seconds()` spawn `ffprobe` on every call. Within `_create_educational_videos()` and stacking utilities this gets invoked multiple times per expression.

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

- **Concat repeat path writes temp files for every expression**  
  `repeat_av_demuxer()` builds a concat list file on disk and launches a full encode pass for each repetition, introducing avoidable disk churn.

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

- **Parallel slicer has a latent NameError and no concurrency control**  
  `slice_multiple_expressions()` references `aligned_expressions` instead of the `expressions` parameter, and the naive gather spawns unlimited FFmpeg jobs, risking resource thrash.

  ```170:201:langflix/media/expression_slicer.py
  async def slice_multiple_expressions(..., expressions: List[dict], ...):
      tasks = []
      for expression in aligned_expressions:
          task = self.slice_expression(media_path, expression, media_id)
          tasks.append(task)
      results = await asyncio.gather(*tasks, return_exceptions=True)
  ```

- **Intermediate artifacts proliferate**  
  `_create_educational_videos()` and short-form routines emit multiple temp MKV files before the final long-form output, amplifying disk I/O pressure and cache invalidation churn.

## Optimization Strategy

### Phase 0 – Observability Foundation
1. Instrument pipeline stages (`_process_expressions`, `_create_educational_videos`, `_create_short_videos`) with `time.perf_counter()` spans and structured logging.
2. Add an optional `--profile` flag (CLI/API) that writes a JSON trace (stage timings, per-expression durations, FFmpeg command counts).
3. Provide a lightweight profiler script (`tools/profile_video_pipeline.py`) to run the pipeline on representative input and persist baselines.

### Phase 1 – Low-Risk Efficiency Gains
1. **FFprobe caching:** introduce an LRU cache in `ffmpeg_utils.run_ffprobe` keyed by absolute path + mtime to eliminate redundant probes.
2. **Adaptive clip extraction:** allow `VideoProcessor.extract_clip` to choose between stream-copy (`-c copy`) and encode based on keyframe proximity and downstream filter requirements. For pure slicing (no filters) we can combine `-ss` before `-i` with `-c copy`.
3. **Controlled concurrency:** fix the `aligned_expressions` typo, wrap `asyncio.Semaphore(cpu_count // 2 or 1)` around FFmpeg jobs, and surface batch size tuning through settings.
4. **Temp reuse:** pool concat list files in memory (StringIO) or reuse a shared file per process to avoid hot-temp-file churn.
5. **FFmpeg preset alignment:** align per-stage presets with user-configured quality targets so that repeated encodes reuse consistent `preset`/`crf` (no hidden slow defaults).

### Phase 2 – Structural Changes
1. **Batch trimming:** build a `build_trim_plan(expressions)` helper that emits a single FFmpeg `-filter_complex` graph to trim all expression ranges in one pass, writing them to named pipes or temporary outputs without reopening the source file repeatedly.
2. **Graph-driven assembly:** merge context extraction, subtitle overlay, repetition, and hstack operations into a single FFmpeg invocation per group using complex filter chains (`split`, `trim`, `concat`, `overlay`, `hstack`). This removes several encode–decode cycles.
3. **Shared asset cache:** memoize context-with-subtitles outputs and slides (PNG/TTS combos) across both long-form and short-form builders to prevent duplicative slide regeneration.
4. **Staged pipeline controller:** orchestrate phases via a task DAG so that IO-heavy tasks (subtitle generation, audio TTS) overlap with encode waits without exceeding resource caps.

### Phase 3 – Advanced Enhancements
1. **Incremental output mode:** stream final outputs directly to target storage (via named pipes or `ffmpeg` `-f segment`) to reduce intermediate disk writes.
2. **Optional HW accel hooks:** expose configuration for `vaapi`/`nvenc` when hardware is available without making it a baseline requirement.
3. **Quality-assurance gating:** integrate SSIM/PSNR sampling on a subset of expressions to ensure the new path maintains visual fidelity.

## Implementation Roadmap
| Phase | Key Tasks | Dependencies | Expected Impact |
| --- | --- | --- | --- |
| 0 | Instrument stages, add profiling CLI, baseline run | None | Ground truth metrics |
| 1A | Add ffprobe cache decorator, expose cache invalidation | Phase 0 instrumentation | Reduces probe overhead by ~30-40% |
| 1B | Update `extract_clip` to support copy/encode modes + tests | 0 | Cuts single-expression slice time when keyframes permit |
| 1C | Fix slicer bug, add semaphore | 0 | Stabilizes batch slicing, avoids overload |
| 2A | Implement batch trim planner + unit tests | 1B | Eliminates redundant decode passes |
| 2B | Refactor video assembly to single filter graphs per group | 2A | Largest end-to-end speedup (~35-45%) |
| 3 | Optional streaming outputs, HW acceleration hooks | 2B | Future-proofing |

### Cross-Cutting Considerations
- Update settings schema to hold new tuning knobs (max concurrent FFmpeg jobs, copy-threshold duration, probe cache TTL).
- Extend documentation in `docs/media` and `docs/services` once implementation lands.
- Ensure automated tests cover both old and new paths behind a feature flag before flipping defaults.

## Test Plan (Before/After Timing)

### Goals
- Quantify total pipeline runtime and per-stage durations before and after each optimization phase.
- Verify output parity (duration, resolution, codec, checksum for repeated runs where deterministic).
- Capture resource utilization (CPU %, disk IO wait) to ensure optimizations do not degrade stability.

### Tooling
1. **Profiling Script:** `tools/profile_video_pipeline.py`  
   - Accepts input video+subtitle pair, output directory, and profiling mode (`--profile` flag).  
   - Emits JSON report: stage timings, FFmpeg invocations, average encode duration, cache hit ratios.
2. **Metrics Collector:** Add optional `--emit-metrics <path>` to write Prometheus exposition or CSV for historical comparison.
3. **Log Enhancements:** Structured logging entries `PROFILE_STAGE` with name, duration, count.

### Test Data
- Use a representative 20–25 minute episode with ~30 expressions (existing QA asset in `assets/media`).
- Secondary sample: short clip (5 minutes) to validate behavior on small workloads.

### Procedure
1. Run baseline (current main branch) with profiling enabled. Collect JSON, system metrics (via `pidstat`/`iostat`), and store snapshots under `profiles/baseline/`.
2. After Phase 1 changes, rerun identical command, store under `profiles/phase1/`, and compare metrics (target: ≥20% reduction in FFprobe calls, ≤10% total time improvement).
3. After Phase 2 changes, repeat; success criteria: ≥30% reduction in total pipeline duration, ≤5% deviation in output durations vs. baseline.
4. After each run, execute automated regression tests to ensure no functional regressions.

### Metrics to Track
- End-to-end elapsed time.
- Per-stage durations (parsing, grouping, context extraction, educational assembly, shorts).
- Count of FFmpeg invocations per stage and average duration.
- Cache hit rate for FFprobe.
- Disk write volume per run (from `psutil` or `iostat`).

### Acceptance Criteria
- Phase 1: ≥10% reduction in elapsed time without output changes.
- Phase 2: ≥35% reduction in elapsed time; zero regression in video/audio checksum on deterministic segments; no increase in failure rate.
- Phase 3 (optional): Documented opt-in features without regression.

## Risks & Mitigations
- **Complex FFmpeg graphs increase failure modes** → Build incremental tests, keep legacy path behind feature flag until mature.
- **Cache coherence issues** → Use (path, mtime, size) tuple as cache key; fall back to live probe on mismatch.
- **Concurrency oversubscription** → Use dynamic semaphore tuned to CPU count; expose configuration.
- **Output drift (timings/subtitles)** → Include automated verification comparing timestamps and captions before toggling new pipeline as default.

## Next Steps
1. Create tickets for each roadmap item, referencing this plan.
2. Implement Phase 0 instrumentation immediately to capture baseline while code is unchanged.
3. Execute Phase 1 improvements iteratively with profiling after each sub-phase.
4. Review results and adjust Phase 2 design if unexpected bottlenecks remain.


