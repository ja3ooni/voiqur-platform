# Project Overview

This project is a command center for monitoring a real-time communication system. It provides a dashboard to visualize key metrics like latency, active calls, GPU utilization, and cost. It also allows for simulating flash events and configuring the system.

The project is a full-stack application with a React frontend and a Python backend.

**Frontend:**

*   **Framework:** React with Vite
*   **Language:** TypeScript
*   **Styling:** Tailwind CSS (inferred from class names)
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

# Building and Running

**Prerequisites:**

*   Node.js
*   Python

**Frontend:**

1.  Navigate to the `frontend` directory: `cd voiquyr-command-center/frontend`
2.  Install dependencies: `npm install`
3.  Set the `GEMINI_API_KEY` in `.env.local` to your Gemini API key.
4.  Run the app: `npm run dev`

**Backend:**

1.  Navigate to the `backend` directory: `cd voiquyr-command-center/backend`
2.  Install dependencies: `pip install -r requirements.txt`
3.  Run the app: `uvicorn main:app --reload` (TODO: Verify the command to run the backend)

# Development Conventions

*   The project uses TypeScript in the frontend, which suggests a preference for static typing.
*   The use of FastAPI in the backend suggests a modern, asynchronous approach to building APIs.
*   The project is divided into a `frontend` and `backend` directory, which is a common convention for full-stack applications.
