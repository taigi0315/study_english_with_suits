# Implementation Roadmap
**Generated:** 2025-10-30
**Architect:** Architect Agent

## Executive Summary
- Total tickets approved: 1
- Estimated timeline: 1 sprint (1-2 weeks)
- Critical path: Media pipeline reliability (audio repeat + layout standardization)
- Key milestones:
  - Demuxer-first repeat implemented
  - Layout consistency (long=hstack, short=vstack)
  - Verification script with ffprobe integrated

## Strategic Context
This roadmap addresses reliability issues in the media pipeline to ensure audio is always present and outputs are consistently generated.

### Architectural Vision
- Prefer simpler, deterministic pipelines
- Separate concerns: AV build → layout → finalization
- Explicit stream handling and validation

### Expected Outcomes
- Stable audio in repeated segments
- Consistent long/short outputs
- Automated verification checks

---

## Phase 0: Immediate (This Week)
**Focus:** Critical media pipeline fixes
**Duration:** 1-3 days

### TICKET-001: Fix expression-repeat audio drop and standardize output layout
- **Priority:** Critical
- **Effort:** 1-3 days
- **Why now:** Blocks content generation reliability
- **Owner:** Senior engineer with FFmpeg experience
- **Dependencies:** None
- **Success metric:** Verification script passes on 2+ inputs; outputs contain audio; layout as specified

Tasks:
1. Implement `repeat_av_demuxer` in `langflix/media/ffmpeg_utils.py`.
2. Update `langflix/core/video_editor.py` to use demuxer concat and standardized layouts.
3. Add final audio gain pass (volume=1.25) as separate step.
4. Enhance `tools/verify_media_pipeline.py` with ffprobe checks.
5. Add integration tests for long/short paths.
6. Update docs (ADR-015/troubleshooting) with new flow.

---

## Phase 1: Sprint 1 (Next 2 weeks)
Pending additional approved tickets.

---

## Dependency Graph
```
TICKET-001 (Phase 0)
```

## Critical Path
1. TICKET-001

**Timeline Impact:**
- Can complete within this week if prioritized.

---

## Risk Management
- Validate with ffprobe at each stage
- Keep fallback path (old filter method) behind a flag during transition

---

## Success Metrics
- Short-term:
  - Audio present in all repeated segments
  - Verification script integrated and green
- Long-term:
  - Reduced failure rate in media jobs
