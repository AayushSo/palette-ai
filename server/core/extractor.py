from abc import ABC, abstractmethod
from typing import List
import numpy as np
from PIL import Image
import httpx
import io


class PaletteExtractorStrategy(ABC):
    """
    Abstract base class for palette extraction strategies.
    Implements the Strategy Pattern to allow interchangeable algorithms.
    """

    @abstractmethod
    def extract(self, image_url: str) -> List[str]:
        """
        Extract a color palette from an image.
        
        Args:
            image_url: URL of the image to process
        
        Returns:
            List of hex color codes (e.g., ['#FF5733', '#33FF57', ...])
        """
        pass


class KMeansExtractor(PaletteExtractorStrategy):
    """
    K-Means based color palette extractor.
    Uses clustering to find the most representative colors in an image.
    """

    def __init__(self, num_colors: int = 5):
        """
        Initialize the K-Means extractor.
        
        Args:
            num_colors: Number of colors to extract (default: 5)
        """
        self.num_colors = num_colors

    def extract(self, image_url: str) -> List[str]:
        """
        Extract colors using K-Means clustering.
        Currently returns dummy hex codes as placeholder.
        
        Args:
            image_url: URL of the image to process
        
        Returns:
            List of hex color codes
        """
        try:
            # Placeholder implementation - returns dummy colors
            # TODO: Implement actual K-Means clustering with image processing
            
            # For now, return a hardcoded palette as placeholder
            dummy_palette = [
                "#FF6B6B",  # Red
                "#4ECDC4",  # Teal
                "#45B7D1",  # Blue
                "#FFA07A",  # Light Salmon
                "#98D8C8",  # Mint
            ]
            
            return dummy_palette[:self.num_colors]
        
        except Exception as e:
            raise Exception(f"Error extracting palette: {str(e)}")

    def _fetch_image(self, image_url: str) -> np.ndarray:
        """
        Fetch image from URL and convert to numpy array.
        
        Args:
            image_url: URL of the image
        
        Returns:
            Image as numpy array
        """
        try:
            response = httpx.get(image_url, timeout=10.0)
            response.raise_for_status()
            image = Image.open(io.BytesIO(response.content))
            image = image.convert("RGB")
            return np.array(image)
        except Exception as e:
            raise Exception(f"Failed to fetch image: {str(e)}")

    def _rgb_to_hex(self, rgb: tuple) -> str:
        """Convert RGB tuple to hex color code."""
        return "#{:02X}{:02X}{:02X}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


class DominantColorExtractor(PaletteExtractorStrategy):
    """
    Future implementation: Extracts dominant colors without clustering.
    Placeholder for alternative algorithm.
    """

    def extract(self, image_url: str) -> List[str]:
        """Extract dominant colors from an image."""
        # Placeholder for future implementation
        return ["#333333", "#666666", "#999999"]


class VibrantColorExtractor(PaletteExtractorStrategy):
    """
    Future implementation: Prioritizes vibrant, saturated colors.
    Placeholder for alternative algorithm.
    """

    def extract(self, image_url: str) -> List[str]:
        """Extract vibrant colors from an image."""
        # Placeholder for future implementation
        return ["#FF00FF", "#00FFFF", "#FFFF00"]
