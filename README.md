# Palette AI

Palette AI is a full-stack color palette app built with a Vite frontend and FastAPI backend.

It supports:
- Palette generation from text prompts using Gemini.
- Palette extraction from images (URL or local file upload).
- Two image extraction methods: AI Agent (Gemini vision) and Local (K-Means clustering).
- Vibe-based styling and generation (`vibrant`, `minimal`, `dark`, `pastel`, `warm`, `cool`).
- Palette refinement and color name generation.
- Shareable palette links, export JSON, and copy hex codes.

## Tech Stack

- Frontend: Vite, vanilla JavaScript, CSS
- Backend: FastAPI, Python
- AI: Gemini REST API
- Image/local extraction: NumPy, Pillow, scikit-learn (K-Means)

## Project Structure

```text
palette-ai/
	client/                # Vite frontend
		src/
			main.js
			style.css
		index.html
		package.json
	server/                # FastAPI backend
		core/
			extractor.py
			llm_service.py
			prompts.py
		main.py
		requirements.txt
		.env
```

## Features

### 1. Generate From Text
- Enter a prompt describing your desired palette.
- Select a vibe.
- App returns 5 colors with hex and short names.

### 2. Extract From Image
- Input an image URL or upload a local image file.
- Select vibe.
- Select generation method:
	- `ai`: Gemini vision-based palette extraction.
	- `local`: K-Means clustering on image pixels.

### 3. Refine Existing Palette
- Use the `Update` input on palette screen to refine current colors with natural language.

### 4. Utilities
- Copy all hex codes.
- Export palette as JSON.
- Generate fallback color names when needed.

## Local Development

### Prerequisites
- Node.js 18+
- Python 3.10+
- A Gemini API key

### 1. Backend Setup

```bash
cd server
python -m venv ../venv
../venv/Scripts/activate
pip install -r requirements.txt
```

Create `server/.env`:

```dotenv
LLM_API_KEY=your_api_key_here
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-3.1-flash-lite-preview
GEMINI_API_VERSION=v1beta

BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
DEBUG=True
```

Run backend:

```bash
cd server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup

```bash
cd client
npm install
npm run dev
```

By default, frontend dev talks to `http://localhost:8000`.

## Environment Variables

### Backend (`server/.env`)
- `LLM_API_KEY`: Gemini API key.
- `LLM_PROVIDER`: currently `gemini`.
- `GEMINI_MODEL`: model name.
- `GEMINI_API_VERSION`: usually `v1beta`.
- `DEBUG`: `True` or `False`.

### Frontend (deployment env)
- `VITE_API_URL`: public backend base URL.

If `VITE_API_URL` is not set:
- Dev mode fallback: `http://localhost:8000`
- Production fallback: same origin (`window.location.origin`)

## API Endpoints

### `GET /`
Health check.

### `POST /api/generate-palette`
Generate palette from text.

Request body:

```json
{
	"prompt": "Ocean sunset with warm oranges and cool blues",
	"vibe": "vibrant"
}
```

### `POST /api/extract-palette`
Extract palette from image.

Supports:
- `application/json` for URL source
- `multipart/form-data` for file upload

JSON example:

```json
{
	"image_url": "https://example.com/image.jpg",
	"vibe": "pastel",
	"method": "ai"
}
```

FormData fields:
- `file`: image file
- `vibe`: vibe string
- `method`: `ai` or `local`

### `POST /api/refine-palette`
Refine current palette via instruction.

### `POST /api/generate-color-names`
Generate names for provided hex colors.

## Deployment Notes

### Important: avoid `localhost` in production

If your deployed frontend is calling `http://localhost:8000`, other users will fail with:
- `ERR_CONNECTION_REFUSED`
- `Failed to fetch`

Set `VITE_API_URL` in your frontend hosting environment (for example Vercel) to your public backend URL, then redeploy.

Example:

```text
VITE_API_URL=https://your-backend-domain.com
```

### CORS

Current CORS allowlist is defined in `server/main.py`:
- `http://localhost:5174`
- `https://palette-ai-delta.vercel.app`

If you deploy under a different frontend domain, update this list accordingly.


## License

See `LICENSE`.
