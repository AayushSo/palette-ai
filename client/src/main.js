// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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
    const response = await fetch(`${API_BASE_URL}/api/extract-palette`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ image_url: imageUrl }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || "Failed to extract palette");
    }

    const data = await response.json();
    if (data.success) {
      displayPalette(data.palette);
      showMessage("Palette extracted successfully!");
    } else {
      throw new Error(data.error || "Unknown error");
    }
  } catch (error) {
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
    const response = await fetch(`${API_BASE_URL}/api/generate-palette`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt, vibe }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || "Failed to generate palette");
    }

    const data = await response.json();
    if (data.success) {
      displayPalette(data.palette.colors);
      showMessage("Palette generated successfully!");
    } else {
      throw new Error(data.error || "Unknown error");
    }
  } catch (error) {
    showError(error.message);
  } finally {
    showLoading(false);
  }
}

/**
 * Display palette in the UI
 */
function displayPalette(colors) {
  currentPalette = colors;
  paletteGrid.innerHTML = "";

  colors.forEach((color) => {
    const colorCard = document.createElement("div");
    colorCard.className = "color-card";
    colorCard.innerHTML = `
      <div class="color-preview" style="background-color: ${color}"></div>
      <div class="color-info">
        <code>${color}</code>
        <button class="btn-copy" onclick="copyToClipboard('${color}')" title="Copy hex code">
          📋
        </button>
      </div>
    `;
    paletteGrid.appendChild(colorCard);
  });

  paletteContainer.classList.remove("hidden");
  paletteContainer.scrollIntoView({ behavior: "smooth" });
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
