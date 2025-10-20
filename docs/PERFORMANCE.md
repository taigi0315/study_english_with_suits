# LangFlix Performance Guide

**Version:** 1.0  
**Last Updated:** October 19, 2025

This guide provides comprehensive performance optimization strategies for LangFlix, covering video processing, LLM operations, and overall system performance.

---

## Table of Contents

1. [Performance Overview](#performance-overview)
2. [Video Processing Optimization](#video-processing-optimization)
3. [LLM and API Optimization](#llm-and-api-optimization)
4. [Memory Management](#memory-management)
5. [Concurrency and Parallelization](#concurrency-and-parallelization)
6. [I/O Optimization](#io-optimization)
7. [Caching Strategies](#caching-strategies)
8. [Monitoring and Profiling](#monitoring-and-profiling)
9. [Hardware Recommendations](#hardware-recommendations)
10. [Performance Troubleshooting](#performance-troubleshooting)

---

## Performance Overview

### Current Performance Characteristics

**Typical Processing Times:**
- Small episode (20 minutes): 15-25 minutes
- Medium episode (45 minutes): 35-50 minutes  
- Large episode (60 minutes): 50-80 minutes

**Key Bottlenecks:**
1. **LLM API calls** (60% of processing time)
2. **Video processing** (25% of processing time)
3. **File I/O operations** (10% of processing time)
4. **Other operations** (5% of processing time)

### Performance Targets

- **Throughput**: Process 1 minute of content in ~30 seconds
- **Memory usage**: <8GB for typical episodes
- **API efficiency**: <5% retry rate
- **Video quality**: Maintain high quality while optimizing speed

---

## Video Processing Optimization

### FFmpeg Optimization

#### 1. Hardware Acceleration

**Enable GPU acceleration when available:**

```yaml
# config.yaml
video:
  hardware_acceleration: "cuda"  # or "qsv" for Intel, "vaapi" for AMD
  codec: "h264_nvenc"  # or "h264_qsv", "h264_vaapi"
  preset: "fast"
```

**Implementation example:**
```python
# langflix/video_processor.py
def extract_clip_optimized(self, video_path: Path, start_time: str, end_time: str, output_path: Path) -> bool:
    """Optimized clip extraction with hardware acceleration."""
    
    # Check for hardware acceleration
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
               crf=20,  # Balanced quality/size
               threads=0)  # Use all available threads
        .overwrite_output()
        .run(quiet=True)
    )
```

#### 2. Multi-threading Configuration

```python
class VideoProcessor:
    def __init__(self, media_dir: str = "assets/media"):
        self.media_dir = Path(media_dir)
        # Detect optimal thread count
        self.thread_count = min(os.cpu_count() or 4, 8)  # Cap at 8 threads
        
    def extract_clip(self, video_path: Path, start_time: str, end_time: str, output_path: Path) -> bool:
        """Extract with optimal threading."""
        (
            ffmpeg
            .input(str(video_path), ss=start_seconds, t=duration)
            .output(str(output_path),
                   threads=self.thread_count,
                   preset='fast')
            .run(quiet=True)
        )
```

#### 3. Codec and Quality Optimization

```yaml
# config.yaml - Performance-optimized settings
video:
  # Fast encoding presets
  preset: "fast"           # Balance of speed and compression
  crf: 23                  # Good quality with reasonable file size
  
  # For production with quality priority
  preset: "medium"         # Better compression
  crf: 20                  # Higher quality
  
  # For maximum speed (lower quality)
  preset: "veryfast"       # Fastest encoding
  crf: 26                  # Larger files, faster encoding
```

### Video Processing Pipeline Optimization

#### 1. Batch Processing

```python
def batch_extract_clips(self, expressions: List[ExpressionAnalysis], video_path: Path) -> List[Path]:
    """Extract multiple clips efficiently."""
    
    # Group expressions by time proximity
    sorted_expressions = sorted(expressions, key=lambda x: x.context_start_time)
    
    # Process in batches to avoid memory overload
    batch_size = min(5, len(sorted_expressions))
    results = []
    
    for i in range(0, len(sorted_expressions), batch_size):
        batch = sorted_expressions[i:i + batch_size]
        
        # Extract clips in parallel for the batch
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for expr in batch:
                future = executor.submit(self.extract_single_clip, expr, video_path)
                futures.append(future)
            
            # Collect results
            for future in futures:
                result = future.result()
                if result:
                    results.append(result)
    
    return results
```

#### 2. Temporary File Management

```python
import tempfile
from contextlib import contextmanager

@contextmanager
def temp_video_directory():
    """Context manager for temporary video files."""
    temp_dir = tempfile.mkdtemp(prefix="langflix_")
    try:
        yield Path(temp_dir)
    finally:
        # Clean up temporary files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

# Usage in video processing
def process_expressions_optimized(self, expressions):
    with temp_video_directory() as temp_dir:
        # Process all clips in temp directory
        for expr in expressions:
            temp_clip = temp_dir / f"temp_{expr.expression}.mkv"
            self.extract_clip(video_path, expr.start, expr.end, temp_clip)
            # Process clip...
        # Automatic cleanup when exiting context
```

---

## LLM and API Optimization

### 1. Prompt Optimization

#### Chunk Size Optimization

```yaml
# config.yaml - Optimized for performance
llm:
  max_input_length: 1680    # Balance between context and speed
  chunk_size: 1400         # Leave buffer for prompt overhead
```

#### Prompt Caching

```python
import hashlib
from functools import lru_cache

class OptimizedExpressionAnalyzer:
    def __init__(self):
        self.prompt_cache = {}
    
    def get_cached_prompt(self, chunk_hash: str) -> Optional[str]:
        """Retrieve cached prompt if available."""
        return self.prompt_cache.get(chunk_hash)
    
    def cache_prompt(self, chunk_hash: str, prompt: str):
        """Cache generated prompt."""
        if len(self.prompt_cache) < 100:  # Limit cache size
            self.prompt_cache[chunk_hash] = prompt
    
    def analyze_chunk_optimized(self, subtitle_chunk: List[dict]) -> List[ExpressionAnalysis]:
        """Analyze chunk with caching optimization."""
        # Create hash of chunk content for caching
        chunk_content = json.dumps(subtitle_chunk, sort_keys=True)
        chunk_hash = hashlib.md5(chunk_content.encode()).hexdigest()
        
        # Check cache first
        cached_prompt = self.get_cached_prompt(chunk_hash)
        if cached_prompt:
            # Use cached result if available
            return self.process_cached_result(chunk_hash)
        
        # Generate new prompt and cache it
        prompt = get_prompt_for_chunk(subtitle_chunk)
        self.cache_prompt(chunk_hash, prompt)
        
        # Continue with normal processing...
```

### 2. API Request Optimization

#### Connection Pooling and Timeouts

```python
import httpx
from asyncio import as_completed
import asyncio

class AsyncExpressionAnalyzer:
    def __init__(self, max_concurrent_requests: int = 3):
        self.max_concurrent = max_concurrent_requests
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
    
    async def analyze_chunks_async(self, chunks: List[List[dict]]) -> List[List[ExpressionAnalysis]]:
        """Analyze multiple chunks concurrently."""
        
        async def analyze_single_chunk(chunk: List[dict]) -> List[ExpressionAnalysis]:
            async with self.semaphore:
                # Rate limiting to avoid API limits
                await asyncio.sleep(0.1)  # Small delay between requests
                return await self.analyze_chunk_async(chunk)
        
        # Process chunks concurrently with limit
        tasks = [analyze_single_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        return [r for r in results if not isinstance(r, Exception)]
```

#### Retry Strategy Optimization

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
        """API call with optimized retry strategy."""
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "rate limit" in str(e).lower():
                # Longer wait for rate limits
                time.sleep(random.uniform(30, 60))
                raise
            else:
                raise
```

### 3. Response Processing Optimization

```python
def optimized_response_processing(self, response) -> List[ExpressionAnalysis]:
    """Optimized response processing with early validation."""
    
    try:
        # Fast JSON parsing with validation
        if hasattr(response, 'text'):
            response_data = json.loads(response.text)
        else:
            response_data = response
        
        # Early validation before full processing
        if not isinstance(response_data, dict) or 'expressions' not in response_data:
            logger.warning("Invalid response structure, skipping")
            return []
        
        # Process with minimal object creation
        expressions = []
        for expr_data in response_data['expressions']:
            try:
                # Validate essential fields first
                if not all(key in expr_data for key in ['expression', 'translation', 'dialogues']):
                    continue
                
                expression = ExpressionAnalysis(**expr_data)
                expressions.append(expression)
                
            except ValidationError as e:
                logger.warning(f"Skipping invalid expression: {e}")
                continue
        
        return expressions
        
    except Exception as e:
        logger.error(f"Error processing response: {e}")
        return []
```

---

## Memory Management

### 1. Memory-Efficient Video Processing

```python
import gc
import psutil

class MemoryManager:
    def __init__(self, max_memory_mb: int = 6144):  # 6GB limit
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cleanup_threshold = 0.8  # Cleanup at 80% usage
    
    def check_memory_pressure(self) -> bool:
        """Check if memory usage is approaching limits."""
        memory = psutil.virtual_memory()
        return memory.used > self.max_memory_bytes * self.cleanup_threshold
    
    def force_cleanup(self):
        """Force garbage collection and cleanup."""
        gc.collect()
        
        # If still high, force more aggressive cleanup
        if self.check_memory_pressure():
            time.sleep(1)  # Allow system to catch up
            gc.collect()

def process_with_memory_management(self, expressions: List[ExpressionAnalysis]):
    """Process expressions with memory management."""
    memory_manager = MemoryManager()
    
    for i, expression in enumerate(expressions):
        # Check memory before each processing step
        if memory_manager.check_memory_pressure():
            logger.info("Memory pressure detected, performing cleanup")
            memory_manager.force_cleanup()
        
        # Process expression
        self.process_single_expression(expression)
        
        # Periodic cleanup every 5 expressions
        if i % 5 == 0:
            gc.collect()
```

### 2. Streaming Large Operations

```python
def stream_process_episode(self, subtitle_file: Path) -> Iterator[ExpressionAnalysis]:
    """Process episode in streaming fashion to minimize memory usage."""
    
    # Parse and chunk subtitles
    subtitles = parse_srt_file(str(subtitle_file))
    chunks = chunk_subtitles(subtitles)
    
    for chunk in chunks:
        # Process one chunk at a time
        expressions = self.analyze_chunk(chunk)
        
        for expression in expressions:
            yield expression  # Stream results as they're available
            
        # Clean up chunk processing
        del chunk, expressions
        gc.collect()
```

---

## Concurrency and Parallelization

### 1. Pipeline Parallelization

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp

class ParallelProcessor:
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or min(mp.cpu_count(), 4)
    
    def parallel_video_processing(self, expressions: List[ExpressionAnalysis]) -> List[bool]:
        """Process video clips in parallel."""
        
        def process_single_expression(expr: ExpressionAnalysis) -> bool:
            try:
                return self.video_processor.extract_clip(
                    video_path, expr.context_start_time, 
                    expr.context_end_time, output_path
                )
            except Exception as e:
                logger.error(f"Error processing expression {expr.expression}: {e}")
                return False
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(process_single_expression, expr) for expr in expressions]
            results = [future.result() for future in futures]
        
        return results
    
    def parallel_llm_analysis(self, chunks: List[List[dict]]) -> List[List[ExpressionAnalysis]]:
        """Analyze chunks in parallel with rate limiting."""
        
        def analyze_chunk_safe(chunk: List[dict]) -> List[ExpressionAnalysis]:
            try:
                return analyze_chunk(chunk)
            except Exception as e:
                logger.error(f"Error analyzing chunk: {e}")
                return []
        
        # Limit concurrent API calls to avoid rate limits
        max_concurrent = min(2, self.max_workers)  # Conservative for API calls
        
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = [executor.submit(analyze_chunk_safe, chunk) for chunk in chunks]
            results = [future.result() for future in futures]
        
        return results
```

### 2. Async I/O Operations

```python
import asyncio
import aiofiles

class AsyncFileManager:
    async def async_process_subtitle_files(self, file_paths: List[Path]) -> List[str]:
        """Process multiple subtitle files asynchronously."""
        
        async def read_subtitle_file(file_path: Path) -> str:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                return await f.read()
        
        tasks = [read_subtitle_file(path) for path in file_paths]
        results = await asyncio.gather(*tasks)
        return results
    
    async def async_write_output_files(self, outputs: Dict[str, str]) -> None:
        """Write multiple output files asynchronously."""
        
        async def write_file(filename: str, content: str) -> None:
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(content)
        
        tasks = [write_file(filename, content) for filename, content in outputs.items()]
        await asyncio.gather(*tasks)
```

---

## I/O Optimization

### 1. File System Optimization

```python
class OptimizedFileOperations:
    def __init__(self):
        self.read_buffer_size = 8192  # Optimal buffer size
        
    def batch_read_files(self, file_paths: List[Path]) -> Dict[Path, str]:
        """Read multiple files efficiently."""
        results = {}
        
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8', buffering=self.read_buffer_size) as f:
                    results[file_path] = f.read()
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
                results[file_path] = None
        
        return results
    
    def optimized_directory_scan(self, directory: Path) -> List[Path]:
        """Optimized directory scanning."""
        # Use os.scandir for better performance than os.listdir
        files = []
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_file() and entry.name.lower().endswith('.srt'):
                        files.append(Path(entry.path))
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
        
        return files
```

### 2. Network I/O Optimization

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class OptimizedHTTPClient:
    def __init__(self):
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_maxsize=10)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def make_request(self, url: str, **kwargs) -> requests.Response:
        """Make optimized HTTP request."""
        return self.session.get(url, timeout=30, **kwargs)
```

---

## Caching Strategies

### 1. Expression Analysis Caching

```python
import pickle
import hashlib
from pathlib import Path

class ExpressionCache:
    def __init__(self, cache_dir: Path = Path("cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        
    def get_cache_key(self, chunk: List[dict], language_level: str) -> str:
        """Generate cache key for chunk and settings."""
        content = json.dumps(chunk, sort_keys=True) + language_level
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get_cached_result(self, cache_key: str) -> Optional[List[ExpressionAnalysis]]:
        """Retrieve cached analysis result."""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Error loading cache {cache_file}: {e}")
        
        return None
    
    def cache_result(self, cache_key: str, result: List[ExpressionAnalysis]) -> None:
        """Cache analysis result."""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
        except Exception as e:
            logger.warning(f"Error caching result {cache_file}: {e}")
```

### 2. Video Processing Cache

```python
class VideoProcessingCache:
    def __init__(self, cache_dir: Path = Path("cache/video")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_video_info_cache_key(self, video_path: Path) -> str:
        """Generate cache key based on file path and modification time."""
        stat = video_path.stat()
        return f"{video_path.name}_{stat.st_mtime}_{stat.st_size}"
    
    def get_cached_video_info(self, video_path: Path) -> Optional[Dict[str, Any]]:
        """Get cached video information."""
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
        """Cache video information."""
        cache_key = self.get_video_info_cache_key(video_path)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        with open(cache_file, 'w') as f:
            json.dump(info, f)
```

---

## Monitoring and Profiling

### 1. Performance Monitoring

```python
import time
import psutil
from functools import wraps
from typing import Dict, Any

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
    
    def monitor_function(self, func_name: str):
        """Decorator to monitor function performance."""
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
        """Record performance metric."""
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append(metric)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
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

# Usage
monitor = PerformanceMonitor()

@monitor.monitor_function('analyze_chunk')
def analyze_chunk(subtitle_chunk):
    # Function implementation
    pass

# Get performance summary
summary = monitor.get_summary()
```

### 2. Memory Profiling

```python
import tracemalloc
import linecache

class MemoryProfiler:
    def __init__(self):
        self.snapshots = []
    
    def start_profiling(self):
        """Start memory profiling."""
        tracemalloc.start()
    
    def take_snapshot(self, label: str):
        """Take memory snapshot."""
        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append((label, snapshot))
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
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

## Hardware Recommendations

### Minimum Requirements

**Development/Testing:**
- CPU: 4 cores, 2.4+ GHz
- RAM: 8 GB
- Storage: 100 GB SSD
- GPU: Integrated (for basic processing)

**Production:**
- CPU: 8+ cores, 3.0+ GHz (Intel/AMD)
- RAM: 16+ GB
- Storage: 500+ GB NVMe SSD
- GPU: NVIDIA RTX 3060+ or equivalent (for hardware acceleration)

### Optimized Configuration

**High-Performance Setup:**
- CPU: 16+ cores, 3.5+ GHz
- RAM: 32+ GB DDR4-3200
- Storage: 1+ TB NVMe SSD (multiple for parallel I/O)
- GPU: NVIDIA RTX 4080/4090 or equivalent

**Configuration for High Performance:**

```yaml
# config.yaml - High-performance settings
llm:
  max_input_length: 2000    # Larger chunks for efficiency
  max_retries: 5
  retry_backoff_seconds: 2

video:
  hardware_acceleration: "cuda"  # Use GPU acceleration
  preset: "fast"                 # Speed over compression
  threads: 16                    # Match CPU cores
  
processing:
  max_concurrent_jobs: 8        # Parallel processing
  batch_size: 10                # Larger batches
```

---

## Performance Troubleshooting

### Common Issues and Solutions

#### 1. Slow Video Processing

**Symptoms:** Video clip extraction takes >30 seconds per clip

**Diagnosis:**
```bash
# Check FFmpeg version and capabilities
ffmpeg -version
ffmpeg -encoders | grep nvenc  # Check GPU support

# Monitor CPU/GPU usage during processing
htop  # or nvidia-smi for GPU
```

**Solutions:**
```yaml
# Enable hardware acceleration
video:
  hardware_acceleration: "cuda"  # or "qsv", "vaapi"
  codec: "h264_nvenc"
  preset: "fast"

# Optimize threading
video:
  threads: 0  # Use all available cores
```

#### 2. High Memory Usage

**Symptoms:** System runs out of memory during processing

**Diagnosis:**
```python
# Monitor memory usage
import psutil
memory = psutil.virtual_memory()
print(f"Memory usage: {memory.percent}%")
```

**Solutions:**
```python
# Implement memory management
def process_with_cleanup(expressions):
    for i, expr in enumerate(expressions):
        process_expression(expr)
        
        # Cleanup every 5 expressions
        if i % 5 == 0:
            import gc
            gc.collect()
```

#### 3. API Rate Limiting

**Symptoms:** Frequent API timeout errors, 429 responses

**Solutions:**
```python
# Implement proper rate limiting
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

@rate_limit(calls_per_minute=30)  # Conservative rate limit
def api_call(prompt):
    # API call implementation
    pass
```

#### 4. Disk I/O Bottlenecks

**Symptoms:** System hangs during file operations

**Diagnosis:**
```bash
# Monitor disk I/O
iotop -o  # Show I/O intensive processes
iostat -x 1  # Disk usage statistics
```

**Solutions:**
```python
# Optimize file operations
import aiofiles
import asyncio

async def async_file_operations(files):
    """Use async I/O for better performance."""
    async with aiofiles.open(file_path, 'r') as f:
        content = await f.read()
    
    # Batch operations
    tasks = [read_file_async(f) for f in files]
    results = await asyncio.gather(*tasks)
```

### Performance Benchmarking

Create performance benchmarks to track improvements:

```python
class BenchmarkSuite:
    def __init__(self):
        self.results = {}
    
    def benchmark_video_processing(self, expressions: List[ExpressionAnalysis]) -> Dict[str, float]:
        """Benchmark video processing performance."""
        start_time = time.time()
        
        # Process expressions
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
        """Benchmark LLM analysis performance."""
        start_time = time.time()
        
        for chunk in chunks:
            analyze_chunk(chunk)
        
        total_time = time.time() - start_time
        
        return {
            'total_time': total_time,
            'chunks_per_second': len(chunks) / total_time,
            'avg_time_per_chunk': total_time / len(chunks)
        }

# Usage
benchmark = BenchmarkSuite()
video_results = benchmark.benchmark_video_processing(expressions)
llm_results = benchmark.benchmark_llm_analysis(chunks)
```

---

**For Korean version of this performance guide, see [PERFORMANCE_KOR.md](PERFORMANCE_KOR.md)**

**Related Documentation:**
- [Deployment Guide](DEPLOYMENT.md) - Production optimization
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [API Reference](API_REFERENCE.md) - Understanding the codebase
