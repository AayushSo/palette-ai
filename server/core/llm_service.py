from typing import List, Dict
import os
import json
import re
import logging
import tempfile
from datetime import datetime
from pathlib import Path
import httpx
import base64
from PIL import Image
import io

from core.prompts import (
    PALETTE_GENERATION_SYSTEM_PROMPT,
    PALETTE_GENERATION_USER_TEMPLATE,
    PALETTE_REFINEMENT_USER_TEMPLATE,
    COLOR_NAME_GENERATION_SYSTEM_PROMPT,
    COLOR_NAME_GENERATION_USER_TEMPLATE,
)

# Configure logging
logger = logging.getLogger(__name__)
DEBUG = os.getenv("DEBUG", "False").lower() == "true"


class LLMPaletteService:
    """
    Service for generating color palettes from text prompts using an LLM.
    Provides abstraction for different LLM providers (OpenAI, Anthropic, etc).
    Currently implemented: Google Gemini API
    """

    def __init__(self):
        """Initialize the LLM service with API keys from environment."""
        self.api_key = os.getenv("LLM_API_KEY")
        self.provider = os.getenv("LLM_PROVIDER", "gemini")  # gemini, openai, anthropic, etc.
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self.gemini_api_version = os.getenv("GEMINI_API_VERSION", "v1")
        self.gemini_base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com")
        # Persist raw LLM responses for manual verification.
        self.save_raw_responses = os.getenv("LLM_SAVE_RAW_RESPONSES", "true").lower() == "true"
        self.debug_dump_dir = Path(tempfile.gettempdir()) / "palette-ai-llm"
        
        if DEBUG:
            logger.info(f"🔧 Initializing LLMPaletteService: provider={self.provider}")
            logger.info(f"   model={self.gemini_model}, api_version={self.gemini_api_version}")
        
        if self.provider == "gemini":
            if not self.api_key:
                raise ValueError("LLM_API_KEY environment variable not set for Gemini API")
            if DEBUG:
                logger.info(f"   ✅ Gemini API configured via REST endpoint")

    def _save_raw_response(self, response_text: str, request_type: str, context: Dict[str, str]) -> None:
        """Save raw LLM response into a temp file for easier local debugging."""
        if not self.save_raw_responses:
            return

        self.debug_dump_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        filename = f"{request_type}-{timestamp}.json"
        output_path = self.debug_dump_dir / filename

        payload = {
            "timestamp": datetime.now().isoformat(),
            "request_type": request_type,
            "provider": self.provider,
            "model": self.gemini_model,
            "api_version": self.gemini_api_version,
            "context": context,
            "raw_response": response_text,
        }

        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info(f"   💾 Raw LLM response saved: {output_path}")

    async def _gemini_generate_text(self, message: str, request_type: str, context: Dict[str, str]) -> str:
        """Call Gemini REST API and return the first candidate text."""
        endpoint = (
            f"{self.gemini_base_url}/{self.gemini_api_version}/models/"
            f"{self.gemini_model}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": message}],
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 200,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(endpoint, json=payload)

        if response.status_code >= 400:
            raise ValueError(
                f"Gemini API HTTP {response.status_code}: {response.text[:500]}"
            )

        response_json = response.json()
        text = (
            response_json.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )

        if not text:
            raise ValueError(f"Gemini returned empty text. Response: {json.dumps(response_json)[:500]}")

        self._save_raw_response(response_text=text, request_type=request_type, context=context)
        return text

    async def generate_palette(self, prompt: str, vibe: str = "vibrant") -> Dict:
        """
        Generate a color palette from a text prompt using LLM.
        
        Args:
            prompt: Description of the desired palette
            vibe: Mood/style (e.g., "vibrant", "minimal", "dark", "pastel", "warm", "cool")
        
        Returns:
            Dictionary containing palette and descriptions
        """
        try:
            if DEBUG:
                logger.info(f"🎨 LLMService.generate_palette() called")
                logger.info(f"   prompt: {prompt}")
                logger.info(f"   vibe: {vibe}")
            
            if self.provider == "gemini":
                return await self._call_gemini_api(prompt, vibe)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        
        except Exception as e:
            logger.error(f"Error generating palette from LLM: {str(e)}")
            raise Exception(f"Error generating palette from LLM: {str(e)}")

    async def _call_gemini_api(self, prompt: str, vibe: str) -> Dict:
        """
        Call Google Gemini API to generate palette.
        
        Args:
            prompt: User's palette description
            vibe: Desired mood/style
        
        Returns:
            Generated palette with colors and descriptions
        """
        try:
            if DEBUG:
                logger.info(
                    f"   🔗 Calling Gemini API via REST: model={self.gemini_model}, version={self.gemini_api_version}"
                )
            
            # Build the user message from template
            user_message = PALETTE_GENERATION_USER_TEMPLATE.format(
                prompt=prompt,
                vibe=vibe
            )
            
            response_text = await self._gemini_generate_text(
                message=f"{PALETTE_GENERATION_SYSTEM_PROMPT}\n\n{user_message}",
                request_type="generate",
                context={"prompt": prompt, "vibe": vibe},
            )

            if DEBUG:
                logger.info(f"   ✅ Gemini API responded")
            
            if DEBUG:
                logger.info(f"   📦 Response length: {len(response_text)} chars")
                logger.info(f"   📝 Raw response: {response_text}")  # Show full response
            
            # Try to extract JSON array from response - be more aggressive
            # First, try to find JSON with markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find array of objects anywhere in text
                # Look for pattern like [{...}, {...}]
                json_match = re.search(r'\[\s*\{[^\]]+\}\s*(?:,\s*\{[^\]]+\}\s*)*\]', response_text, re.DOTALL)
                if not json_match:
                    logger.error(f"   ❌ Could not find JSON array in response: {response_text}")
                    raise ValueError(f"No JSON array found in response. Response was: {response_text[:200]}")
                json_str = json_match.group()
            
            if DEBUG:
                logger.info(f"   🔍 Extracted JSON string: {json_str[:200]}...")
            
            # Clean up common JSON issues
            json_str = json_str.replace('\n', ' ').replace('\r', '')
            # Remove trailing commas before closing brackets
            json_str = re.sub(r',\s*]', ']', json_str)
            json_str = re.sub(r',\s*}', '}', json_str)
            
            try:
                color_objects = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"   ❌ JSON Parse Error at position {e.pos}")
                logger.error(f"   📝 Problematic JSON around error:")
                start = max(0, e.pos - 100)
                end = min(len(json_str), e.pos + 100)
                logger.error(f"      ...{json_str[start:end]}...")
                logger.error(f"   📝 Full JSON string: {json_str}")
                raise
            
            # Validate and return
            if not isinstance(color_objects, list) or len(color_objects) != 5:
                raise ValueError(f"Response must be an array of exactly 5 color objects, got {len(color_objects) if isinstance(color_objects, list) else 'not an array'}")
            
            # Validate each color object has hex and name
            for i, color in enumerate(color_objects):
                if not isinstance(color, dict) or 'hex' not in color or 'name' not in color:
                    raise ValueError(f"Color object at index {i} must have 'hex' and 'name' fields. Got: {color}")
            
            if DEBUG:
                logger.info(f"   🎨 Parsed {len(color_objects)} color objects from response")
            
            # Return colors with hex and name
            return {
                "colors": color_objects,
                "vibe": vibe,
                "prompt": prompt
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            raise Exception(f"Failed to parse LLM response as JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            raise Exception(f"Error calling Gemini API: {str(e)}")

    async def refine_palette(self, current_palette: List[Dict], instruction: str, vibe: str) -> Dict:
        """
        Refine an existing color palette based on user instructions.
        
        Args:
            current_palette: List of current color objects with hex and description
            instruction: User's modification instruction
            vibe: Desired mood/style to maintain
        
        Returns:
            Refined palette with colors and descriptions
        """
        try:
            if DEBUG:
                logger.info(f"🎨 LLMService.refine_palette() called")
                logger.info(f"   instruction: {instruction}")
                logger.info(f"   vibe: {vibe}")
                logger.info(f"   current colors: {len(current_palette)}")
            
            # Format current palette for the prompt (showing hex and name if available)
            if isinstance(current_palette[0], dict):
                # If palette has dicts with 'hex' and 'name' keys
                if 'name' in current_palette[0]:
                    current_palette_str = ", ".join([f"{color['hex']} ({color['name']})" for color in current_palette])
                else:
                    current_palette_str = ", ".join([color.get('hex', color) for color in current_palette])
            else:
                # If palette is just hex strings
                current_palette_str = ", ".join(current_palette)
            
            # Build the user message from refinement template
            user_message = PALETTE_REFINEMENT_USER_TEMPLATE.format(
                current_palette=current_palette_str,
                instruction=instruction,
                vibe=vibe
            )

            if DEBUG:
                logger.info(
                    f"   🔗 Calling Gemini API via REST: model={self.gemini_model}, version={self.gemini_api_version}"
                )

            response_text = await self._gemini_generate_text(
                message=f"{PALETTE_GENERATION_SYSTEM_PROMPT}\n\n{user_message}",
                request_type="refine",
                context={"instruction": instruction, "vibe": vibe},
            )

            if DEBUG:
                logger.info(f"   ✅ Gemini API responded")
            
            if DEBUG:
                logger.info(f"   📦 Response length: {len(response_text)} chars")
                logger.info(f"   📝 Raw response: {response_text}")
            
            # Try to extract JSON array from response - be more aggressive
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find array of objects anywhere in text
                json_match = re.search(r'\[\s*\{[^\]]+\}\s*(?:,\s*\{[^\]]+\}\s*)*\]', response_text, re.DOTALL)
                if not json_match:
                    logger.error(f"   ❌ Could not find JSON array in response: {response_text}")
                    raise ValueError(f"No JSON array found in response. Response was: {response_text[:200]}")
                json_str = json_match.group()
            
            if DEBUG:
                logger.info(f"   🔍 Extracted JSON string: {json_str[:200]}...")
            
            # Clean up common JSON issues
            json_str = json_str.replace('\n', ' ').replace('\r', '')
            json_str = re.sub(r',\s*]', ']', json_str)
            json_str = re.sub(r',\s*}', '}', json_str)
            
            try:
                color_objects = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"   ❌ JSON Parse Error at position {e.pos}")
                logger.error(f"   📝 Problematic JSON around error:")
                start = max(0, e.pos - 100)
                end = min(len(json_str), e.pos + 100)
                logger.error(f"      ...{json_str[start:end]}...")
                logger.error(f"   📝 Full JSON string: {json_str}")
                raise
            
            # Validate and return
            if not isinstance(color_objects, list) or len(color_objects) != 5:
                raise ValueError(f"Response must be an array of exactly 5 color objects, got {len(color_objects) if isinstance(color_objects, list) else 'not an array'}")
            
            # Validate each color object has hex and name
            for i, color in enumerate(color_objects):
                if not isinstance(color, dict) or 'hex' not in color or 'name' not in color:
                    raise ValueError(f"Color object at index {i} must have 'hex' and 'name' fields. Got: {color}")
            
            if DEBUG:
                logger.info(f"   🎨 Refined palette with {len(color_objects)} color objects")
            
            return {
                "colors": color_objects,
                "vibe": vibe,
                "instruction": instruction
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            raise Exception(f"Failed to parse LLM response as JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error refining palette: {str(e)}")
            raise Exception(f"Error refining palette: {str(e)}")

    async def generate_color_names(self, hex_codes: List[str]) -> List[str]:
        """
        Generate short color names from hex codes.

        Args:
            hex_codes: List of hex codes (e.g., ["#2D5A27", "#8FBC8F"])

        Returns:
            List of 1-2 word names in the same order
        """
        if not hex_codes:
            return []

        normalized_hex_codes = []
        for hex_code in hex_codes:
            if not isinstance(hex_code, str):
                raise ValueError(f"Invalid hex code type: {type(hex_code)}")
            normalized = hex_code if hex_code.startswith("#") else f"#{hex_code}"
            if not self.validate_hex_color(normalized):
                raise ValueError(f"Invalid hex color code: {hex_code}")
            normalized_hex_codes.append(normalized.upper())

        user_message = COLOR_NAME_GENERATION_USER_TEMPLATE.format(
            hex_codes=", ".join(normalized_hex_codes)
        )

        response_text = await self._gemini_generate_text(
            message=f"{COLOR_NAME_GENERATION_SYSTEM_PROMPT}\n\n{user_message}",
            request_type="generate-color-names",
            context={"hex_codes": ",".join(normalized_hex_codes)},
        )

        json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if not json_match:
                raise ValueError(f"No JSON array found in response. Response was: {response_text[:200]}")
            json_str = json_match.group()

        json_str = json_str.replace('\n', ' ').replace('\r', '')
        json_str = re.sub(r',\s*]', ']', json_str)

        names = json.loads(json_str)

        if not isinstance(names, list):
            raise ValueError("Response must be a JSON array of names")

        if len(names) != len(normalized_hex_codes):
            raise ValueError(
                f"Expected {len(normalized_hex_codes)} names, got {len(names)}"
            )

        cleaned_names = []
        for i, name in enumerate(names):
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"Invalid name at index {i}: {name}")
            short_name = " ".join(name.strip().split()[:2])
            cleaned_names.append(short_name)

        return cleaned_names

    def validate_hex_color(self, hex_color: str) -> bool:
        """
        Validate that a string is a valid hex color code.
        
        Args:
            hex_color: String to validate (e.g., "#FF6B6B" or "FF6B6B")
        
        Returns:
            True if valid hex color, False otherwise
        """
        hex_color = hex_color.lstrip("#")
        return len(hex_color) == 6 and all(c in "0123456789ABCDEFabcdef" for c in hex_color)

    async def generate_palette_from_image(self, image_source: str, vibe: str = "vibrant") -> Dict:
        """
        Generate a color palette from an image using LLM vision capabilities.
        
        Args:
            image_source: URL or file path of the image
            vibe: Desired mood/style (e.g., "vibrant", "minimal", "dark", "pastel", "warm", "cool")
        
        Returns:
            Dictionary containing palette with colors and descriptions
        """
        try:
            if DEBUG:
                logger.info(f"🖼️ LLMService.generate_palette_from_image() called")
                logger.info(f"   image_source: {image_source}")
                logger.info(f"   vibe: {vibe}")
            
            if self.provider == "gemini":
                return await self._call_gemini_vision_api(image_source, vibe)
            else:
                raise ValueError(f"Unsupported provider for image palette generation: {self.provider}")
        
        except Exception as e:
            logger.error(f"Error generating palette from image: {str(e)}")
            raise Exception(f"Error generating palette from image: {str(e)}")

    async def _call_gemini_vision_api(self, image_source: str, vibe: str) -> Dict:
        """
        Call Google Gemini Vision API to generate palette from image.
        
        Args:
            image_source: URL or file path of the image
            vibe: Desired mood/style
        
        Returns:
            Generated palette with colors and descriptions
        """
        try:
            if DEBUG:
                logger.info(
                    f"   🔗 Calling Gemini Vision API: model={self.gemini_model}, version={self.gemini_api_version}"
                )
            
            # Load and encode image
            image_data, mime_type = await self._load_and_encode_image(image_source)
            
            # Build the prompt
            prompt = f"""Analyze this image and generate a cohesive color palette of exactly 5 colors that capture its essence.
The palette should reflect a {vibe} mood/vibe.

Extract colors that are:
- Representative of the image's main color themes
- Complementary and aesthetically pleasing together
- Evocative of the {vibe} vibe

Return ONLY a valid JSON array of 5 color objects with no additional text.
Each object must have:
- "hex": the hex color code (e.g., "#FF6B6B")
- "name": a short descriptive name (1-2 words ONLY, e.g., "Coral Sunset", "Ocean Blue")

Example format:
[{{"hex": "#FF6B6B", "name": "Coral Blush"}}, {{"hex": "#4ECDC4", "name": "Mint Fresh"}}, {{"hex": "#45B7D1", "name": "Sky Blue"}}, {{"hex": "#FFA07A", "name": "Peach Glow"}}, {{"hex": "#98D8C8", "name": "Seafoam"}}]

Return ONLY the JSON array, nothing else."""
            
            # Call Gemini API with image
            endpoint = (
                f"{self.gemini_base_url}/{self.gemini_api_version}/models/"
                f"{self.gemini_model}:generateContent?key={self.api_key}"
            )
            
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": prompt
                            },
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": image_data
                                }
                            }
                        ],
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 300,
                },
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(endpoint, json=payload)

            if response.status_code >= 400:
                raise ValueError(
                    f"Gemini Vision API HTTP {response.status_code}: {response.text[:500]}"
                )

            response_json = response.json()
            response_text = (
                response_json.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )

            if not response_text:
                raise ValueError(f"Gemini returned empty text. Response: {json.dumps(response_json)[:500]}")

            self._save_raw_response(response_text=response_text, request_type="generate-from-image", context={"vibe": vibe})

            if DEBUG:
                logger.info(f"   ✅ Gemini Vision API responded")
                logger.info(f"   📦 Response length: {len(response_text)} chars")
                logger.info(f"   📝 Raw response: {response_text}")
            
            # Parse JSON response (same as generate_palette)
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\[\s*\{[^\]]+\}\s*(?:,\s*\{[^\]]+\}\s*)*\]', response_text, re.DOTALL)
                if not json_match:
                    logger.error(f"   ❌ Could not find JSON array in response: {response_text}")
                    raise ValueError(f"No JSON array found in response. Response was: {response_text[:200]}")
                json_str = json_match.group()
            
            # Clean up common JSON issues
            json_str = json_str.replace('\n', ' ').replace('\r', '')
            json_str = re.sub(r',\s*]', ']', json_str)
            json_str = re.sub(r',\s*}', '}', json_str)
            
            color_objects = json.loads(json_str)
            
            # Validate
            if not isinstance(color_objects, list) or len(color_objects) != 5:
                raise ValueError(f"Response must be an array of exactly 5 color objects")
            
            for i, color in enumerate(color_objects):
                if not isinstance(color, dict) or 'hex' not in color or 'name' not in color:
                    raise ValueError(f"Color object at index {i} must have 'hex' and 'name' fields")
            
            if DEBUG:
                logger.info(f"   🎨 Parsed {len(color_objects)} color objects from image")
            
            return {
                "colors": color_objects,
                "vibe": vibe
            }
            
        except Exception as e:
            logger.error(f"Error calling Gemini Vision API: {str(e)}")
            raise Exception(f"Error calling Gemini Vision API: {str(e)}")

    async def _load_and_encode_image(self, image_source: str) -> tuple[str, str]:
        """
        Load an image from URL or file path and encode it as base64.
        
        Args:
            image_source: URL or file path of the image
        
        Returns:
            Tuple of (base64_encoded_data, mime_type)
        """
        try:
            # Check if it's a local file path
            if os.path.exists(image_source):
                with open(image_source, "rb") as f:
                    image_bytes = f.read()
                
                # Determine mime type from file extension
                ext = Path(image_source).suffix.lower()
                mime_type_map = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp'
                }
                mime_type = mime_type_map.get(ext, 'image/jpeg')
            else:
                # Assume it's a URL
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(image_source)
                    response.raise_for_status()
                    image_bytes = response.content
                    
                # Get mime type from response headers
                mime_type = response.headers.get('content-type', 'image/jpeg')
            
            # Encode to base64
            base64_data = base64.b64encode(image_bytes).decode('utf-8')
            
            if DEBUG:
                logger.info(f"   📷 Image encoded: {len(base64_data)} bytes, mime_type={mime_type}")
            
            return base64_data, mime_type
            
        except Exception as e:
            raise Exception(f"Failed to load and encode image: {str(e)}")
