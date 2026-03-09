// API Configuration
// For local dev: http://localhost:8000
// For production: automatically uses Vercel env variable
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const DEBUG_MODE = import.meta.env.VITE_DEBUG === "true" || true; // Enable debug by default

// Import ntc.js for color name lookup
import './ntc.js';

console.log("🚀 [App Init] Starting Color Palette App");
console.log("   API_BASE_URL:", API_BASE_URL);
console.log("   DEBUG_MODE:", DEBUG_MODE);

// Initialize ntc.js
if (window.ntc) {
  window.ntc.init();
  console.log("✅ [ntc.js] Color name lookup initialized");
}

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
const promptInput = document.getElementById("prompt");
const vibeSelect = document.getElementById("vibe");
const loadingDiv = document.getElementById("loading");
const errorDiv = document.getElementById("error");
const errorMessage = document.getElementById("errorMessage");
const paletteContainer = document.getElementById("paletteContainer");
const paletteGrid = document.getElementById("paletteGrid");
const copyAllBtn = document.getElementById("copyAllBtn");
const exportBtn = document.getElementById("exportBtn");

// Store current palette for export/copy
let currentPalette = [];

// ====================
// Event Listeners
// ====================

// Tab switching
tabButtons.forEach((button) => {
  button.addEventListener("click", (e) => {
    const tabName = e.target.dataset.tab;
    switchTab(tabName);
  });
});

// Update background when vibe changes
vibeSelect.addEventListener("change", (e) => {
  applyVibeBackground(e.target.value);
});

// Extract palette from image
extractBtn.addEventListener("click", async () => {
  const imageUrl = imageUrlInput.value.trim();
  if (!imageUrl) {
    showError("Please enter an image URL");
    return;
  }
  await extractPalette(imageUrl);
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

// Copy all hex codes
copyAllBtn.addEventListener("click", () => {
  const hexCodes = currentPalette.join("\n");
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
 * Extract palette from image URL
 */
async function extractPalette(imageUrl) {
  showLoading(true);
  try {
    console.log("📷 [extractPalette] Starting request...");
    console.log("   imageUrl:", imageUrl);
    console.log("   endpoint:", `${API_BASE_URL}/api/extract-palette`);
    
    const response = await fetch(`${API_BASE_URL}/api/extract-palette`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ image_url: imageUrl }),
    });

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
      displayPalette(data.palette);
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
      displayPalette(data.palette.colors);
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
 * Display palette in the UI
 */
function displayPalette(colors) {
  console.log("🎨 [displayPalette] Rendering palette");
  console.log("   colors:", colors);
  console.log("   type of first color:", typeof colors[0]);
  
  currentPalette = colors;
  paletteGrid.innerHTML = "";

  colors.forEach((colorData, index) => {
    // Handle both old format (string or object) and new format (just hex strings)
    let hex;
    let colorName = "";
    
    if (typeof colorData === "string") {
      // New format: just hex string
      hex = colorData;
      // Get color name from ntc.js
      if (window.ntc) {
        const nameMatch = window.ntc.name(hex);
        colorName = nameMatch[1]; // Color name
        console.log(`   [${index}] ${hex} -> "${colorName}"${nameMatch[2] ? ' (exact)' : ' (closest)'}`);
      }
    } else if (typeof colorData === "object") {
      // Old format: object with hex and description
      hex = colorData.hex;
      colorName = colorData.description || "";
      console.log(`   [${index}] hex: ${hex}, description: ${colorName}`);
    }
    
    const colorCard = document.createElement("div");
    colorCard.className = "color-card";
    
    let colorInfoHTML = `<code>${hex}</code>`;
    if (colorName) {
      colorInfoHTML += `<p class="color-name">${colorName}</p>`;
    }
    colorInfoHTML += `<button class="btn-copy" onclick="copyToClipboard('${hex}')" title="Copy hex code">📋</button>`;
    
    colorCard.innerHTML = `
      <div class="color-preview" style="background-color: ${hex}"></div>
      <div class="color-info">
        ${colorInfoHTML}
      </div>
    `;
    paletteGrid.appendChild(colorCard);
  });

  paletteContainer.classList.remove("hidden");
  paletteContainer.scrollIntoView({ behavior: "smooth" });
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
