from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import logging
from dotenv import load_dotenv
from typing import Optional
import tempfile
from pathlib import Path

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

class ExtractPaletteRequest(BaseModel):
    """Request model for palette extraction from image URL."""
    image_url: str
    vibe: str = "vibrant"
    method: str = "local"

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
async def extract_palette(
    request: Request,
    file: Optional[UploadFile] = File(None),
    vibe: Optional[str] = Form(None),
    method: Optional[str] = Form(None)
):
    """
    Extract a color palette from an image URL or uploaded file.
    Supports both JSON (for URLs) and multipart/form-data (for file uploads).
    
    Args:
        request: FastAPI request object to inspect content type
        file: Optional uploaded image file
        vibe: The mood/style of the palette (for AI method)
        method: Extraction method - "local" (K-Means) or "ai" (LLM-based)
    
    Returns:
        Palette with hex color codes and descriptions
    """
    try:
        image_url = None
        
        # Check if this is a JSON request (URL-based) or FormData (file upload)
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            # Handle JSON request for URL-based extraction
            json_data = await request.json()
            image_url = json_data.get("image_url")
            vibe = json_data.get("vibe", "vibrant")
            method = json_data.get("method", "local")
        else:
            # Handle FormData for file upload
            vibe = vibe or "vibrant"
            method = method or "local"
        
        # Validate input
        if not image_url and not file:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Either image_url or file must be provided"}
            )
        
        if image_url and file:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Provide either image_url or file, not both"}
            )
        
        if DEBUG:
            logger.info(f"📷 Extract palette: method={method}, vibe={vibe}")
            if file:
                logger.info(f"   Source: Uploaded file '{file.filename}'")
            else:
                logger.info(f"   Source: URL '{image_url[:50]}...'")
        
        # Handle file upload - save to temp file
        image_source = image_url
        temp_file_path = None
        
        if file:
            # Create temp file with original extension
            suffix = Path(file.filename).suffix if file.filename else ".jpg"
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file_path = temp_file.name
            
            # Write uploaded content to temp file
            content = await file.read()
            temp_file.write(content)
            temp_file.close()
            image_source = temp_file_path
            
            if DEBUG:
                logger.info(f"   Temp file: {temp_file_path}")
        
        try:
            if method == "ai":
                # Use LLM to generate palette from image
                palette = await llm_service.generate_palette_from_image(image_source, vibe)
                
                if DEBUG:
                    logger.info(f"✅ AI palette generated: {len(palette.get('colors', []))} colors")
                
                return {
                    "success": True,
                    "palette": palette,
                    "method": "ai",
                    "vibe": vibe
                }
            else:
                # Use K-Means local extraction
                palette = extractor.extract(image_source, vibe)
                
                if DEBUG:
                    logger.info(f"✅ Local palette extracted: {len(palette)} colors")
                
                return {
                    "success": True,
                    "palette": palette,
                    "method": "local"
                }
        finally:
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                if DEBUG:
                    logger.info(f"   Cleaned up temp file")
                    
    except Exception as e:
        if DEBUG:
            logger.error(f"❌ Error extracting palette: {str(e)}", exc_info=True)
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
