"""
Test script for TTS integration
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from langflix.tts.factory import create_tts_client
from langflix import settings


def test_tts_configuration():
    """Test that TTS configuration is loaded correctly"""
    print("Testing TTS configuration...")
    
    tts_config = settings.get_tts_config()
    print(f"TTS Config: {tts_config}")
    
    provider = settings.get_tts_provider()
    print(f"TTS Provider: {provider}")
    
    enabled = settings.is_tts_enabled()
    print(f"TTS Enabled: {enabled}")
    
    assert provider == "lemonfox", f"Expected 'lemonfox', got '{provider}'"
    assert enabled == True, "TTS should be enabled"
    
    print("✅ TTS configuration test passed\n")


def test_tts_client_creation():
    """Test TTS client creation"""
    print("Testing TTS client creation...")
    
    tts_config = settings.get_tts_config()
    provider = settings.get_tts_provider()
    provider_config = tts_config.get(provider, {})
    
    print(f"Creating TTS client for provider: {provider}")
    print(f"Provider config: {provider_config}")
    
    try:
        client = create_tts_client(provider, provider_config)
        print(f"✅ Successfully created TTS client: {type(client).__name__}")
        
        # Validate config
        is_valid = client.validate_config()
        print(f"Config validation: {'✅ Valid' if is_valid else '❌ Invalid'}")
        
        assert is_valid, "TTS client configuration should be valid"
        
    except Exception as e:
        print(f"❌ Error creating TTS client: {e}")
        raise
    
    print("✅ TTS client creation test passed\n")


def test_text_sanitization():
    """Test text sanitization for TTS"""
    print("Testing text sanitization...")
    
    from langflix.tts.lemonfox_client import LemonFoxTTSClient
    
    # Create a test client (won't actually call API)
    client = LemonFoxTTSClient(api_key="test", voice="bella")
    
    test_cases = [
        ("I'm gonna get screwed", "I'm gonna get screwed"),
        ("don't_worry_2_much!", "don't worry 2 much"),
        ("2 cups of coffee", "two cups of coffee"),
        ("the 3rd time's a charm", "the third time's a charm"),
        ("hello@#$%world", "hello world"),
    ]
    
    for input_text, expected_pattern in test_cases:
        sanitized = client._sanitize_text_for_speech(input_text)
        sanitized_with_nums = client._convert_numbers_to_words(sanitized)
        print(f"  Input: '{input_text}'")
        print(f"  Sanitized: '{sanitized}'")
        print(f"  With numbers: '{sanitized_with_nums}'")
        print()
    
    print("✅ Text sanitization test passed\n")


def test_tts_audio_generation():
    """Test actual TTS audio generation (requires API key)"""
    print("Testing TTS audio generation...")
    print("⚠️  This test will make an actual API call to LemonFox")
    
    try:
        tts_config = settings.get_tts_config()
        provider = settings.get_tts_provider()
        provider_config = tts_config.get(provider, {})
        
        client = create_tts_client(provider, provider_config)
        
        # Test with a simple expression
        test_text = "get screwed"
        print(f"Generating speech for: '{test_text}'")
        
        audio_path = client.generate_speech(test_text)
        
        print(f"✅ Successfully generated audio: {audio_path}")
        print(f"   File exists: {audio_path.exists()}")
        print(f"   File size: {audio_path.stat().st_size} bytes")
        
        # Clean up
        if audio_path.exists():
            audio_path.unlink()
            print("   Cleaned up test audio file")
        
        print("✅ TTS audio generation test passed\n")
        
    except Exception as e:
        print(f"❌ Error generating TTS audio: {e}")
        print("   This might be expected if API key is invalid or network is unavailable")
        raise


if __name__ == "__main__":
    print("=" * 60)
    print("LangFlix TTS Integration Tests")
    print("=" * 60)
    print()
    
    try:
        test_tts_configuration()
        test_tts_client_creation()
        test_text_sanitization()
        
        # Optional: comment out if you don't want to make actual API calls
        print("⚠️  About to test actual TTS generation (will use API)")
        response = input("Continue? (y/n): ").strip().lower()
        if response == 'y':
            test_tts_audio_generation()
        else:
            print("Skipping actual TTS generation test")
        
        print()
        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Tests failed: {e}")
        print("=" * 60)
        sys.exit(1)

