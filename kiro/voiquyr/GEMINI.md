# Project Overview

This project is a command center for monitoring a real-time communication system. It provides a dashboard to visualize key metrics like latency, active calls, GPU utilization, and cost. It also allows for simulating flash events and configuring the system.

The project is a full-stack application with a React frontend and a Python backend.

**Frontend:**

*   **Framework:** React with Vite
*   **Language:** TypeScript
*   **Styling:** Tailwind CSS (via CDN in `index.html`)
*   **Module Loading:** ESM with `importmap` for production-grade CDNs
*   **Key Libraries:**
    *   `recharts` for charting
    *   `lucide-react` for icons

**Backend:**

*   **Framework:** FastAPI
*   **Language:** Python
*   **Key Libraries:**
    *   `uvicorn` for serving the application
    *   `deepgram-sdk`, `openai`, `elevenlabs` for AI and speech processing
    *   `websockets` for real-time communication
    *   `redis` for state management
    *   `pydantic-settings` for configuration

# Building and Running

**Prerequisites:**

*   Node.js (v18+)
*   Python (3.10+)

**Frontend:**

1.  Navigate to the `frontend` directory: `cd voiquyr-command-center/frontend`
2.  Install dependencies: `npm install`
3.  Set the `GEMINI_API_KEY` in `.env` (Vite loads from project root or frontend dir depending on config).
4.  Run the app: `npm run dev` (runs on port 3000)

**Backend:**

1.  Navigate to the `backend` directory: `cd voiquyr-command-center/backend`
2.  Install dependencies: `pip install -r requirements.txt`
3.  Run the app: `python main.py` or `uvicorn main:app --reload`

# Development Conventions

*   The project uses TypeScript in the frontend for type safety.
*   The frontend uses a modern ESM approach with `importmap` for certain dependencies.
*   The backend follows a modular FastAPI structure with routers in the `app/routers` directory.
*   The project is divided into a `frontend` and `backend` directory within the `voiquyr-command-center` folder.
