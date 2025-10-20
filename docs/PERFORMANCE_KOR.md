# LangFlix 성능 가이드

**버전:** 1.0  
**최종 업데이트:** 2025년 10월 19일

이 가이드는 LangFlix의 비디오 처리, LLM 작업 및 전체 시스템 성능을 포함한 포괄적인 성능 최적화 전략을 제공합니다.

---

## 목차

1. [성능 개요](#성능-개요)
2. [비디오 처리 최적화](#비디오-처리-최적화)
3. [LLM 및 API 최적화](#llm-및-api-최적화)
4. [메모리 관리](#메모리-관리)
5. [동시성 및 병렬화](#동시성-및-병렬화)
6. [I/O 최적화](#io-최적화)
7. [캐싱 전략](#캐싱-전략)
8. [모니터링 및 프로파일링](#모니터링-및-프로파일링)
9. [하드웨어 권장사항](#하드웨어-권장사항)
10. [성능 문제 해결](#성능-문제-해결)

---

## 성능 개요

### 현재 성능 특성

**일반적인 처리 시간:**
- 소형 에피소드 (20분): 15-25분
- 중형 에피소드 (45분): 35-50분  
- 대형 에피소드 (60분): 50-80분

**주요 병목 지점:**
1. **LLM API 호출** (처리 시간의 60%)
2. **비디오 처리** (처리 시간의 25%)
3. **파일 I/O 작업** (처리 시간의 10%)
4. **기타 작업** (처리 시간의 5%)

### 성능 목표

- **처리량**: 30초 내에 1분 콘텐츠 처리
- **메모리 사용량**: 일반적인 에피소드에 대해 <8GB
- **API 효율성**: <5% 재시도율
- **비디오 품질**: 속도 최적화하면서 고품질 유지

---

## 비디오 처리 최적화

### FFmpeg 최적화

#### 1. 하드웨어 가속

**사용 가능한 경우 GPU 가속 활성화:**

```yaml
# config.yaml
video:
  hardware_acceleration: "cuda"  # Intel의 경우 "qsv", AMD의 경우 "vaapi"
  codec: "h264_nvenc"            # 또는 "h264_qsv", "h264_vaapi"
  preset: "fast"
```

**구현 예제:**
```python
# langflix/video_processor.py
def extract_clip_optimized(self, video_path: Path, start_time: str, end_time: str, output_path: Path) -> bool:
    """하드웨어 가속으로 최적화된 클립 추출."""
    
    # 하드웨어 가속 확인
    hw_config = self.get_hardware_config()
    
    if hw_config['cuda_available']:
        vcodec = 'h264_nvenc'
        preset = 'fast'
    elif hw_config['qsv_available']:
        vcodec = 'h264_qsv'
        preset = 'faster'
    else:
        vcodec = 'libx264'
        preset = 'fast'
    
    (
        ffmpeg
        .input(str(video_path), ss=start_seconds, t=duration)
        .output(str(output_path), 
               vcodec=vcodec,
               preset=preset,
               crf=20,  # 품질/크기 균형
               threads=0)  # 사용 가능한 모든 스레드 사용
        .overwrite_output()
        .run(quiet=True)
    )
```

#### 2. 다중 스레딩 구성

```python
class VideoProcessor:
    def __init__(self, media_dir: str = "assets/media"):
        self.media_dir = Path(media_dir)
        # 최적 스레드 수 감지
        self.thread_count = min(os.cpu_count() or 4, 8)  # 최대 8개 스레드로 제한
        
    def extract_clip(self, video_path: Path, start_time: str, end_time: str, output_path: Path) -> bool:
        """최적 스레딩으로 추출."""
        (
            ffmpeg
            .input(str(video_path), ss=start_seconds, t=duration)
            .output(str(output_path),
                   threads=self.thread_count,
                   preset='fast')
            .run(quiet=True)
        )
```

#### 3. 코덱 및 품질 최적화

```yaml
# config.yaml - 성능 최적화 설정
video:
  # 빠른 인코딩 프리셋
  preset: "fast"           # 속도와 압축의 균형
  crf: 23                  # 합리적인 파일 크기로 좋은 품질
  
  # 품질 우선 프로덕션용
  preset: "medium"         # 더 나은 압축
  crf: 20                  # 더 높은 품질
  
  # 최대 속도용 (낮은 품질)
  preset: "veryfast"       # 가장 빠른 인코딩
  crf: 26                  # 더 큰 파일, 더 빠른 인코딩
```

### 비디오 처리 파이프라인 최적화

#### 1. 배치 처리

```python
def batch_extract_clips(self, expressions: List[ExpressionAnalysis], video_path: Path) -> List[Path]:
    """여러 클립을 효율적으로 추출."""
    
    # 시간 근접성으로 표현 그룹화
    sorted_expressions = sorted(expressions, key=lambda x: x.context_start_time)
    
    # 메모리 과부하 방지를 위해 배치로 처리
    batch_size = min(5, len(sorted_expressions))
    results = []
    
    for i in range(0, len(sorted_expressions), batch_size):
        batch = sorted_expressions[i:i + batch_size]
        
        # 배치에 대해 클립을 병렬로 추출
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for expr in batch:
                future = executor.submit(self.extract_single_clip, expr, video_path)
                futures.append(future)
            
            # 결과 수집
            for future in futures:
                result = future.result()
                if result:
                    results.append(result)
    
    return results
```

#### 2. 임시 파일 관리

```python
import tempfile
from contextlib import contextmanager

@contextmanager
def temp_video_directory():
    """임시 비디오 파일용 컨텍스트 매니저."""
    temp_dir = tempfile.mkdtemp(prefix="langflix_")
    try:
        yield Path(temp_dir)
    finally:
        # 임시 파일 정리
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

# 비디오 처리에서 사용
def process_expressions_optimized(self, expressions):
    with temp_video_directory() as temp_dir:
        # temp 디렉토리에서 모든 클립 처리
        for expr in expressions:
            temp_clip = temp_dir / f"temp_{expr.expression}.mkv"
            self.extract_clip(video_path, expr.start, expr.end, temp_clip)
            # 클립 처리...
        # 컨텍스트 종료 시 자동 정리
```

---

## LLM 및 API 최적화

### 1. 프롬프트 최적화

#### 청크 크기 최적화

```yaml
# config.yaml - 성능 최적화
llm:
  max_input_length: 1680    # 컨텍스트와 속도 간 균형
  chunk_size: 1400         # 프롬프트 오버헤드를 위한 버퍼 남김
```

#### 프롬프트 캐싱

```python
import hashlib
from functools import lru_cache

class OptimizedExpressionAnalyzer:
    def __init__(self):
        self.prompt_cache = {}
    
    def get_cached_prompt(self, chunk_hash: str) -> Optional[str]:
        """사용 가능한 경우 캐시된 프롬프트 검색."""
        return self.prompt_cache.get(chunk_hash)
    
    def cache_prompt(self, chunk_hash: str, prompt: str):
        """생성된 프롬프트 캐싱."""
        if len(self.prompt_cache) < 100:  # 캐시 크기 제한
            self.prompt_cache[chunk_hash] = prompt
    
    def analyze_chunk_optimized(self, subtitle_chunk: List[dict]) -> List[ExpressionAnalysis]:
        """캐싱 최적화로 청크 분석."""
        # 캐싱을 위한 청크 콘텐츠 해시 생성
        chunk_content = json.dumps(subtitle_chunk, sort_keys=True)
        chunk_hash = hashlib.md5(chunk_content.encode()).hexdigest()
        
        # 먼저 캐시 확인
        cached_prompt = self.get_cached_prompt(chunk_hash)
        if cached_prompt:
            # 사용 가능한 경우 캐시된 결과 사용
            return self.process_cached_result(chunk_hash)
        
        # 새 프롬프트 생성 및 캐싱
        prompt = get_prompt_for_chunk(subtitle_chunk)
        self.cache_prompt(chunk_hash, prompt)
        
        # 일반 처리 계속...
```

### 2. API 요청 최적화

#### 연결 풀링 및 타임아웃

```python
import httpx
from asyncio import as_completed
import asyncio

class AsyncExpressionAnalyzer:
    def __init__(self, max_concurrent_requests: int = 3):
        self.max_concurrent = max_concurrent_requests
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
    
    async def analyze_chunks_async(self, chunks: List[List[dict]]) -> List[List[ExpressionAnalysis]]:
        """여러 청크를 동시에 분석."""
        
        async def analyze_single_chunk(chunk: List[dict]) -> List[ExpressionAnalysis]:
            async with self.semaphore:
                # API 제한을 피하기 위한 속도 제한
                await asyncio.sleep(0.1)  # 요청 간 짧은 지연
                return await self.analyze_chunk_async(chunk)
        
        # 제한과 함께 청크 동시 처리
        tasks = [analyze_single_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 필터링
        return [r for r in results if not isinstance(r, Exception)]
```

#### 재시도 전략 최적화

```python
import random
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class OptimizedRetryStrategy:
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((TimeoutError, ConnectionError))
    )
    def api_call_with_backoff(self, prompt: str) -> str:
        """최적화된 재시도 전략으로 API 호출."""
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "rate limit" in str(e).lower():
                # 속도 제한에 대한 더 긴 대기
                time.sleep(random.uniform(30, 60))
                raise
            else:
                raise
```

### 3. 응답 처리 최적화

```python
def optimized_response_processing(self, response) -> List[ExpressionAnalysis]:
    """조기 검증으로 최적화된 응답 처리."""
    
    try:
        # 검증과 함께 빠른 JSON 파싱
        if hasattr(response, 'text'):
            response_data = json.loads(response.text)
        else:
            response_data = response
        
        # 전체 처리 전 조기 검증
        if not isinstance(response_data, dict) or 'expressions' not in response_data:
            logger.warning("잘못된 응답 구조, 건너뜀")
            return []
        
        # 최소 객체 생성으로 처리
        expressions = []
        for expr_data in response_data['expressions']:
            try:
                # 먼저 필수 필드 검증
                if not all(key in expr_data for key in ['expression', 'translation', 'dialogues']):
                    continue
                
                expression = ExpressionAnalysis(**expr_data)
                expressions.append(expression)
                
            except ValidationError as e:
                logger.warning(f"잘못된 표현 건너뜀: {e}")
                continue
        
        return expressions
        
    except Exception as e:
        logger.error(f"응답 처리 오류: {e}")
        return []
```

---

## 메모리 관리

### 1. 메모리 효율적인 비디오 처리

```python
import gc
import psutil

class MemoryManager:
    def __init__(self, max_memory_mb: int = 6144):  # 6GB 제한
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cleanup_threshold = 0.8  # 80% 사용 시 정리
    
    def check_memory_pressure(self) -> bool:
        """메모리 사용량이 제한에 근접하는지 확인."""
        memory = psutil.virtual_memory()
        return memory.used > self.max_memory_bytes * self.cleanup_threshold
    
    def force_cleanup(self):
        """가비지 컬렉션 및 정리 강제 실행."""
        gc.collect()
        
        # 여전히 높으면 더 적극적인 정리
        if self.check_memory_pressure():
            time.sleep(1)  # 시스템이 따라잡을 수 있도록 허용
            gc.collect()

def process_with_memory_management(self, expressions: List[ExpressionAnalysis]):
    """메모리 관리로 표현 처리."""
    memory_manager = MemoryManager()
    
    for i, expression in enumerate(expressions):
        # 각 처리 단계 전에 메모리 확인
        if memory_manager.check_memory_pressure():
            logger.info("메모리 압력 감지, 정리 수행")
            memory_manager.force_cleanup()
        
        # 표현 처리
        self.process_single_expression(expression)
        
        # 5개 표현마다 정기적 정리
        if i % 5 == 0:
            gc.collect()
```

### 2. 큰 작업 스트리밍

```python
def stream_process_episode(self, subtitle_file: Path) -> Iterator[ExpressionAnalysis]:
    """메모리 사용량을 최소화하기 위해 스트리밍 방식으로 에피소드 처리."""
    
    # 자막 파싱 및 청킹
    subtitles = parse_srt_file(str(subtitle_file))
    chunks = chunk_subtitles(subtitles)
    
    for chunk in chunks:
        # 한 번에 하나의 청크 처리
        expressions = self.analyze_chunk(chunk)
        
        for expression in expressions:
            yield expression  # 사용 가능한 대로 결과 스트리밍
            
        # 청크 처리 정리
        del chunk, expressions
        gc.collect()
```

---

## 동시성 및 병렬화

### 1. 파이프라인 병렬화

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp

class ParallelProcessor:
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or min(mp.cpu_count(), 4)
    
    def parallel_video_processing(self, expressions: List[ExpressionAnalysis]) -> List[bool]:
        """비디오 클립을 병렬로 처리."""
        
        def process_single_expression(expr: ExpressionAnalysis) -> bool:
            try:
                return self.video_processor.extract_clip(
                    video_path, expr.context_start_time, 
                    expr.context_end_time, output_path
                )
            except Exception as e:
                logger.error(f"표현 {expr.expression} 처리 오류: {e}")
                return False
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(process_single_expression, expr) for expr in expressions]
            results = [future.result() for future in futures]
        
        return results
    
    def parallel_llm_analysis(self, chunks: List[List[dict]]) -> List[List[ExpressionAnalysis]]:
        """속도 제한과 함께 청크를 병렬로 분석."""
        
        def analyze_chunk_safe(chunk: List[dict]) -> List[ExpressionAnalysis]:
            try:
                return analyze_chunk(chunk)
            except Exception as e:
                logger.error(f"청크 분석 오류: {e}")
                return []
        
        # 속도 제한을 피하기 위해 동시 API 호출 제한
        max_concurrent = min(2, self.max_workers)  # API 호출에 대해 보수적
        
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = [executor.submit(analyze_chunk_safe, chunk) for chunk in chunks]
            results = [future.result() for future in futures]
        
        return results
```

### 2. 비동기 I/O 작업

```python
import asyncio
import aiofiles

class AsyncFileManager:
    async def async_process_subtitle_files(self, file_paths: List[Path]) -> List[str]:
        """여러 자막 파일을 비동기로 처리."""
        
        async def read_subtitle_file(file_path: Path) -> str:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                return await f.read()
        
        tasks = [read_subtitle_file(path) for path in file_paths]
        results = await asyncio.gather(*tasks)
        return results
    
    async def async_write_output_files(self, outputs: Dict[str, str]) -> None:
        """여러 출력 파일을 비동기로 쓰기."""
        
        async def write_file(filename: str, content: str) -> None:
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(content)
        
        tasks = [write_file(filename, content) for filename, content in outputs.items()]
        await asyncio.gather(*tasks)
```

---

## I/O 최적화

### 1. 파일 시스템 최적화

```python
class OptimizedFileOperations:
    def __init__(self):
        self.read_buffer_size = 8192  # 최적 버퍼 크기
        
    def batch_read_files(self, file_paths: List[Path]) -> Dict[Path, str]:
        """여러 파일을 효율적으로 읽기."""
        results = {}
        
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8', buffering=self.read_buffer_size) as f:
                    results[file_path] = f.read()
            except Exception as e:
                logger.error(f"{file_path} 읽기 오류: {e}")
                results[file_path] = None
        
        return results
    
    def optimized_directory_scan(self, directory: Path) -> List[Path]:
        """최적화된 디렉토리 스캔."""
        # os.listdir보다 성능이 더 좋은 os.scandir 사용
        files = []
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_file() and entry.name.lower().endswith('.srt'):
                        files.append(Path(entry.path))
        except Exception as e:
            logger.error(f"디렉토리 {directory} 스캔 오류: {e}")
        
        return files
```

### 2. 네트워크 I/O 최적화

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class OptimizedHTTPClient:
    def __init__(self):
        self.session = requests.Session()
        
        # 재시도 전략 구성
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_maxsize=10)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def make_request(self, url: str, **kwargs) -> requests.Response:
        """최적화된 HTTP 요청."""
        return self.session.get(url, timeout=30, **kwargs)
```

---

## 캐싱 전략

### 1. 표현 분석 캐싱

```python
import pickle
import hashlib
from pathlib import Path

class ExpressionCache:
    def __init__(self, cache_dir: Path = Path("cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        
    def get_cache_key(self, chunk: List[dict], language_level: str) -> str:
        """청크와 설정에 대한 캐시 키 생성."""
        content = json.dumps(chunk, sort_keys=True) + language_level
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get_cached_result(self, cache_key: str) -> Optional[List[ExpressionAnalysis]]:
        """캐시된 분석 결과 검색."""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"캐시 {cache_file} 로드 오류: {e}")
        
        return None
    
    def cache_result(self, cache_key: str, result: List[ExpressionAnalysis]) -> None:
        """분석 결과 캐싱."""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
        except Exception as e:
            logger.warning(f"결과 캐싱 오류 {cache_file}: {e}")
```

### 2. 비디오 처리 캐시

```python
class VideoProcessingCache:
    def __init__(self, cache_dir: Path = Path("cache/video")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_video_info_cache_key(self, video_path: Path) -> str:
        """파일 경로와 수정 시간을 기반으로 캐시 키 생성."""
        stat = video_path.stat()
        return f"{video_path.name}_{stat.st_mtime}_{stat.st_size}"
    
    def get_cached_video_info(self, video_path: Path) -> Optional[Dict[str, Any]]:
        """캐시된 비디오 정보 가져오기."""
        cache_key = self.get_video_info_cache_key(video_path)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return None
    
    def cache_video_info(self, video_path: Path, info: Dict[str, Any]) -> None:
        """비디오 정보 캐싱."""
        cache_key = self.get_video_info_cache_key(video_path)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        with open(cache_file, 'w') as f:
            json.dump(info, f)
```

---

## 모니터링 및 프로파일링

### 1. 성능 모니터링

```python
import time
import psutil
from functools import wraps
from typing import Dict, Any

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
    
    def monitor_function(self, func_name: str):
        """함수 성능 모니터링 데코레이터."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                start_memory = psutil.virtual_memory().used
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.time()
                    end_memory = psutil.virtual_memory().used
                    
                    execution_time = end_time - start_time
                    memory_delta = (end_memory - start_memory) / 1024 / 1024  # MB
                    
                    self.record_metric(func_name, {
                        'execution_time': execution_time,
                        'memory_delta': memory_delta,
                        'timestamp': end_time
                    })
            
            return wrapper
        return decorator
    
    def record_metric(self, name: str, metric: Dict[str, Any]):
        """성능 메트릭 기록."""
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append(metric)
    
    def get_summary(self) -> Dict[str, Any]:
        """성능 요약 가져오기."""
        summary = {}
        
        for func_name, metrics in self.metrics.items():
            if metrics:
                times = [m['execution_time'] for m in metrics]
                memory_deltas = [m['memory_delta'] for m in metrics]
                
                summary[func_name] = {
                    'avg_time': sum(times) / len(times),
                    'max_time': max(times),
                    'total_calls': len(times),
                    'avg_memory_delta': sum(memory_deltas) / len(memory_deltas)
                }
        
        return summary

# 사용법
monitor = PerformanceMonitor()

@monitor.monitor_function('analyze_chunk')
def analyze_chunk(subtitle_chunk):
    # 함수 구현
    pass

# 성능 요약 가져오기
summary = monitor.get_summary()
```

### 2. 메모리 프로파일링

```python
import tracemalloc
import linecache

class MemoryProfiler:
    def __init__(self):
        self.snapshots = []
    
    def start_profiling(self):
        """메모리 프로파일링 시작."""
        tracemalloc.start()
    
    def take_snapshot(self, label: str):
        """메모리 스냅샷 찍기."""
        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append((label, snapshot))
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """메모리 사용 통계 가져오기."""
        if not tracemalloc.is_tracing():
            return {}
        
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        return {
            'total_memory_mb': sum(stat.size for stat in top_stats) / 1024 / 1024,
            'top_allocations': [
                {
                    'filename': stat.traceback.format()[0],
                    'size_mb': stat.size / 1024 / 1024,
                    'count': stat.count
                }
                for stat in top_stats[:10]
            ]
        }
```

---

## 하드웨어 권장사항

### 최소 요구사항

**개발/테스팅:**
- CPU: 4코어, 2.4+ GHz
- RAM: 8 GB
- 저장공간: 100 GB SSD
- GPU: 통합형 (기본 처리용)

**프로덕션:**
- CPU: 8+ 코어, 3.0+ GHz (Intel/AMD)
- RAM: 16+ GB
- 저장공간: 500+ GB NVMe SSD
- GPU: NVIDIA RTX 3060+ 또는 동등 (하드웨어 가속용)

### 최적화된 구성

**고성능 설정:**
- CPU: 16+ 코어, 3.5+ GHz
- RAM: 32+ GB DDR4-3200
- 저장공간: 1+ TB NVMe SSD (병렬 I/O용 여러 개)
- GPU: NVIDIA RTX 4080/4090 또는 동등

**고성능 설정:**

```yaml
# config.yaml - 고성능 설정
llm:
  max_input_length: 2000    # 효율성을 위한 더 큰 청크
  max_retries: 5
  retry_backoff_seconds: 2

video:
  hardware_acceleration: "cuda"  # GPU 가속 사용
  preset: "fast"                 # 압축보다 속도 우선
  threads: 16                    # CPU 코어와 일치
  
processing:
  max_concurrent_jobs: 8        # 병렬 처리
  batch_size: 10                # 더 큰 배치
```

---

## 성능 문제 해결

### 일반적인 문제와 해결책

#### 1. 느린 비디오 처리

**증상:** 비디오 클립 추출이 클립당 >30초 소요

**진단:**
```bash
# FFmpeg 버전 및 기능 확인
ffmpeg -version
ffmpeg -encoders | grep nvenc  # GPU 지원 확인

# 처리 중 CPU/GPU 사용량 모니터링
htop  # 또는 GPU용 nvidia-smi
```

**해결책:**
```yaml
# 하드웨어 가속 활성화
video:
  hardware_acceleration: "cuda"  # 또는 "qsv", "vaapi"
  codec: "h264_nvenc"
  preset: "fast"

# 스레딩 최적화
video:
  threads: 0  # 사용 가능한 모든 코어 사용
```

#### 2. 높은 메모리 사용량

**증상:** 처리 중 시스템 메모리 부족

**진단:**
```python
# 메모리 사용량 모니터링
import psutil
memory = psutil.virtual_memory()
print(f"메모리 사용량: {memory.percent}%")
```

**해결책:**
```python
# 메모리 관리 구현
def process_with_cleanup(expressions):
    for i, expr in enumerate(expressions):
        process_expression(expr)
        
        # 5개 표현마다 정리
        if i % 5 == 0:
            import gc
            gc.collect()
```

#### 3. API 속도 제한

**증상:** 빈번한 API 타임아웃 오류, 429 응답

**해결책:**
```python
# 적절한 속도 제한 구현
import time
from functools import wraps

def rate_limit(calls_per_minute: int = 60):
    min_interval = 60.0 / calls_per_minute
    
    def decorator(func):
        last_called = [0.0]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator

@rate_limit(calls_per_minute=30)  # 보수적 속도 제한
def api_call(prompt):
    # API 호출 구현
    pass
```

#### 4. 디스크 I/O 병목

**증상:** 파일 작업 중 시스템 정지

**진단:**
```bash
# 디스크 I/O 모니터링
iotop -o  # I/O 집약적 프로세스 표시
iostat -x 1  # 디스크 사용 통계
```

**해결책:**
```python
# 파일 작업 최적화
import aiofiles
import asyncio

async def async_file_operations(files):
    """더 나은 성능을 위한 비동기 I/O 사용."""
    async with aiofiles.open(file_path, 'r') as f:
        content = await f.read()
    
    # 배치 작업
    tasks = [read_file_async(f) for f in files]
    results = await asyncio.gather(*tasks)
```

### 성능 벤치마킹

개선사항을 추적하기 위한 성능 벤치마크 생성:

```python
class BenchmarkSuite:
    def __init__(self):
        self.results = {}
    
    def benchmark_video_processing(self, expressions: List[ExpressionAnalysis]) -> Dict[str, float]:
        """비디오 처리 성능 벤치마킹."""
        start_time = time.time()
        
        # 표현 처리
        results = []
        for expr in expressions:
            result = self.process_expression(expr)
            results.append(result)
        
        total_time = time.time() - start_time
        
        return {
            'total_time': total_time,
            'expressions_per_second': len(expressions) / total_time,
            'avg_time_per_expression': total_time / len(expressions)
        }
    
    def benchmark_llm_analysis(self, chunks: List[List[dict]]) -> Dict[str, float]:
        """LLM 분석 성능 벤치마킹."""
        start_time = time.time()
        
        for chunk in chunks:
            analyze_chunk(chunk)
        
        total_time = time.time() - start_time
        
        return {
            'total_time': total_time,
            'chunks_per_second': len(chunks) / total_time,
            'avg_time_per_chunk': total_time / len(chunks)
        }

# 사용법
benchmark = BenchmarkSuite()
video_results = benchmark.benchmark_video_processing(expressions)
llm_results = benchmark.benchmark_llm_analysis(chunks)
```

---

**이 성능 가이드의 영어 버전은 [PERFORMANCE.md](PERFORMANCE.md)를 참조하세요**

**관련 문서:**
- [배포 가이드](DEPLOYMENT_KOR.md) - 프로덕션 최적화
- [문제 해결 가이드](TROUBLESHOOTING_KOR.md) - 일반적인 문제와 해결책
- [API 참조](API_REFERENCE_KOR.md) - 코드베이스 이해
