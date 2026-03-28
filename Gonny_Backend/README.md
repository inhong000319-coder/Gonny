# Gonny Backend

FastAPI backend scaffold focused on role-B features:

- F03 estimated duration
- F04 weather-aware alternatives
- F05 companion preference merge
- F06 accommodations recommendation
- F07 transport recommendation (+ optional ODSay override)
- F08 restaurant recommendation
- F15 seasonal travel feed (+ optional TourAPI feed)

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

If Python is not installed globally, use the local runtime created during setup:

```powershell
& "c:\workspace\Gonny\tools\python311\runtime\python.exe" -m pip install -r .\requirements.txt
& "c:\workspace\Gonny\tools\python311\runtime\python.exe" -m uvicorn app.main:app --app-dir . --reload
```

## API docs

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/health`
