from abc import ABC, abstractmethod
from typing import List
import numpy as np
from PIL import Image
import httpx
import io
import os
import colorsys
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

    def extract(self, image_source: str, vibe: str = "vibrant") -> List[str]:
        """
        Extract colors using K-Means clustering.
        
        Args:
            image_source: URL or file path of the image to process
            vibe: The mood/style to optimize for in clustering weights
        
        Returns:
            List of hex color codes
        """
        try:
            # Load image from URL or file
            image_array = self._load_image(image_source)

            # Build pixel set with chunk-based sampling for large images.
            pixels = self._prepare_pixels(image_array)

            # Convert RGB pixels to HSV in [0, 1], then warp HSV cylinder to Cartesian.
            hsv_pixels = self._rgb_pixels_to_hsv(pixels)
            cartesian_pixels = self._hsv_to_cartesian(hsv_pixels)

            # Calculate weights for every pixel based on vibe
            h = hsv_pixels[:, 0]
            s = hsv_pixels[:, 1]
            v = hsv_pixels[:, 2]
            
            if vibe == "vibrant":
                w = (s ** 2) * v
            elif vibe == "minimal":
                w = (1 - s) ** 2
            elif vibe == "dark":
                w = (1 - v) ** 2
            elif vibe == "pastel":
                w = (v ** 2) * (s * (1 - s)) * 4  # *4 scales the peak of s*(1-s) back up to 1.0
            elif vibe == "warm":
                w = s * ((np.cos((h - 0.05) * 2 * np.pi) + 1) / 2)
            elif vibe == "cool":
                w = s * ((np.cos((h - 0.55) * 2 * np.pi) + 1) / 2)
            else:  # "standard" or any unrecognized vibe
                w = np.ones_like(h)  # Equal weight for all pixels
            
            # Add a tiny baseline weight so no pixels are entirely ignored
            weights = w + 0.05

            # Apply K-Means in warped Cartesian HSV space with pixel weights.
            kmeans = KMeans(n_clusters=self.num_colors, random_state=42, n_init=10)
            kmeans.fit(cartesian_pixels, sample_weight=weights)

            # Convert cluster centers back: Cartesian -> HSV -> RGB -> HEX.
            hsv_centers = self._cartesian_to_hsv(kmeans.cluster_centers_)
            rgb_centers = self._hsv_centers_to_rgb(hsv_centers)
            hex_colors = [self._rgb_to_hex(color) for color in rgb_centers]
            
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

    def _prepare_pixels(self, image_array: np.ndarray) -> np.ndarray:
        """
        Prepare pixels for clustering.

        If image has more than 10k pixels, split into 10x10 chunks and sample
        100 random pixels from each chunk for spatially balanced coverage.
        """
        height, width, _ = image_array.shape
        total_pixels = height * width

        if total_pixels <= 10000:
            return image_array.reshape(-1, 3)

        sampled_chunks = []
        row_chunks = np.array_split(image_array, 10, axis=0)

        for row_chunk in row_chunks:
            col_chunks = np.array_split(row_chunk, 10, axis=1)
            for chunk in col_chunks:
                chunk_pixels = chunk.reshape(-1, 3)
                # Enforce 100 picks per chunk; sample with replacement if needed.
                replace = len(chunk_pixels) < 100
                indices = np.random.choice(len(chunk_pixels), 100, replace=replace)
                sampled_chunks.append(chunk_pixels[indices])

        return np.vstack(sampled_chunks)

    def _rgb_pixels_to_hsv(self, rgb_pixels: np.ndarray) -> np.ndarray:
        """Convert RGB pixels (0-255) to HSV values in [0, 1]."""
        rgb = np.clip(rgb_pixels.astype(np.float64) / 255.0, 0.0, 1.0)

        r = rgb[:, 0]
        g = rgb[:, 1]
        b = rgb[:, 2]

        maxc = np.max(rgb, axis=1)
        minc = np.min(rgb, axis=1)
        delta = maxc - minc

        h = np.zeros_like(maxc)
        s = np.zeros_like(maxc)
        v = maxc

        nonzero_max = maxc > 0
        s[nonzero_max] = delta[nonzero_max] / maxc[nonzero_max]

        nonzero_delta = delta > 0

        r_is_max = (maxc == r) & nonzero_delta
        g_is_max = (maxc == g) & nonzero_delta
        b_is_max = (maxc == b) & nonzero_delta

        h[r_is_max] = ((g[r_is_max] - b[r_is_max]) / delta[r_is_max]) % 6.0
        h[g_is_max] = ((b[g_is_max] - r[g_is_max]) / delta[g_is_max]) + 2.0
        h[b_is_max] = ((r[b_is_max] - g[b_is_max]) / delta[b_is_max]) + 4.0
        h = (h / 6.0) % 1.0

        return np.column_stack((h, s, v))

    def _hsv_to_cartesian(self, hsv_pixels: np.ndarray) -> np.ndarray:
        """
        Warp HSV cylinder to Cartesian coordinates before clustering.

        X = S * cos(H * 2*pi)
        Y = S * sin(H * 2*pi)
        Z = V
        """
        h = hsv_pixels[:, 0]
        s = hsv_pixels[:, 1]
        v = hsv_pixels[:, 2]

        theta = h * 2.0 * np.pi
        x = s * np.cos(theta)
        y = s * np.sin(theta)
        z = v

        return np.column_stack((x, y, z))

    def _cartesian_to_hsv(self, xyz_points: np.ndarray) -> np.ndarray:
        """
        Convert Cartesian cluster centers back to HSV.

        H = (atan2(Y, X) / (2*pi)) mod 1
        S = sqrt(X^2 + Y^2)
        V = Z
        """
        x = xyz_points[:, 0]
        y = xyz_points[:, 1]
        z = xyz_points[:, 2]

        h = (np.arctan2(y, x) / (2.0 * np.pi)) % 1.0
        s = np.sqrt(np.square(x) + np.square(y))
        v = z

        hsv = np.column_stack((h, s, v))
        hsv[:, 1] = np.clip(hsv[:, 1], 0.0, 1.0)
        hsv[:, 2] = np.clip(hsv[:, 2], 0.0, 1.0)
        return hsv

    def _hsv_centers_to_rgb(self, hsv_centers: np.ndarray) -> np.ndarray:
        """Convert HSV cluster centers in [0, 1] to RGB values in [0, 255]."""
        rgb_centers = []
        for h, s, v in hsv_centers:
            r, g, b = colorsys.hsv_to_rgb(float(h), float(s), float(v))
            rgb_centers.append([r * 255.0, g * 255.0, b * 255.0])
        return np.array(rgb_centers)

    def _rgb_to_hex(self, rgb: tuple) -> str:
        """Convert RGB tuple to hex color code."""
        r = int(np.clip(round(rgb[0]), 0, 255))
        g = int(np.clip(round(rgb[1]), 0, 255))
        b = int(np.clip(round(rgb[2]), 0, 255))
        return "#{:02X}{:02X}{:02X}".format(r, g, b)


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
