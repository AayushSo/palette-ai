from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

from core.extractor import KMeansExtractor
from core.llm_service import LLMPaletteService

# Load environment variables
load_dotenv()

app = FastAPI(title="Color Palette Extraction API", version="1.0.0")

# Configure CORS
allowed_origins = [
    "http://localhost:5174",  # Vite dev server
    "https://yourdomain.vercel.app",  # TODO: Update with production Vercel URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
extractor = KMeansExtractor()
llm_service = LLMPaletteService()


@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"message": "Color Palette API is running"}


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
async def generate_palette(prompt: str, vibe: str = "vibrant"):
    """
    Generate a color palette from a text prompt using LLM.
    
    Args:
        prompt: Description of the desired palette
        vibe: Mood/style (e.g., "vibrant", "minimal", "dark", "pastel")
    
    Returns:
        Palette with hex color codes and descriptions
    """
    try:
        palette = await llm_service.generate_palette(prompt, vibe)
        return {
            "success": True,
            "palette": palette,
            "prompt": prompt,
            "vibe": vibe
        }
    except Exception as e:
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
