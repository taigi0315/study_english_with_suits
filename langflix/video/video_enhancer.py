"""
Video quality enhancement system for LangFlix Expression-Based Learning Feature.

This module provides:
- Intelligent video upscaling
- Frame interpolation
- Color correction
- Stabilization
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
class VideoQualityMetrics:
    """Video quality metrics"""
    resolution: Tuple[int, int]
    fps: float
    bitrate: int
    color_space: str
    color_range: str
    brightness: float
    contrast: float
    saturation: float
    sharpness: float
    noise_level: float

@dataclass
class VideoEnhancementConfig:
    """Video enhancement configuration"""
    target_resolution: Optional[Tuple[int, int]] = None
    target_fps: Optional[float] = None
    target_bitrate: Optional[int] = None
    enhance_sharpness: bool = True
    enhance_colors: bool = True
    stabilize: bool = False
    interpolate_frames: bool = False
    upscale_quality: str = "high"  # low, medium, high

class VideoEnhancer:
    """Advanced video quality enhancement system"""
    
    def __init__(self, config: Optional[VideoEnhancementConfig] = None):
        """
        Initialize video enhancer
        
        Args:
            config: Video enhancement configuration
        """
        self.config = config or VideoEnhancementConfig()
        logger.info("VideoEnhancer initialized")
    
    def enhance_video(
        self,
        input_path: str,
        output_path: str,
        enhancement_level: str = "medium"
    ) -> VideoQualityMetrics:
        """
        Enhance video quality for educational content
        
        Args:
            input_path: Path to input video file
            output_path: Path to output enhanced video file
            enhancement_level: Level of enhancement (low, medium, high)
            
        Returns:
            VideoQualityMetrics with enhancement results
        """
        logger.info(f"Enhancing video: {input_path} -> {output_path}")
        
        # Analyze input video
        input_metrics = self._analyze_video_quality(input_path)
        logger.info(f"Input video metrics: {input_metrics}")
        
        # Apply enhancements based on level
        if enhancement_level == "low":
            enhanced_path = self._apply_basic_enhancement(input_path, output_path)
        elif enhancement_level == "medium":
            enhanced_path = self._apply_medium_enhancement(input_path, output_path)
        elif enhancement_level == "high":
            enhanced_path = self._apply_high_enhancement(input_path, output_path)
        else:
            raise ValueError(f"Invalid enhancement level: {enhancement_level}")
        
        # Analyze output video
        output_metrics = self._analyze_video_quality(enhanced_path)
        logger.info(f"Output video metrics: {output_metrics}")
        
        return output_metrics
    
    def _analyze_video_quality(self, video_path: str) -> VideoQualityMetrics:
        """Analyze video quality metrics using FFprobe"""
        try:
            # Use FFprobe to analyze video
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_streams', '-show_format', video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            # Find video stream
            video_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                raise ValueError("No video stream found")
            
            # Extract metrics
            width = int(video_stream.get('width', 1920))
            height = int(video_stream.get('height', 1080))
            fps = eval(video_stream.get('r_frame_rate', '30/1'))
            bitrate = int(data.get('format', {}).get('bit_rate', 0))
            
            return VideoQualityMetrics(
                resolution=(width, height),
                fps=fps,
                bitrate=bitrate,
                color_space=video_stream.get('color_space', 'unknown'),
                color_range=video_stream.get('color_range', 'unknown'),
                brightness=0.5,  # Placeholder - would need advanced analysis
                contrast=0.5,
                saturation=0.5,
                sharpness=0.5,
                noise_level=0.1
            )
            
        except Exception as e:
            logger.warning(f"Failed to analyze video quality: {e}")
            return VideoQualityMetrics(
                resolution=(1920, 1080), fps=30.0, bitrate=5000000,
                color_space='unknown', color_range='unknown',
                brightness=0.5, contrast=0.5, saturation=0.5,
                sharpness=0.5, noise_level=0.1
            )
    
    def _apply_basic_enhancement(self, input_path: str, output_path: str) -> str:
        """Apply basic video enhancement"""
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', 'unsharp=5:5:0.8:3:3:0.4',  # Basic sharpening
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-c:a', 'aac', '-b:a', '192k',
            '-y', output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def _apply_medium_enhancement(self, input_path: str, output_path: str) -> str:
        """Apply medium video enhancement"""
        filters = [
            'unsharp=5:5:0.8:3:3:0.4',  # Sharpening
            'eq=brightness=0.05:contrast=1.1:saturation=1.1',  # Color enhancement
        ]
        
        if self.config.stabilize:
            filters.insert(0, 'vidstabdetect=stepsize=6:shakiness=8:accuracy=9:result=transforms.trf')
        
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', ','.join(filters),
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
            '-c:a', 'aac', '-b:a', '256k',
            '-y', output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def _apply_high_enhancement(self, input_path: str, output_path: str) -> str:
        """Apply high video enhancement"""
        filters = [
            'unsharp=5:5:0.8:3:3:0.4',  # Sharpening
            'eq=brightness=0.05:contrast=1.1:saturation=1.1',  # Color enhancement
            'hqdn3d=4:3:6:4.5',  # Noise reduction
        ]
        
        if self.config.stabilize:
            filters.insert(0, 'vidstabdetect=stepsize=6:shakiness=8:accuracy=9:result=transforms.trf')
        
        if self.config.interpolate_frames:
            filters.append('minterpolate=fps=60:mi_mode=mci')  # Frame interpolation
        
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', ','.join(filters),
            '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
            '-c:a', 'aac', '-b:a', '320k',
            '-y', output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def upscale_video(
        self,
        input_path: str,
        output_path: str,
        target_resolution: Tuple[int, int],
        upscale_quality: str = "high"
    ) -> str:
        """Upscale video to target resolution"""
        width, height = target_resolution
        
        if upscale_quality == "high":
            # Use advanced upscaling
            cmd = [
                'ffmpeg', '-i', input_path,
                '-vf', f'scale={width}:{height}:flags=lanczos',
                '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                '-c:a', 'aac', '-b:a', '256k',
                '-y', output_path
            ]
        else:
            # Use standard upscaling
            cmd = [
                'ffmpeg', '-i', input_path,
                '-vf', f'scale={width}:{height}',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
                '-c:a', 'aac', '-b:a', '192k',
                '-y', output_path
            ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def stabilize_video(self, input_path: str, output_path: str) -> str:
        """Stabilize shaky video"""
        # First pass: detect motion
        detect_cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', 'vidstabdetect=stepsize=6:shakiness=8:accuracy=9:result=transforms.trf',
            '-f', 'null', '-'
        ]
        
        subprocess.run(detect_cmd, check=True, capture_output=True)
        
        # Second pass: apply stabilization
        stabilize_cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', 'vidstabtransform=smoothing=10:input=transforms.trf',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-c:a', 'aac', '-b:a', '192k',
            '-y', output_path
        ]
        
        subprocess.run(stabilize_cmd, check=True, capture_output=True)
        return output_path
    
    def enhance_colors(self, input_path: str, output_path: str) -> str:
        """Enhance video colors"""
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', 'eq=brightness=0.05:contrast=1.1:saturation=1.1',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-c:a', 'aac', '-b:a', '192k',
            '-y', output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def reduce_noise(self, input_path: str, output_path: str) -> str:
        """Reduce video noise"""
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', 'hqdn3d=4:3:6:4.5',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-c:a', 'aac', '-b:a', '192k',
            '-y', output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def interpolate_frames(self, input_path: str, output_path: str, target_fps: float = 60.0) -> str:
        """Interpolate frames to increase FPS"""
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', f'minterpolate=fps={target_fps}:mi_mode=mci',
            '-c:v', 'libx264', '-preset', 'slow', '-crf', '20',
            '-c:a', 'aac', '-b:a', '256k',
            '-y', output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def get_enhancement_recommendations(self, metrics: VideoQualityMetrics) -> List[str]:
        """Get enhancement recommendations based on video metrics"""
        recommendations = []
        
        width, height = metrics.resolution
        if width < 1280 or height < 720:
            recommendations.append("Low resolution - consider upscaling")
        
        if metrics.fps < 24:
            recommendations.append("Low frame rate - consider frame interpolation")
        
        if metrics.bitrate < 2000000:
            recommendations.append("Low bitrate - consider re-encoding with higher quality")
        
        if metrics.brightness < 0.3:
            recommendations.append("Dark video - increase brightness")
        elif metrics.brightness > 0.7:
            recommendations.append("Bright video - reduce brightness")
        
        if metrics.contrast < 0.4:
            recommendations.append("Low contrast - increase contrast")
        
        if metrics.saturation < 0.4:
            recommendations.append("Low saturation - increase color saturation")
        
        if metrics.sharpness < 0.4:
            recommendations.append("Blurry video - apply sharpening")
        
        if metrics.noise_level > 0.3:
            recommendations.append("High noise - apply noise reduction")
        
        return recommendations

# Global video enhancer instance
_video_enhancer: Optional[VideoEnhancer] = None

def get_video_enhancer() -> VideoEnhancer:
    """Get global video enhancer instance"""
    global _video_enhancer
    if _video_enhancer is None:
        _video_enhancer = VideoEnhancer()
    return _video_enhancer

def enhance_video_file(
    input_path: str,
    output_path: str,
    enhancement_level: str = "medium"
) -> VideoQualityMetrics:
    """
    Convenience function for video enhancement
    
    Args:
        input_path: Path to input video file
        output_path: Path to output enhanced video file
        enhancement_level: Level of enhancement (low, medium, high)
        
    Returns:
        VideoQualityMetrics with enhancement results
    """
    enhancer = get_video_enhancer()
    return enhancer.enhance_video(input_path, output_path, enhancement_level)
