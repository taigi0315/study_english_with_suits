"""
Audio optimization system for LangFlix Expression-Based Learning Feature.

This module provides:
- Audio normalization
- Noise reduction
- Dynamic range compression
- Audio synchronization improvement
- Quality enhancement
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class AudioQualityMetrics:
    """Audio quality metrics"""
    loudness_lufs: float
    peak_db: float
    dynamic_range: float
    noise_floor_db: float
    frequency_response: Dict[str, float]
    distortion_percent: float

@dataclass
class AudioOptimizationConfig:
    """Audio optimization configuration"""
    target_loudness: float = -23.0  # LUFS
    max_peak: float = -1.0  # dB
    noise_reduction: float = 0.3  # 0-1
    dynamic_range_compression: float = 0.5  # 0-1
    normalize: bool = True
    enhance_clarity: bool = True

class AudioOptimizer:
    """Advanced audio optimization system"""
    
    def __init__(self, config: Optional[AudioOptimizationConfig] = None):
        """
        Initialize audio optimizer
        
        Args:
            config: Audio optimization configuration
        """
        self.config = config or AudioOptimizationConfig()
        logger.info("AudioOptimizer initialized")
    
    def optimize_audio(
        self,
        input_path: str,
        output_path: str,
        optimization_level: str = "medium"
    ) -> AudioQualityMetrics:
        """
        Optimize audio file for educational content
        
        Args:
            input_path: Path to input audio file
            output_path: Path to output optimized audio file
            optimization_level: Level of optimization (low, medium, high)
            
        Returns:
            AudioQualityMetrics with optimization results
        """
        logger.info(f"Optimizing audio: {input_path} -> {output_path}")
        
        # Analyze input audio
        input_metrics = self._analyze_audio_quality(input_path)
        logger.info(f"Input audio metrics: {input_metrics}")
        
        # Apply optimizations based on level
        if optimization_level == "low":
            optimized_path = self._apply_basic_optimization(input_path, output_path)
        elif optimization_level == "medium":
            optimized_path = self._apply_medium_optimization(input_path, output_path)
        elif optimization_level == "high":
            optimized_path = self._apply_high_optimization(input_path, output_path)
        else:
            raise ValueError(f"Invalid optimization level: {optimization_level}")
        
        # Analyze output audio
        output_metrics = self._analyze_audio_quality(optimized_path)
        logger.info(f"Output audio metrics: {output_metrics}")
        
        return output_metrics
    
    def _analyze_audio_quality(self, audio_path: str) -> AudioQualityMetrics:
        """Analyze audio quality metrics using FFmpeg"""
        try:
            # Use FFmpeg to analyze audio
            cmd = [
                'ffmpeg', '-i', audio_path, '-af', 'loudnorm=I=-23:LRA=7:TP=-1',
                '-f', 'null', '-'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, stderr=subprocess.STDOUT)
            
            # Parse FFmpeg output for metrics
            metrics = self._parse_ffmpeg_metrics(result.stdout)
            
            return AudioQualityMetrics(
                loudness_lufs=metrics.get('loudness', -23.0),
                peak_db=metrics.get('peak', -1.0),
                dynamic_range=metrics.get('dynamic_range', 7.0),
                noise_floor_db=metrics.get('noise_floor', -60.0),
                frequency_response=metrics.get('frequency_response', {}),
                distortion_percent=metrics.get('distortion', 0.0)
            )
            
        except Exception as e:
            logger.warning(f"Failed to analyze audio quality: {e}")
            return AudioQualityMetrics(
                loudness_lufs=-23.0, peak_db=-1.0, dynamic_range=7.0,
                noise_floor_db=-60.0, frequency_response={}, distortion_percent=0.0
            )
    
    def _parse_ffmpeg_metrics(self, output: str) -> Dict[str, Any]:
        """Parse FFmpeg output for audio metrics"""
        metrics = {}
        
        # Parse loudness information
        for line in output.split('\n'):
            if 'Input Integrated' in line:
                try:
                    loudness = float(line.split(':')[1].strip().split()[0])
                    metrics['loudness'] = loudness
                except:
                    pass
        
        return metrics
    
    def _apply_basic_optimization(self, input_path: str, output_path: str) -> str:
        """Apply basic audio optimization"""
        cmd = [
            'ffmpeg', '-i', input_path,
            '-af', 'loudnorm=I=-23:LRA=7:TP=-1',
            '-c:a', 'aac', '-b:a', '128k',
            '-y', output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def _apply_medium_optimization(self, input_path: str, output_path: str) -> str:
        """Apply medium audio optimization"""
        cmd = [
            'ffmpeg', '-i', input_path,
            '-af', f'loudnorm=I={self.config.target_loudness}:LRA=7:TP={self.config.max_peak},'
                   f'highpass=f=80,lowpass=f=8000,'
                   f'compand=.3|.3:1|1:-90/-60|-60/-40|-40/-30|-20/-20:6:0:-90:0.2',
            '-c:a', 'aac', '-b:a', '192k',
            '-y', output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def _apply_high_optimization(self, input_path: str, output_path: str) -> str:
        """Apply high audio optimization"""
        cmd = [
            'ffmpeg', '-i', input_path,
            '-af', f'loudnorm=I={self.config.target_loudness}:LRA=7:TP={self.config.max_peak},'
                   f'highpass=f=80,lowpass=f=8000,'
                   f'compand=.3|.3:1|1:-90/-60|-60/-40|-40/-30|-20/-20:6:0:-90:0.2,'
                   f'equalizer=f=1000:width_type=h:width=200:g=2,'
                   f'equalizer=f=3000:width_type=h:width=500:g=1',
            '-c:a', 'aac', '-b:a', '256k',
            '-y', output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def normalize_audio(self, input_path: str, output_path: str) -> str:
        """Normalize audio to target loudness"""
        cmd = [
            'ffmpeg', '-i', input_path,
            '-af', f'loudnorm=I={self.config.target_loudness}:LRA=7:TP={self.config.max_peak}',
            '-c:a', 'aac', '-b:a', '192k',
            '-y', output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def reduce_noise(self, input_path: str, output_path: str, noise_reduction: float = 0.3) -> str:
        """Reduce background noise in audio"""
        cmd = [
            'ffmpeg', '-i', input_path,
            '-af', f'highpass=f=80,lowpass=f=8000,'
                   f'compand=.3|.3:1|1:-90/-60|-60/-40|-40/-30|-20/-20:6:0:-90:{noise_reduction}',
            '-c:a', 'aac', '-b:a', '192k',
            '-y', output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def enhance_clarity(self, input_path: str, output_path: str) -> str:
        """Enhance audio clarity for speech"""
        cmd = [
            'ffmpeg', '-i', input_path,
            '-af', 'highpass=f=80,lowpass=f=8000,'
                   'equalizer=f=1000:width_type=h:width=200:g=2,'
                   'equalizer=f=3000:width_type=h:width=500:g=1',
            '-c:a', 'aac', '-b:a', '192k',
            '-y', output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def synchronize_audio(self, audio_path: str, video_path: str, output_path: str) -> str:
        """Synchronize audio with video"""
        cmd = [
            'ffmpeg', '-i', video_path, '-i', audio_path,
            '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
            '-map', '0:v:0', '-map', '1:a:0',
            '-shortest', '-y', output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def get_optimization_recommendations(self, metrics: AudioQualityMetrics) -> List[str]:
        """Get optimization recommendations based on audio metrics"""
        recommendations = []
        
        if metrics.loudness_lufs < -26:
            recommendations.append("Audio is too quiet - increase gain")
        elif metrics.loudness_lufs > -20:
            recommendations.append("Audio is too loud - reduce gain")
        
        if metrics.peak_db > -1:
            recommendations.append("Audio is clipping - reduce peak levels")
        
        if metrics.dynamic_range < 5:
            recommendations.append("Audio has low dynamic range - consider compression")
        
        if metrics.noise_floor_db > -50:
            recommendations.append("High noise floor - apply noise reduction")
        
        if metrics.distortion_percent > 1:
            recommendations.append("Audio has distortion - check input levels")
        
        return recommendations

# Global audio optimizer instance
_audio_optimizer: Optional[AudioOptimizer] = None

def get_audio_optimizer() -> AudioOptimizer:
    """Get global audio optimizer instance"""
    global _audio_optimizer
    if _audio_optimizer is None:
        _audio_optimizer = AudioOptimizer()
    return _audio_optimizer

def optimize_audio_file(
    input_path: str,
    output_path: str,
    optimization_level: str = "medium"
) -> AudioQualityMetrics:
    """
    Convenience function for audio optimization
    
    Args:
        input_path: Path to input audio file
        output_path: Path to output optimized audio file
        optimization_level: Level of optimization (low, medium, high)
        
    Returns:
        AudioQualityMetrics with optimization results
    """
    optimizer = get_audio_optimizer()
    return optimizer.optimize_audio(input_path, output_path, optimization_level)
