#!/usr/bin/env python3
"""
YouTube API 인증 테스트 스크립트
"""
import os
import sys
import logging
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def test_youtube_authentication():
    """YouTube API 인증 테스트"""
    try:
        logger.info("🔐 YouTube API 인증 테스트 시작...")
        
        # YouTube 업로더 임포트
        from langflix.youtube.uploader import YouTubeUploader
        
        # 인증 파일 경로 확인
        credentials_file = "youtube_credentials.json"
        if not os.path.exists(credentials_file):
            logger.error(f"❌ 인증 파일을 찾을 수 없습니다: {credentials_file}")
            return False
        
        logger.info(f"✅ 인증 파일 발견: {credentials_file}")
        
        # YouTube 업로더 초기화
        uploader = YouTubeUploader(credentials_file=credentials_file)
        logger.info("✅ YouTubeUploader 초기화 완료")
        
        # 인증 시도
        logger.info("🔑 YouTube API 인증 시도 중...")
        success = uploader.authenticate()
        
        if success:
            logger.info("✅ YouTube API 인증 성공!")
            
            # 간단한 API 테스트 (채널 정보 가져오기)
            try:
                logger.info("📺 YouTube API 연결 테스트 중...")
                # YouTube 서비스가 제대로 초기화되었는지 확인
                if uploader.service:
                    logger.info("✅ YouTube API 서비스 연결 확인됨")
                    
                    # 간단한 API 호출 테스트
                    response = uploader.service.channels().list(
                        part='snippet',
                        mine=True
                    ).execute()
                    
                    if response.get('items'):
                        channel = response['items'][0]
                        channel_title = channel['snippet']['title']
                        logger.info(f"✅ 채널 정보 확인: {channel_title}")
                    else:
                        logger.warning("⚠️ 채널 정보를 가져올 수 없습니다")
                    
                    return True
                else:
                    logger.error("❌ YouTube API 서비스가 초기화되지 않았습니다")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ YouTube API 테스트 실패: {e}")
                return False
        else:
            logger.error("❌ YouTube API 인증 실패")
            return False
            
    except ImportError as e:
        logger.error(f"❌ 모듈 임포트 실패: {e}")
        logger.error("필요한 패키지가 설치되어 있는지 확인하세요:")
        logger.error("pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        return False
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류: {e}")
        return False

def test_video_manager():
    """비디오 매니저 테스트"""
    try:
        logger.info("📁 비디오 매니저 테스트 시작...")
        
        from langflix.youtube.video_manager import VideoFileManager
        
        # 비디오 매니저 초기화
        video_manager = VideoFileManager("output")
        logger.info("✅ VideoFileManager 초기화 완료")
        
        # 비디오 스캔 테스트
        videos = video_manager.scan_all_videos()
        logger.info(f"📊 발견된 비디오 파일: {len(videos)}개")
        
        if videos:
            for i, video in enumerate(videos[:3]):  # 처음 3개만 표시
                logger.info(f"  {i+1}. {video.filename} ({video.video_type}, {video.duration_formatted})")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 비디오 매니저 테스트 실패: {e}")
        return False

def test_metadata_generator():
    """메타데이터 생성기 테스트"""
    try:
        logger.info("📝 메타데이터 생성기 테스트 시작...")
        
        from langflix.youtube.metadata_generator import YouTubeMetadataGenerator
        
        # 메타데이터 생성기 초기화
        generator = YouTubeMetadataGenerator()
        logger.info("✅ YouTubeMetadataGenerator 초기화 완료")
        
        # 사용 가능한 템플릿 확인
        templates = generator.get_available_templates()
        logger.info(f"📋 사용 가능한 템플릿: {', '.join(templates)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 메타데이터 생성기 테스트 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    logger.info("🚀 LangFlix YouTube 통합 테스트 시작")
    logger.info("=" * 60)
    
    tests = [
        ("YouTube API 인증", test_youtube_authentication),
        ("비디오 매니저", test_video_manager),
        ("메타데이터 생성기", test_metadata_generator),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 {test_name} 테스트 중...")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                logger.info(f"✅ {test_name} 테스트 통과")
            else:
                logger.error(f"❌ {test_name} 테스트 실패")
        except Exception as e:
            logger.error(f"❌ {test_name} 테스트 중 오류: {e}")
            results.append((test_name, False))
    
    # 결과 요약
    logger.info("\n" + "=" * 60)
    logger.info("📊 테스트 결과 요약:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        logger.info(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n🎯 전체 결과: {passed}/{len(results)} 테스트 통과")
    
    if passed == len(results):
        logger.info("🎉 모든 테스트가 성공했습니다! YouTube 통합이 준비되었습니다.")
        return True
    else:
        logger.warning("⚠️ 일부 테스트가 실패했습니다. 문제를 해결한 후 다시 시도하세요.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
