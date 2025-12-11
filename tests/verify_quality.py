import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))

from langflix.core.video_editor import VideoEditor
from langflix import settings

def test_video_args():
    print("Testing Video Quality Settings...")
    
    # Check settings directly
    print(f"Settings CRF: {settings.get_video_config().get('crf')}")
    print(f"Settings Preset: {settings.get_video_config().get('preset')}")
    
    # Check VideoEditor args
    try:
        editor = VideoEditor(output_dir=Path("test_output"))
        args = editor._get_video_output_args()
        print("\nVideoEditor._get_video_output_args():")
        for k, v in args.items():
            print(f"  {k}: {v}")
            
        if args.get('crf') != 18:
            print("FAILURE: CRF is not 18")
            sys.exit(1)
            
        if args.get('preset') not in ['slow', 'medium']:
            print(f"FAILURE: Preset is {args.get('preset')}, expected slow/medium")
            sys.exit(1)
            
        print("\nSUCCESS: Quality settings verified.")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        # If initialization fails due to missing deps, we might need to mock
        sys.exit(1)

if __name__ == "__main__":
    test_video_args()
