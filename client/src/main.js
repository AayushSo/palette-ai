// API Configuration
// In production, default to same-origin unless VITE_API_URL is explicitly set.
const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? window.location.origin : "http://localhost:8000");
const DEBUG_MODE = import.meta.env.VITE_DEBUG === "true";

console.log("🚀 [App Init] Starting Color Palette App");
console.log("   API_BASE_URL:", API_BASE_URL);
console.log("   DEBUG_MODE:", DEBUG_MODE);

// Check API health on load
(async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/`);
    const data = await response.json();
    console.log("✅ [API Health] Backend is running");
    console.log("   debug:", data.debug);
  } catch (error) {
    console.error("❌ [API Health] Failed to reach backend:", error.message);
  }
})();

// DOM Elements
const tabButtons = document.querySelectorAll(".tab-button");
const tabContents = document.querySelectorAll(".tab-content");
const extractBtn = document.getElementById("extractBtn");
const generateBtn = document.getElementById("generateBtn");
const imageUrlInput = document.getElementById("imageUrl");
const imageFileInput = document.getElementById("imageFile");
const extractVibeSelect = document.getElementById("extractVibe");
const extractMethodSelect = document.getElementById("extractMethod");
const promptInput = document.getElementById("prompt");
const vibeSelect = document.getElementById("vibe");
const loadingDiv = document.getElementById("loading");
const errorDiv = document.getElementById("error");
const errorMessage = document.getElementById("errorMessage");
const dismissErrorBtn = document.getElementById("dismissErrorBtn");
const paletteContainer = document.getElementById("paletteContainer");
const paletteGrid = document.getElementById("paletteGrid");
const copyAllBtn = document.getElementById("copyAllBtn");
const exportBtn = document.getElementById("exportBtn");
const headerTitle = document.getElementById("headerTitle");
const quickSearch = document.getElementById("quickSearch");
const quickPrompt = document.getElementById("quickPrompt");
const quickVibe = document.getElementById("quickVibe");
const quickGenerateBtn = document.getElementById("quickGenerateBtn");

// Store current palette for export/copy
let currentPalette = [];
let currentVibe = "vibrant";
let namingRequestCounter = 0;

// ====================
// Event Listeners
// ====================

// Go back to home when header title is clicked
headerTitle.addEventListener("click", () => {
  goBackToHome();
});

// Tab switching
tabButtons.forEach((button) => {
  button.addEventListener("click", (e) => {
    const tabName = e.target.dataset.tab;
    switchTab(tabName);
  });
});

// Update background when vibe changes
vibeSelect.addEventListener("change", (e) => {
  currentVibe = e.target.value;
  applyVibeBackground(currentVibe);
});

// Update background when extract vibe changes
extractVibeSelect.addEventListener("change", (e) => {
  currentVibe = e.target.value;
  applyVibeBackground(currentVibe);
});

// Extract palette from image
extractBtn.addEventListener("click", async () => {
  const imageUrl = imageUrlInput.value.trim();
  const imageFile = imageFileInput.files[0];
  const vibe = extractVibeSelect.value;
  const method = extractMethodSelect.value;
  
  if (!imageUrl && !imageFile) {
    showError("Please enter an image URL or upload an image file");
    return;
  }
  
  if (imageUrl && imageFile) {
    showError("Please provide either a URL or a file, not both");
    return;
  }
  
  await extractPalette(imageUrl, imageFile, vibe, method);
});

// Generate palette from text
generateBtn.addEventListener("click", async () => {
  const prompt = promptInput.value.trim();
  if (!prompt) {
    showError("Please describe your desired palette");
    return;
  }
  const vibe = vibeSelect.value;
  await generatePalette(prompt, vibe);
});

// Quick search refine palette
quickGenerateBtn.addEventListener("click", async () => {
  const instruction = quickPrompt.value.trim();
  if (!instruction) {
    showError("Please describe how to refine your palette");
    return;
  }
  const vibe = quickVibe.value;
  await refinePalette(currentPalette, instruction, vibe);
});

// Update current vibe when quick vibe selector changes
quickVibe.addEventListener("change", (e) => {
  currentVibe = e.target.value;
});

// Quick search on Enter key
quickPrompt.addEventListener("keypress", (e) => {
  if (e.key === "Enter") {
    quickGenerateBtn.click();
  }
});

dismissErrorBtn.addEventListener("click", () => {
  closeError();
});

// Copy all hex codes
copyAllBtn.addEventListener("click", () => {
  // Extract hex codes from palette (handle both string and object formats)
  const hexCodes = currentPalette.map(color => 
    typeof color === "string" ? color : color.hex
  ).join("\n");
  navigator.clipboard.writeText(hexCodes).then(() => {
    showMessage("Copied all hex codes to clipboard!");
  });
});

// Export palette as JSON
exportBtn.addEventListener("click", () => {
  const data = {
    colors: currentPalette,
    timestamp: new Date().toISOString(),
  };
  const json = JSON.stringify(data, null, 2);
  downloadJSON(json, "palette.json");
});

// ====================
// Core Functions
// ====================

/**
 * Return to home screen (hide palette and show form)
 */
function goBackToHome() {
  document.body.classList.remove("palette-visible");
  headerTitle.classList.remove("hidden");
  quickSearch.classList.add("hidden");
  paletteContainer.classList.add("hidden");
  paletteGrid.innerHTML = "";

  // Reset URL to home view when leaving palette mode
  const url = new URL(window.location.href);
  url.searchParams.delete("colors");
  window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
  
  // Reset quick search input
  quickPrompt.value = "";
}

/**
 * Convert a color value to six-digit uppercase hex without '#'.
 */
function normalizeHexForUrl(colorValue) {
  if (!colorValue) {
    return null;
  }
  const rawHex = String(colorValue).replace(/^#/, "").trim();
  return /^[0-9A-Fa-f]{6}$/.test(rawHex) ? rawHex.toUpperCase() : null;
}

/**
 * Update the current URL with shareable palette colors.
 * Format: ?colors=2D5A27-8FBC8F-F5F5DC-E8F48C-556B2F
 */
function updateUrlWithPalette(colors) {
  const serializedColors = colors
    .map((color) => {
      const hex = typeof color === "string" ? color : color.hex;
      return normalizeHexForUrl(hex);
    })
    .filter(Boolean)
    .join("-");

  if (!serializedColors) {
    return;
  }

  const url = new URL(window.location.href);
  url.searchParams.set("colors", serializedColors);
  window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
}

/**
 * Parse shareable colors from URL query string.
 */
function getPaletteFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const rawColors = params.get("colors");

  if (!rawColors) {
    return null;
  }

  const colorTokens = rawColors
    .split("-")
    .map((token) => token.trim())
    .filter(Boolean);

  if (colorTokens.length === 0) {
    return null;
  }

  const parsedColors = [];
  for (const token of colorTokens) {
    const normalized = normalizeHexForUrl(token);
    if (!normalized) {
      console.warn(`⚠️ [URL Palette] Invalid color token ignored: ${token}`);
      return null;
    }
    parsedColors.push({ hex: `#${normalized}`, name: "" });
  }

  return parsedColors;
}

/**
 * Request color names in the background and patch the current palette UI.
 */
async function generateColorNamesInBackground(colors) {
  const requestId = ++namingRequestCounter;
  const hexCodes = colors.map((color) => (typeof color === "string" ? color : color.hex));

  try {
    const response = await fetch(`${API_BASE_URL}/api/generate-color-names`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ colors: hexCodes }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || "Failed to generate color names");
    }

    const data = await response.json();
    if (!data.success || !Array.isArray(data.names)) {
      throw new Error(data.error || "Invalid color names response");
    }

    // Ignore stale responses from older requests.
    if (requestId !== namingRequestCounter) {
      return;
    }

    currentPalette = currentPalette.map((color, index) => {
      const hex = typeof color === "string" ? color : color.hex;
      const existingName = typeof color === "string" ? "" : (color.name || "");
      return {
        hex,
        name: existingName || data.names[index] || "",
      };
    });

    // Update names in-place without blocking initial palette render.
    displayPalette(currentPalette, currentVibe, false);
  } catch (error) {
    console.warn("⚠️ [Color Names] Background naming failed:", error.message);
  }
}

/**
 * Switch between Extract and Generate tabs
 */
function switchTab(tabName) {
  // Update buttons
  tabButtons.forEach((btn) => btn.classList.remove("active"));
  event.target.classList.add("active");

  // Update content
  tabContents.forEach((content) => content.classList.remove("active"));
  document.getElementById(tabName).classList.add("active");
}

/**
 * Apply background based on selected vibe
 */
function applyVibeBackground(vibe) {
  // Remove all vibe classes
  document.body.classList.remove(
    "vibe-vibrant",
    "vibe-minimal",
    "vibe-dark",
    "vibe-pastel",
    "vibe-warm",
    "vibe-cool"
  );
  // Add selected vibe class
  document.body.classList.add(`vibe-${vibe}`);
}

/**
 * Extract palette from image URL or file
 */
async function extractPalette(imageUrl, imageFile, vibe, method) {
  showLoading(true);
  try {
    console.log("📷 [extractPalette] Starting request...");
    console.log("   imageUrl:", imageUrl);
    console.log("   imageFile:", imageFile?.name);
    console.log("   vibe:", vibe);
    console.log("   method:", method);
    console.log("   endpoint:", `${API_BASE_URL}/api/extract-palette`);
    
    let response;
    
    if (imageFile) {
      // Handle file upload
      const formData = new FormData();
      formData.append("file", imageFile);
      formData.append("vibe", vibe);
      formData.append("method", method);
      
      response = await fetch(`${API_BASE_URL}/api/extract-palette`, {
        method: "POST",
        body: formData,
      });
    } else {
      // Handle URL
      response = await fetch(`${API_BASE_URL}/api/extract-palette`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ image_url: imageUrl, vibe, method }),
      });
    }

    console.log("✅ [extractPalette] Response received");
    console.log("   status:", response.status);

    if (!response.ok) {
      const errorData = await response.json();
      console.error("❌ [extractPalette] Error response:", errorData);
      throw new Error(errorData.error || "Failed to extract palette");
    }

    const data = await response.json();
    console.log("📦 [extractPalette] Response data:", data);
    
    if (data.success) {
      // For AI method, use data.palette.colors (similar to generate)
      // For local method, use data.palette (array of hex strings)
      const colors = method === "ai" ? data.palette.colors : data.palette;
      displayPalette(colors, vibe);
      showMessage("Palette extracted successfully!");
    } else {
      throw new Error(data.error || "Unknown error");
    }
  } catch (error) {
    console.error("❌ [extractPalette] Error:", error.message);
    showError(error.message);
  } finally {
    showLoading(false);
  }
}

/**
 * Generate palette from text prompt using LLM
 */
async function generatePalette(prompt, vibe) {
  showLoading(true);
  try {
    console.log("🎨 [generatePalette] Starting request...");
    console.log("   prompt:", prompt);
    console.log("   vibe:", vibe);
    console.log("   endpoint:", `${API_BASE_URL}/api/generate-palette`);
    
    const response = await fetch(`${API_BASE_URL}/api/generate-palette`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt, vibe }),
    });

    console.log("✅ [generatePalette] Response received");
    console.log("   status:", response.status);
    console.log("   ok:", response.ok);

    if (!response.ok) {
      const errorData = await response.json();
      console.error("❌ [generatePalette] Error response:", errorData);
      throw new Error(errorData.error || "Failed to generate palette");
    }

    const data = await response.json();
    console.log("📦 [generatePalette] Response data:", data);
    console.log("   success:", data.success);
    console.log("   colors count:", data.palette?.colors?.length);
    
    if (data.success) {
      displayPalette(data.palette.colors, vibe);
      showMessage("Palette generated successfully!");
    } else {
      throw new Error(data.error || "Unknown error");
    }
  } catch (error) {
    console.error("❌ [generatePalette] Error:", error.message);
    showError(error.message);
  } finally {
    showLoading(false);
  }
}

/**
 * Refine existing palette based on user instruction using LLM
 */
async function refinePalette(colors, instruction, vibe) {
  showLoading(true);
  try {
    console.log("✨ [refinePalette] Starting request...");
    console.log("   current colors:", colors);
    console.log("   instruction:", instruction);
    console.log("   vibe:", vibe);
    console.log("   endpoint:", `${API_BASE_URL}/api/refine-palette`);
    
    const response = await fetch(`${API_BASE_URL}/api/refine-palette`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ colors, instruction, vibe }),
    });

    console.log("✅ [refinePalette] Response received");
    console.log("   status:", response.status);
    console.log("   ok:", response.ok);

    if (!response.ok) {
      const errorData = await response.json();
      console.error("❌ [refinePalette] Error response:", errorData);
      throw new Error(errorData.error || "Failed to refine palette");
    }

    const data = await response.json();
    console.log("📦 [refinePalette] Response data:", data);
    console.log("   success:", data.success);
    console.log("   colors count:", data.palette?.colors?.length);
    
    if (data.success) {
      displayPalette(data.palette.colors, vibe);
      showMessage("Palette refined successfully!");
      // Clear the instruction input after successful refinement
      quickPrompt.value = "";
    } else {
      throw new Error(data.error || "Unknown error");
    }
  } catch (error) {
    console.error("❌ [refinePalette] Error:", error.message);
    showError(error.message);
  } finally {
    showLoading(false);
  }
}

/**
 * Calculate relative luminance of a color
 * Returns a value between 0 (darkest) and 1 (lightest)
 * Based on WCAG formula: https://www.w3.org/TR/WCAG20-TECHS/G17.html
 */
function getLuminance(hex) {
  // Convert hex to RGB
  const rgb = parseInt(hex.substring(1), 16);
  const r = (rgb >> 16) & 0xff;
  const g = (rgb >> 8) & 0xff;
  const b = (rgb >> 0) & 0xff;
  
  // Convert to 0-1 range and apply gamma correction
  const rsRGB = r / 255;
  const gsRGB = g / 255;
  const bsRGB = b / 255;
  
  const rLinear = rsRGB <= 0.03928 ? rsRGB / 12.92 : Math.pow((rsRGB + 0.055) / 1.055, 2.4);
  const gLinear = gsRGB <= 0.03928 ? gsRGB / 12.92 : Math.pow((gsRGB + 0.055) / 1.055, 2.4);
  const bLinear = bsRGB <= 0.03928 ? bsRGB / 12.92 : Math.pow((bsRGB + 0.055) / 1.055, 2.4);
  
  // Calculate luminance
  return 0.2126 * rLinear + 0.7152 * gLinear + 0.0722 * bLinear;
}

/**
 * Determine if text should be light or dark based on background color
 * Returns 'light-text' for light text on dark background
 * Returns 'dark-text' for dark text on light background
 */
function getTextColorClass(hex) {
  const luminance = getLuminance(hex);
  // If luminance is above 0.5, use dark text; otherwise use light text
  return luminance > 0.5 ? 'dark-text' : 'light-text';
}

/**
 * Display palette in the UI
 */
function displayPalette(colors, vibe = "vibrant", shouldScroll = true) {
  console.log("🎨 [displayPalette] Rendering palette");
  console.log("   colors:", colors);
  console.log("   vibe:", vibe);
  console.log("   type of first color:", typeof colors[0]);
  
  currentPalette = colors;
  currentVibe = vibe;
  paletteGrid.innerHTML = "";
  
  // Update the quick vibe selector to match current vibe
  quickVibe.value = vibe;

  colors.forEach((colorData, index) => {
    // Colors should be object format from LLM: { hex, name }
    const hex = typeof colorData === "string" ? colorData : colorData.hex;
    const colorName = typeof colorData === "string" ? "" : (colorData.name || "");
    console.log(`   [${index}] hex: ${hex}, name: ${colorName}`);
    
    // Determine text color based on background luminance
    const textColorClass = getTextColorClass(hex);
    
    const colorCard = document.createElement("div");
    colorCard.className = "color-card";
    colorCard.onclick = () => copyToClipboard(hex);
    
    colorCard.innerHTML = `
      <div class="color-preview" style="background-color: ${hex}"></div>
      <div class="color-info ${textColorClass}">
        <code>${hex}</code>
        <p class="color-name">${colorName}</p>
      </div>
    `;
    paletteGrid.appendChild(colorCard);
  });

  const needsNames = colors.some((color) => {
    if (typeof color === "string") {
      return true;
    }
    return !(color.name && color.name.trim());
  });

  if (needsNames) {
    generateColorNamesInBackground(colors);
  }

  // Keep the URL shareable with the currently visible palette.
  updateUrlWithPalette(colors);

  paletteContainer.classList.remove("hidden");
  
  // Toggle to full-screen palette view
  document.body.classList.add("palette-visible");
  headerTitle.classList.add("hidden");
  quickSearch.classList.remove("hidden");
  
  if (shouldScroll) {
    paletteContainer.scrollIntoView({ behavior: "smooth" });
  }
  console.log("✅ [displayPalette] Palette rendered successfully");
}

/**
 * Copy a color to clipboard
 */
function copyToClipboard(color) {
  navigator.clipboard.writeText(color).then(() => {
    showMessage(`Copied ${color} to clipboard!`);
  });
}

// ====================
// UI Helpers
// ====================

/**
 * Show loading spinner
 */
function showLoading(show) {
  if (show) {
    loadingDiv.classList.remove("hidden");
  } else {
    loadingDiv.classList.add("hidden");
  }
}

/**
 * Show error message
 */
function showError(message) {
  errorMessage.textContent = message;
  errorDiv.classList.remove("hidden");
  console.error("Error:", message);
}

/**
 * Close error message
 */
function closeError() {
  errorDiv.classList.add("hidden");
}

/**
 * Show temporary success message
 */
function showMessage(message) {
  const tempDiv = document.createElement("div");
  tempDiv.className = "message-toast";
  tempDiv.textContent = message;
  document.body.appendChild(tempDiv);

  setTimeout(() => {
    tempDiv.remove();
  }, 3000);
}

/**
 * Download JSON file
 */
function downloadJSON(jsonString, filename) {
  const element = document.createElement("a");
  element.setAttribute(
    "href",
    "data:text/json;charset=utf-8," + encodeURIComponent(jsonString)
  );
  element.setAttribute("download", filename);
  document.body.appendChild(element);
  element.click();
  document.body.removeChild(element);
}

// ====================
// Initialize
// ====================

console.log(`🚀 Color Palette App initialized`);
console.log(`📡 API Base URL: ${API_BASE_URL}`);

// Auto-load shared palettes from URL when present.
const sharedPalette = getPaletteFromUrl();
if (sharedPalette) {
  console.log("🔗 [URL Palette] Loading palette from query string");
  displayPalette(sharedPalette, currentVibe);
}
