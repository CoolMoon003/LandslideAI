# LandslideAI FastAPI Backend

This backend is designed for the existing YHACK-LANDSLIDE project and reads the generated processed data directly from the repository.

## Project location

Place this folder as:

`C:\Users\Naveen\Desktop\YHACK-LANDSLIDE\backend`

The backend expects `data/processed` and `models` to remain at the project root.

## Run

```powershell
cd C:\Users\Naveen\Desktop\YHACK-LANDSLIDE
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000
```

## Test

Open:

`http://127.0.0.1:8000/api/health`

API docs:

`http://127.0.0.1:8000/docs`

## Frontend

Run the React frontend separately with `npm run dev`.
