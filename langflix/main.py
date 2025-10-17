import argparse
from langflix.subtitle_parser import parse_subtitle_file, chunk_subtitles

def main():
    """
    Main function to run the LangFlix processing pipeline.
    """
    parser = argparse.ArgumentParser(description="Generate English learning videos from TV shows.")
    parser.add_argument("subtitle_file", help="Path to the .srt subtitle file.")
    # parser.add_argument("video_file", help="Path to the video file.") # To be used in Phase 2
    args = parser.parse_args()

    print(f"Processing subtitle file: {args.subtitle_file}")

    # Phase 1: Parse and Chunk Subtitles
    subtitles = parse_subtitle_file(args.subtitle_file)
    if not subtitles:
        print("Could not parse subtitles. Exiting.")
        return

    subtitle_chunks = chunk_subtitles(subtitles)
    print(f"Split subtitles into {len(subtitle_chunks)} chunks to fit LLM context window.")

    # The next step will be to feed these chunks into the expression analyzer.
    # For now, we'll just print the number of chunks.

if __name__ == "__main__":
    main()
