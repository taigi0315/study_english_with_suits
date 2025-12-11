#!/usr/bin/env bash
set -euo pipefail

# Benchmark Video Generation Performance
# Usage: ./scripts/benchmark_video_generation.sh [num_expressions]

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${PROJECT_ROOT}/logs/benchmark_${timestamp}.log"
REPORT_FILE="${PROJECT_ROOT}/logs/benchmark_report_${timestamp}.json"

# Default to processing 3 expressions for a quick benchmark, or use argument
MAX_EXPRESSIONS=${1:-3}

echo "🚀 Starting Benchmark: Video Generation (Max Expressions: ${MAX_EXPRESSIONS})"
echo "Logs: ${LOG_FILE}"

# Ensure log directory exists
mkdir -p "${PROJECT_ROOT}/logs"

# Start timer
start_time=$(date +%s)

# Run pipeline in test mode but with profiling enabled
# We use TEST_MODE=1 to avoid full episode generation unless specifically testing full load
# But for performance tuning, we might want to disable TEST_MODE eventually.
# For now, let's use a specific benchmark configuration.

export PROFILING_ENABLED=1
export PROFILE_OUTPUT="${REPORT_FILE}"

# Run the make command with timing
# We override max_expressions to control workload
make dev-all MAX_EXPRESSIONS=${MAX_EXPRESSIONS} > "${LOG_FILE}" 2>&1

end_time=$(date +%s)
duration=$((end_time - start_time))

echo "✅ Benchmark Complete"
echo "Total Duration: ${duration} seconds"
echo "Report saved to: ${REPORT_FILE}"

# Extract some key stats from the log if available (or just rely on the profiler report)
echo "---------------------------------------------------"
grep "PROFILE_STAGE" "${LOG_FILE}" | head -n 5
echo "..."
echo "---------------------------------------------------"
