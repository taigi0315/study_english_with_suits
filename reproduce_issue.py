
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
                        print(f"  > New Best (Substring): '{clean_dialogue}' Score: {score:.2f} (idx {j})")
                        best_score = score
                        best_match_idx = j
                
                # 2. Accumulated Match
                if test_accumulated in clean_dialogue:
                    accumulated_score = len(test_accumulated.split()) / max(len(clean_dialogue.split()), 1)
                    if accumulated_score > best_score:
                        print(f"  > New Best (Accumulated): '{clean_dialogue}' Score: {accumulated_score:.2f} (idx {j})")
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

# Hypothetical Scenario: Proximity Override
dialogues = [
    "I",              # 0 (Short dialogue)
    "I see."          # 1
]

subtitles = [
    {"text": "I"},    # Matches 0 (Substring), Matches 1 (Fuzzy+Bonus)
]

print("Test Case 1: Short 'I' match")
matcher = SubtitleMatcher()
result = matcher._map_subtitles_to_dialogues(subtitles, dialogues)
print("Final Mapping:", result)
print("Expected: [0]")

# Test Case 2: The Suit Case with Partial Match
print("\nTest Case 2: Suit Case")
dialogues_suit = [
    "but you know, I-I-I had some extra time.",   # 0
    "So I insisted."                              # 1
]
# Simulate a scenario where 'but you know' is processed, state is -1
subtitles_suit = [
    {"text": "but you know I"}, # 'I' also appears in next line?
]

matcher_suit = SubtitleMatcher()
result_suit = matcher_suit._map_subtitles_to_dialogues(subtitles_suit, dialogues_suit)
print("Final Mapping:", result_suit)
