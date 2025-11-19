# Background Music System for Video Clips

## 1. List of Scene Vibes/Moods in Drama/Show/Movie

### Core Emotional Categories (12 Essential Moods)

1. **Comedic/Funny** - Light, playful, humorous moments
2. **Tense/Suspenseful** - Building tension, anticipation, nail-biting moments
3. **Dramatic/Serious** - Heavy emotional moments, important revelations
4. **Romantic/Tender** - Intimate, sweet, heartfelt moments
5. **Action/Energetic** - Fast-paced, dynamic, exciting scenes
6. **Melancholic/Sad** - Emotional loss, disappointment, reflection
7. **Mysterious/Intriguing** - Puzzles, secrets, investigation
8. **Triumphant/Victorious** - Success, achievement, breakthrough moments
9. **Confrontational/Angry** - Arguments, conflicts, heated exchanges
10. **Inspirational/Uplifting** - Motivational, hopeful, encouraging
11. **Awkward/Uncomfortable** - Cringe, embarrassing, socially tense
12. **Reflective/Contemplative** - Thoughtful, introspective, quiet moments

---

## 2. Music Creation Prompts (Instrumental Only)

### **1. COMEDIC/FUNNY**
**Prompt for Music Generation:**
```
Create a light, playful instrumental track with upbeat tempo (120-140 BPM). Use pizzicato strings, xylophone, ukulele, or quirky synth sounds. Include bouncy rhythms and whimsical melodies that evoke sitcom or comedy sketches. Add occasional comedic accents (boings, whistles). Keep it fun and not too serious. Duration: 30-45 seconds, seamless loop.
```

### **2. TENSE/SUSPENSEFUL**
**Prompt for Music Generation:**
```
Create a suspenseful instrumental with slow build-up (80-100 BPM). Use low strings (cellos, basses), subtle percussion (ticking clocks, heartbeat-like drums), and atmospheric synth pads. Include rising tension with crescendos. Think thriller/mystery vibes - keep listeners on edge. Minimal melody, focus on atmosphere and building anxiety. Duration: 30-45 seconds, seamless loop.
```

### **3. DRAMATIC/SERIOUS**
**Prompt for Music Generation:**
```
Create a serious, emotional instrumental (70-90 BPM). Use full orchestra with emphasis on strings and piano. Include dramatic swells and powerful chord progressions. Evoke gravitas and weight - suitable for important conversations or revelations. Think prestige drama or courtroom scenes. Duration: 30-45 seconds, seamless loop.
```

### **4. ROMANTIC/TENDER**
**Prompt for Music Generation:**
```
Create a warm, intimate instrumental (60-80 BPM). Use soft piano, acoustic guitar, light strings, and gentle pads. Melody should be sweet and flowing. Evoke feelings of love, warmth, and connection. Suitable for heartfelt moments between characters. Keep it gentle and non-intrusive. Duration: 30-45 seconds, seamless loop.
```

### **5. ACTION/ENERGETIC**
**Prompt for Music Generation:**
```
Create a high-energy instrumental (140-160 BPM). Use driving drums, electric guitars, aggressive synths, and punchy bass. Include dynamic rhythms and powerful hooks. Evoke adrenaline, movement, and excitement. Suitable for chases, fights, or intense competitive moments. Duration: 30-45 seconds, seamless loop.
```

### **6. MELANCHOLIC/SAD**
**Prompt for Music Generation:**
```
Create a somber, emotional instrumental (50-70 BPM). Use solo piano or strings with sparse arrangement. Include minor keys and descending melodies. Evoke sadness, loss, or disappointment. Suitable for emotional goodbyes or contemplative sad moments. Keep it understated and poignant. Duration: 30-45 seconds, seamless loop.
```

### **7. MYSTERIOUS/INTRIGUING**
**Prompt for Music Generation:**
```
Create an intriguing instrumental with mid-tempo (90-110 BPM). Use ambient textures, light percussion, celesta, harp, and subtle electronic elements. Include mysterious harmonic progressions and unexpected accents. Evoke curiosity and investigation. Suitable for puzzle-solving or uncovering secrets. Duration: 30-45 seconds, seamless loop.
```

### **8. TRIUMPHANT/VICTORIOUS**
**Prompt for Music Generation:**
```
Create an uplifting, victorious instrumental (110-130 BPM). Use full orchestra with prominent brass, soaring strings, and epic drums. Include heroic melodies and major key progressions. Evoke achievement, success, and breakthrough moments. Think sports victory or overcoming obstacles. Duration: 30-45 seconds, seamless loop.
```

### **9. CONFRONTATIONAL/ANGRY**
**Prompt for Music Generation:**
```
Create an aggressive, intense instrumental (100-130 BPM). Use heavy percussion, distorted guitars, aggressive strings, and dissonant harmonies. Include sharp accents and driving rhythms. Evoke conflict, anger, and heated arguments. Suitable for tense confrontations or explosive moments. Duration: 30-45 seconds, seamless loop.
```

### **10. INSPIRATIONAL/UPLIFTING**
**Prompt for Music Generation:**
```
Create an inspiring, hopeful instrumental (100-120 BPM). Use piano, acoustic guitar, strings, and uplifting synth pads. Include building dynamics from soft to powerful. Evoke motivation, hope, and positive change. Suitable for pep talks or characters finding courage. Think motivational speech background. Duration: 30-45 seconds, seamless loop.
```

### **11. AWKWARD/UNCOMFORTABLE**
**Prompt for Music Generation:**
```
Create an uncomfortable, quirky instrumental (90-110 BPM). Use off-kilter rhythms, dissonant notes, awkward pauses, and unusual instrument combinations (kazoo, theremin, prepared piano). Include jarring transitions. Evoke social awkwardness and cringe moments. Think awkward silence or embarrassing situations. Duration: 30-45 seconds, seamless loop.
```

### **12. REFLECTIVE/CONTEMPLATIVE**
**Prompt for Music Generation:**
```
Create a thoughtful, introspective instrumental (60-80 BPM). Use ambient pads, soft piano, light strings, and minimal percussion. Include gentle, flowing melodies with space between notes. Evoke quiet reflection and inner thought. Suitable for characters processing emotions or making decisions. Keep it calm and meditative. Duration: 30-45 seconds, seamless loop.
```

---

## 3. Music Descriptions for LLM Selection

These descriptions will be provided to the LLM to help it choose the appropriate background music for each video clip.

```json
{
  "music_library": [
    {
      "id": "comedic_funny",
      "name": "Comedic/Funny",
      "description": "Light, playful, and bouncy music with quirky sounds. Perfect for humorous dialogues, witty comebacks, funny misunderstandings, or comedic situations. Use when the scene is meant to make viewers laugh or smile.",
      "best_for": ["humor", "comedy", "playful banter", "funny moments", "sitcom-style exchanges"],
      "avoid_for": ["serious topics", "emotional moments", "tense situations"]
    },
    {
      "id": "tense_suspenseful",
      "name": "Tense/Suspenseful",
      "description": "Dark, atmospheric music with building tension. Perfect for mysteries, secrets being revealed, characters in danger, or moments where something important is about to happen. Creates anticipation and keeps viewers on edge.",
      "best_for": ["tension", "suspense", "mystery", "secrets", "dangerous situations", "cliffhangers"],
      "avoid_for": ["light-hearted moments", "comedy", "romance"]
    },
    {
      "id": "dramatic_serious",
      "name": "Dramatic/Serious",
      "description": "Powerful orchestral music with emotional weight. Perfect for important conversations, major revelations, life-changing decisions, or confronting difficult truths. Adds gravitas to serious moments.",
      "best_for": ["drama", "serious conversations", "important revelations", "emotional confrontations", "heavy topics"],
      "avoid_for": ["comedy", "light moments", "romantic scenes"]
    },
    {
      "id": "romantic_tender",
      "name": "Romantic/Tender",
      "description": "Soft, warm music with gentle melodies. Perfect for intimate conversations, expressions of affection, vulnerable moments between characters, or budding romance. Creates emotional warmth.",
      "best_for": ["romance", "tender moments", "intimate conversations", "emotional vulnerability", "heartfelt exchanges"],
      "avoid_for": ["action", "comedy", "confrontations"]
    },
    {
      "id": "action_energetic",
      "name": "Action/Energetic",
      "description": "Fast-paced, driving music with powerful beats. Perfect for high-stakes situations, competitive moments, urgent deadlines, or characters taking decisive action. Creates excitement and momentum.",
      "best_for": ["action", "fast-paced scenes", "competition", "urgent situations", "decisive moments", "high energy"],
      "avoid_for": ["quiet moments", "sadness", "romance"]
    },
    {
      "id": "melancholic_sad",
      "name": "Melancholic/Sad",
      "description": "Slow, somber music with emotional depth. Perfect for losses, disappointments, goodbyes, regrets, or characters dealing with sadness. Evokes empathy and emotional resonance.",
      "best_for": ["sadness", "loss", "disappointment", "regret", "emotional pain", "goodbyes"],
      "avoid_for": ["comedy", "action", "triumphant moments"]
    },
    {
      "id": "mysterious_intriguing",
      "name": "Mysterious/Intriguing",
      "description": "Subtle, curious music with atmospheric sounds. Perfect for investigation, discovering clues, puzzling situations, or characters figuring things out. Creates intrigue without overwhelming tension.",
      "best_for": ["mystery", "investigation", "discovery", "puzzles", "curious situations", "uncovering secrets"],
      "avoid_for": ["romance", "high action", "obvious comedy"]
    },
    {
      "id": "triumphant_victorious",
      "name": "Triumphant/Victorious",
      "description": "Uplifting, heroic music with powerful crescendos. Perfect for victories, breakthroughs, achieving goals, overcoming obstacles, or moments of success. Celebrates accomplishment.",
      "best_for": ["triumph", "victory", "success", "breakthrough", "achievement", "overcoming obstacles"],
      "avoid_for": ["sadness", "tension", "failure moments"]
    },
    {
      "id": "confrontational_angry",
      "name": "Confrontational/Angry",
      "description": "Aggressive, intense music with sharp accents. Perfect for heated arguments, explosive confrontations, betrayals revealed, or characters in conflict. Amplifies emotional intensity.",
      "best_for": ["confrontation", "arguments", "anger", "conflict", "betrayal", "heated exchanges"],
      "avoid_for": ["comedy", "romance", "quiet moments"]
    },
    {
      "id": "inspirational_uplifting",
      "name": "Inspirational/Uplifting",
      "description": "Hopeful, motivating music that builds gradually. Perfect for pep talks, characters finding courage, realizations of hope, or turning points. Encourages and uplifts without being overly dramatic.",
      "best_for": ["inspiration", "motivation", "hope", "encouragement", "finding courage", "positive turning points"],
      "avoid_for": ["sadness", "tension", "confrontation"]
    },
    {
      "id": "awkward_uncomfortable",
      "name": "Awkward/Uncomfortable",
      "description": "Quirky, off-kilter music with unusual sounds. Perfect for cringe moments, social awkwardness, embarrassing situations, or uncomfortable silences. Emphasizes the awkwardness comedically.",
      "best_for": ["awkwardness", "cringe", "embarrassment", "uncomfortable situations", "social mishaps"],
      "avoid_for": ["serious drama", "romance", "action"]
    },
    {
      "id": "reflective_contemplative",
      "name": "Reflective/Contemplative",
      "description": "Calm, thoughtful music with space for reflection. Perfect for characters processing emotions, making decisions, internal monologues, or quiet moments of realization. Creates introspective atmosphere.",
      "best_for": ["reflection", "contemplation", "processing emotions", "decision-making", "quiet realizations"],
      "avoid_for": ["action", "comedy", "intense confrontation"]
    }
  ]
}
```

---

## 4. LLM Prompt for Music Selection

```
You will receive a video clip with the following information:
- Scene dialogue
- Scene type (humor, drama, tension, etc.)
- Expression being taught
- Context and emotional tone

Your task: Select the MOST APPROPRIATE background music from the provided music library.

Available Music:
{music_library_json}

Selection Criteria:
1. Match the PRIMARY emotional tone of the scene
2. Consider the scene_type field
3. Ensure music ENHANCES learning without distracting
4. Avoid music that contradicts the scene's mood
5. When in doubt, choose more subtle music over dramatic

Output Format (JSON):
{
  "selected_music_id": "the_id_of_chosen_music",
  "reasoning": "Brief explanation of why this music fits the scene"
}
```

---

## Implementation Notes

1. **Music Generation**: Use AI music generation tools (e.g., Suno, MusicGen, AIVA) with the provided prompts
2. **File Naming**: Save as `{music_id}.mp3` (e.g., `comedic_funny.mp3`)
3. **Volume Mixing**: Background music should be 20-30% of dialogue volume
4. **Fade In/Out**: Apply 1-2 second fade in/out for smooth transitions
5. **Loop Readiness**: Ensure all tracks loop seamlessly for varying clip lengths