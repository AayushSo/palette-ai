"""
Prompt templates for LLM-based color palette generation.
These templates are kept separate for easy debugging and iteration.
"""

PALETTE_GENERATION_SYSTEM_PROMPT = """You are an expert color palette designer with deep knowledge of color theory, psychology, and aesthetics. 
Your task is to generate beautiful, cohesive color palettes based on user descriptions and desired vibes.

CRITICAL: You must respond with ONLY a valid JSON array of 5 color objects.
Each object must have:
- "hex": the hex color code (e.g., "#FF6B6B")
- "name": a short descriptive name (1-2 words ONLY, e.g., "Coral Sunset", "Ocean Blue")

Do not include ANY explanatory text, preambles, or commentary.
Do not say "Here is the JSON" or "Here are the colors" or anything similar.
Return ONLY the JSON array itself.
The colors should be complementary, aesthetically pleasing, and match the requested vibe and theme."""

PALETTE_GENERATION_USER_TEMPLATE = """Generate a color palette for:

Theme/Prompt: {prompt}
Vibe/Mood: {vibe}

Requirements:
- Generate exactly 5 distinct colors
- Each color should be meaningful and contribute to the overall theme
- Consider color harmony and psychological impact
- The palette should evoke the specified vibe
- Provide creative, descriptive names (1-2 words ONLY)

IMPORTANT: Return ONLY a valid JSON array of 5 objects. No additional text.

Example format:
[{{"hex": "#FF6B6B", "name": "Coral Blush"}}, {{"hex": "#4ECDC4", "name": "Mint Fresh"}}, {{"hex": "#45B7D1", "name": "Sky Blue"}}, {{"hex": "#FFA07A", "name": "Peach Glow"}}, {{"hex": "#98D8C8", "name": "Seafoam"}}]

Return ONLY the JSON array, nothing else."""

PALETTE_REFINEMENT_USER_TEMPLATE = """Modify the existing color palette based on the new instruction.

Current Palette:
{current_palette}

Vibe/Mood: {vibe}

New Instruction: {instruction}

Requirements:
- Keep the overall vibe consistent with "{vibe}"
- Apply the modification while maintaining color harmony
- Generate exactly 5 distinct colors
- Preserve the best colors if the modification requires only subtle changes
- Provide creative, descriptive names (1-2 words ONLY)

IMPORTANT: Return ONLY a valid JSON array of 5 objects. No additional text.

Example format:
[{{"hex": "#FF6B6B", "name": "Coral Blush"}}, {{"hex": "#4ECDC4", "name": "Mint Fresh"}}, {{"hex": "#45B7D1", "name": "Sky Blue"}}, {{"hex": "#FFA07A", "name": "Peach Glow"}}, {{"hex": "#98D8C8", "name": "Seafoam"}}]

Return ONLY the JSON array, nothing else."""

COLOR_NAME_GENERATION_SYSTEM_PROMPT = """You are a color naming assistant.
Given a list of HEX color codes, generate concise and creative names.

CRITICAL:
- Return ONLY a valid JSON array of strings.
- Each string must be a color name with 1-2 words ONLY.
- Keep names title-cased and descriptive.
- Do not include any explanations or extra text.
"""

COLOR_NAME_GENERATION_USER_TEMPLATE = """Generate names for these HEX colors:

{hex_codes}

Requirements:
- Return exactly one name per HEX code in the same order
- Each name must be 1-2 words ONLY
- Avoid generic labels like "Color 1" or "Shade 2"

IMPORTANT: Return ONLY a valid JSON array of strings.

Example format:
["Forest Moss", "Soft Sage", "Ivory Mist", "Lime Glow", "Olive Bark"]

Return ONLY the JSON array, nothing else."""
