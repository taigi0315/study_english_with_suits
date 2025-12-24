
import re
from typing import List, Dict, Any

class SubtitleMatcher:
    def _clean_text_for_matching(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _map_subtitles_to_dialogues(self, subtitles: List[Dict[str, Any]], dialogues: List[str]) -> List[int]:
        subtitle_to_dialogue = []
        clean_dialogues = [self._clean_text_for_matching(dialogue) for dialogue in dialogues]
        
        accumulated_text = ""
        current_dialogue_idx = -1
        
        print(f"Mapping {len(subtitles)} subtitles to {len(dialogues)} dialogues")
        
        for i, subtitle in enumerate(subtitles):
            clean_subtitle = self._clean_text_for_matching(subtitle['text'])
            print(f"\nSubtitle {i}: '{clean_subtitle}'")
            
            best_match_idx = -1
            best_score = 0
            
            test_accumulated = (accumulated_text + " " + clean_subtitle).strip()
            
            for j, clean_dialogue in enumerate(clean_dialogues):
                # 1. Exact/Substring Match
                if clean_subtitle in clean_dialogue:
                    score = len(clean_subtitle.split()) / max(len(clean_dialogue.split()), 1)
                    if score > best_score:
                        best_score = score
                        best_match_idx = j
                
                # 2. Accumulated Match
                if test_accumulated in clean_dialogue:
                    accumulated_score = len(test_accumulated.split()) / max(len(clean_dialogue.split()), 1)
                    if accumulated_score > best_score:
                        best_score = accumulated_score
                        best_match_idx = j

                # 3. Fuzzy Match (Integrated with Proximity Bias)
                subtitle_words = set(clean_subtitle.split())
                dialogue_words = set(clean_dialogue.split())
                
                if subtitle_words and dialogue_words:
                    overlap = len(subtitle_words.intersection(dialogue_words))
                    overlap_score = overlap / len(subtitle_words)
                    
                    # Proximity Bonus
                    if j == current_dialogue_idx + 1:
                        overlap_score *= 1.5
                    elif j == current_dialogue_idx:
                        overlap_score *= 1.1
                        
                    if overlap_score > 0.5 and overlap_score > best_score:
                        print(f"  > New Best (Fuzzy): '{clean_dialogue}' Score: {overlap_score:.2f} (idx {j})")
                        best_score = overlap_score
                        best_match_idx = j

            # Update accumulated text and current dialogue index
            if best_match_idx >= 0:
                if best_match_idx != current_dialogue_idx:
                    print(f"  -> MATCHED Index {best_match_idx} (Switching from {current_dialogue_idx})")
                    accumulated_text = clean_subtitle
                    current_dialogue_idx = best_match_idx
                else:
                    print(f"  -> MATCHED Index {best_match_idx} (Accumulating)")
                    accumulated_text = test_accumulated
            else:
                if current_dialogue_idx >= 0:
                    print(f"  -> NO MATCH. Fallback to {current_dialogue_idx}")
                    best_match_idx = current_dialogue_idx
                    accumulated_text = test_accumulated
                else:
                    print(f"  -> NO MATCH. No fallback.")
            
            subtitle_to_dialogue.append(best_match_idx)
            
        return subtitle_to_dialogue

# Test Data
dialogues = [
    "I've got to get my act together.",           # 0 (106)
    "Dude, look at me.",                          # 1 (107)
    "You can burn bud and still be a success.",   # 2 (108)
    "You sell pot for a living.",                 # 3 (109)
    "Still saps the motivation."                  # 4 (110)
]

subtitles = [
    {"text": "I've got to get"},
    {"text": "my act together."},
    {"text": "Dude, look at me."},
    {"text": "You can burn bud"},
    {"text": "and still be a success."},
    {"text": "You sell pot for a living."}
]

matcher = SubtitleMatcher()
result = matcher._map_subtitles_to_dialogues(subtitles, dialogues)
print("\nFinal Mapping:", result)
print("Expected: [0, 0, 1, 2, 2, 3]")
