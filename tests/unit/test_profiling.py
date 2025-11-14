"""
Unit tests for pipeline profiling (TICKET-037).

Tests PipelineProfiler and profile_stage context manager.
"""

import pytest
import json
import tempfile
from pathlib import Path
from time import sleep
from langflix.profiling import PipelineProfiler, profile_stage


class TestPipelineProfiler:
    """Test PipelineProfiler class"""
    
    def test_profiler_initialization_default_path(self):
        """Test profiler initializes with default path"""
        profiler = PipelineProfiler()
        assert profiler.output_path is not None
        assert profiler.output_path.parent.name == "profiles"
        assert profiler.output_path.suffix == ".json"
        assert len(profiler.stages) == 0
    
    def test_profiler_initialization_custom_path(self):
        """Test profiler initializes with custom path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "custom_profile.json"
            profiler = PipelineProfiler(output_path=output_path)
            assert profiler.output_path == output_path
    
    def test_profiler_start_stop(self):
        """Test profiler start and stop"""
        profiler = PipelineProfiler()
        profiler.start(metadata={"test": "value"})
        
        assert profiler.start_time is not None
        assert profiler.metadata["test"] == "value"
        assert "start_timestamp" in profiler.metadata
        
        profiler.stop()
        assert profiler.end_time is not None
        assert "end_timestamp" in profiler.metadata
        assert "total_duration_sec" in profiler.metadata
    
    def test_profiler_record_stage(self):
        """Test recording pipeline stages"""
        profiler = PipelineProfiler()
        profiler.start()
        
        profiler.record("test_stage", 1.5, metadata={"count": 10})
        
        assert len(profiler.stages) == 1
        assert profiler.stages[0]["stage"] == "test_stage"
        assert profiler.stages[0]["duration_sec"] == 1.5
        assert profiler.stages[0]["metadata"]["count"] == 10
    
    def test_profiler_save_report(self):
        """Test saving profiling report to JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_profile.json"
            profiler = PipelineProfiler(output_path=output_path)
            
            profiler.start(metadata={"test": "value"})
            profiler.record("stage1", 1.0)
            profiler.record("stage2", 2.0, metadata={"items": 5})
            profiler.stop()
            
            saved_path = profiler.save_report()
            assert saved_path == output_path
            assert output_path.exists()
            
            # Verify JSON structure
            with open(output_path, 'r') as f:
                report = json.load(f)
            
            assert "metadata" in report
            assert "stages" in report
            assert "summary" in report
            assert len(report["stages"]) == 2
            assert report["stages"][0]["stage"] == "stage1"
            assert report["stages"][1]["stage"] == "stage2"
            assert report["summary"]["total_stages"] == 2
    
    def test_profiler_summary_generation(self):
        """Test summary generation from stages"""
        profiler = PipelineProfiler()
        profiler.start()
        
        profiler.record("fast_stage", 0.5)
        profiler.record("slow_stage", 5.0)
        profiler.record("medium_stage", 2.0)
        profiler.stop()
        
        summary = profiler._generate_summary()
        
        assert summary["total_stages"] == 3
        assert summary["total_stage_duration_sec"] == 7.5
        assert summary["slowest_stage"]["name"] == "slow_stage"
        assert summary["slowest_stage"]["duration_sec"] == 5.0
        assert summary["average_stage_duration_sec"] == pytest.approx(2.5, rel=0.01)
    
    def test_profiler_get_report(self):
        """Test getting report as dictionary without saving"""
        profiler = PipelineProfiler()
        profiler.start()
        profiler.record("test_stage", 1.0)
        profiler.stop()
        
        report = profiler.get_report()
        
        assert "metadata" in report
        assert "stages" in report
        assert "summary" in report
        assert len(report["stages"]) == 1


class TestProfileStage:
    """Test profile_stage context manager"""
    
    def test_profile_stage_without_profiler(self):
        """Test profile_stage works without profiler"""
        with profile_stage("test_stage"):
            sleep(0.01)  # Small delay to ensure timing is recorded
        
        # Should not raise exception
    
    def test_profile_stage_with_profiler(self):
        """Test profile_stage records timing in profiler"""
        profiler = PipelineProfiler()
        profiler.start()
        
        with profile_stage("test_stage", profiler):
            sleep(0.01)
        
        assert len(profiler.stages) == 1
        assert profiler.stages[0]["stage"] == "test_stage"
        assert profiler.stages[0]["duration_sec"] > 0
    
    def test_profile_stage_with_metadata(self):
        """Test profile_stage includes metadata"""
        profiler = PipelineProfiler()
        profiler.start()
        
        with profile_stage("test_stage", profiler, metadata={"count": 5}):
            pass
        
        assert profiler.stages[0]["metadata"]["count"] == 5
    
    def test_profile_stage_exception_handling(self):
        """Test profile_stage still records timing even if exception occurs"""
        profiler = PipelineProfiler()
        profiler.start()
        
        try:
            with profile_stage("test_stage", profiler):
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Should still have recorded the stage
        assert len(profiler.stages) == 1
        assert profiler.stages[0]["stage"] == "test_stage"
    
    def test_profile_stage_profiler_failure_handling(self):
        """Test profile_stage handles profiler failures gracefully"""
        # Create a mock profiler that fails
        class FailingProfiler:
            def record(self, *args, **kwargs):
                raise Exception("Profiler error")
        
        failing_profiler = FailingProfiler()
        
        # Should not raise exception
        with profile_stage("test_stage", failing_profiler):
            pass


class TestProfilingIntegration:
    """Integration tests for profiling"""
    
    def test_full_profiling_workflow(self):
        """Test complete profiling workflow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "integration_test.json"
            profiler = PipelineProfiler(output_path=output_path)
            
            profiler.start(metadata={"test_run": True})
            
            # Simulate pipeline stages
            with profile_stage("parse_subtitles", profiler):
                sleep(0.01)
            
            with profile_stage("chunk_subtitles", profiler, metadata={"num_subtitles": 100}):
                sleep(0.01)
            
            with profile_stage("analyze_expressions", profiler, metadata={"num_chunks": 10}):
                sleep(0.01)
            
            profiler.stop()
            
            # Save and verify
            saved_path = profiler.save_report()
            assert saved_path.exists()
            
            with open(saved_path, 'r') as f:
                report = json.load(f)
            
            assert report["metadata"]["test_run"] is True
            assert len(report["stages"]) == 3
            assert report["summary"]["total_stages"] == 3
            assert report["stages"][1]["metadata"]["num_subtitles"] == 100

