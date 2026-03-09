"""
Prompt templates for LLM-based color palette generation.
These templates are kept separate for easy debugging and iteration.
"""

PALETTE_GENERATION_SYSTEM_PROMPT = """You are an expert color palette designer with deep knowledge of color theory, psychology, and aesthetics. 
Your task is to generate beautiful, cohesive color palettes based on user descriptions and desired vibes.

CRITICAL: You must respond with ONLY a valid JSON array of 5 hex color codes. 
Do not include ANY explanatory text, preambles, or commentary.
Do not say "Here is the JSON" or "Here are the colors" or anything similar.
Return ONLY the JSON array itself: ["#XXXXXX", "#XXXXXX", "#XXXXXX", "#XXXXXX", "#XXXXXX"]
The colors should be complementary, aesthetically pleasing, and match the requested vibe and theme."""

PALETTE_GENERATION_USER_TEMPLATE = """Generate a color palette for:

Theme/Prompt: {prompt}
Vibe/Mood: {vibe}

Requirements:
- Generate exactly 5 distinct hex color codes
- Each color should be meaningful and contribute to the overall theme
- Consider color harmony and psychological impact
- The palette should evoke the specified vibe

IMPORTANT: Return ONLY a valid JSON array of 5 hex color codes. No descriptions, no additional text.

Example format:
["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8"]

Return ONLY the JSON array, nothing else."""

PALETTE_REFINEMENT_USER_TEMPLATE = """Modify the existing color palette based on the new instruction.

Current Palette (hex codes):
{current_palette}

Vibe/Mood: {vibe}

New Instruction: {instruction}

Requirements:
- Keep the overall vibe consistent with "{vibe}"
- Apply the modification while maintaining color harmony
- Generate exactly 5 distinct hex color codes
- Preserve the best colors if the modification requires only subtle changes

IMPORTANT: Return ONLY a valid JSON array of 5 hex color codes. No descriptions, no additional text.

Example format:
["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8"]

Return ONLY the JSON array, nothing else."""
