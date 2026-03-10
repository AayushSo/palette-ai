from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import logging
from dotenv import load_dotenv

from core.extractor import KMeansExtractor
from core.llm_service import LLMPaletteService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Load environment variables
load_dotenv()

app = FastAPI(title="Color Palette Extraction API", version="1.0.0")

# Configure CORS
allowed_origins = [
    "http://localhost:5174",  # Vite dev server (local)
    "https://palette-ai-delta.vercel.app",  # Production Vercel URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class GeneratePaletteRequest(BaseModel):
    """Request model for palette generation from text prompt."""
    prompt: str
    vibe: str = "vibrant"

class RefinePaletteRequest(BaseModel):
    """Request model for palette refinement."""
    colors: list
    instruction: str
    vibe: str = "vibrant"

class GenerateColorNamesRequest(BaseModel):
    """Request model for generating names from hex colors."""
    colors: list

# Initialize services
extractor = KMeansExtractor()
llm_service = LLMPaletteService()

if DEBUG:
    logger.info("🐛 DEBUG MODE ENABLED")
    logger.info(f"   LLM Provider: {os.getenv('LLM_PROVIDER', 'gemini')}")


@app.get("/")
def read_root():
    """Health check endpoint."""
    if DEBUG:
        logger.info("✅ Health check ping")
    return {"message": "Color Palette API is running", "debug": DEBUG}


@app.post("/api/extract-palette")
async def extract_palette(image_url: str):
    """
    Extract a color palette from an image URL.
    
    Args:
        image_url: URL of the image to extract colors from
    
    Returns:
        Palette with hex color codes
    """
    try:
        palette = extractor.extract(image_url)
        return {
            "success": True,
            "palette": palette,
            "algorithm": "kmeans"
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )


@app.post("/api/generate-palette")
async def generate_palette(request: GeneratePaletteRequest):
    """
    Generate a color palette from a text prompt using LLM.
    
    Args:
        request: GeneratePaletteRequest with prompt and vibe
    
    Returns:
        Palette with 5 hex color codes and descriptions
    """
    try:
        if DEBUG:
            logger.info(f"📝 Generate palette: prompt='{request.prompt[:50]}...', vibe='{request.vibe}'")
        
        palette = await llm_service.generate_palette(request.prompt, request.vibe)
        
        if DEBUG:
            logger.info(f"✅ Palette generated: {len(palette.get('colors', []))} colors")
        
        return {
            "success": True,
            "palette": palette,
            "prompt": request.prompt,
            "vibe": request.vibe
        }
    except Exception as e:
        if DEBUG:
            logger.error(f"❌ Error generating palette: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )


@app.post("/api/refine-palette")
async def refine_palette(request: RefinePaletteRequest):
    """
    Refine an existing color palette based on user instructions.
    
    Args:
        request: RefinePaletteRequest with colors, instruction, and vibe
    
    Returns:
        Refined palette with 5 hex color codes and descriptions
    """
    try:
        if DEBUG:
            logger.info(f"🎨 Refine palette: instruction='{request.instruction[:50]}...', vibe='{request.vibe}'")
        
        palette = await llm_service.refine_palette(request.colors, request.instruction, request.vibe)
        
        if DEBUG:
            logger.info(f"✅ Palette refined successfully")
        
        return {
            "success": True,
            "palette": palette,
            "instruction": request.instruction,
            "vibe": request.vibe
        }
    except Exception as e:
        if DEBUG:
            logger.error(f"❌ Error refining palette: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )


@app.get("/api/palette-algorithms")
def get_algorithms():
    """List available extraction algorithms."""
    return {
        "algorithms": ["kmeans"],
        "description": "Current supported algorithms for palette extraction"
    }


@app.post("/api/generate-color-names")
async def generate_color_names(request: GenerateColorNamesRequest):
    """
    Generate short color names for provided HEX codes.

    Args:
        request: GenerateColorNamesRequest with colors list

    Returns:
        Names list in same order as input colors
    """
    try:
        hex_codes = []
        for color in request.colors:
            if isinstance(color, dict):
                hex_codes.append(color.get("hex", ""))
            else:
                hex_codes.append(color)

        names = await llm_service.generate_color_names(hex_codes)

        return {
            "success": True,
            "names": names,
            "colors": hex_codes,
        }
    except Exception as e:
        if DEBUG:
            logger.error(f"❌ Error generating color names: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
