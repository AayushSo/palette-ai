from abc import ABC, abstractmethod
from typing import List
import numpy as np
from PIL import Image
import httpx
import io
import os
from sklearn.cluster import KMeans


class PaletteExtractorStrategy(ABC):
    """
    Abstract base class for palette extraction strategies.
    Implements the Strategy Pattern to allow interchangeable algorithms.
    """

    @abstractmethod
    def extract(self, image_source: str) -> List[str]:
        """
        Extract a color palette from an image.
        
        Args:
            image_source: URL or file path of the image to process
        
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

    def extract(self, image_source: str) -> List[str]:
        """
        Extract colors using K-Means clustering.
        
        Args:
            image_source: URL or file path of the image to process
        
        Returns:
            List of hex color codes
        """
        try:
            # Load image from URL or file
            image_array = self._load_image(image_source)
            
            # Reshape image to be a list of pixels
            pixels = image_array.reshape(-1, 3)
            
            # Sample pixels if image is too large (for performance)
            max_pixels = 10000
            if len(pixels) > max_pixels:
                indices = np.random.choice(len(pixels), max_pixels, replace=False)
                pixels = pixels[indices]
            
            # Apply K-Means clustering
            kmeans = KMeans(n_clusters=self.num_colors, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            # Get the cluster centers (dominant colors)
            colors = kmeans.cluster_centers_
            
            # Convert to hex codes
            hex_colors = [self._rgb_to_hex(color) for color in colors]
            
            return hex_colors
        
        except Exception as e:
            raise Exception(f"Error extracting palette: {str(e)}")

    def _load_image(self, image_source: str) -> np.ndarray:
        """
        Load image from URL or file path and convert to numpy array.
        
        Args:
            image_source: URL or file path of the image
        
        Returns:
            Image as numpy array
        """
        try:
            # Check if it's a local file path
            if os.path.exists(image_source):
                image = Image.open(image_source)
            else:
                # Assume it's a URL
                response = httpx.get(image_source, timeout=10.0)
                response.raise_for_status()
                image = Image.open(io.BytesIO(response.content))
            
            image = image.convert("RGB")
            return np.array(image)
        except Exception as e:
            raise Exception(f"Failed to load image: {str(e)}")

    def _fetch_image(self, image_url: str) -> np.ndarray:
        """
        Fetch image from URL and convert to numpy array.
        Deprecated: Use _load_image instead.
        
        Args:
            image_url: URL of the image
        
        Returns:
            Image as numpy array
        """
        return self._load_image(image_url)

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
