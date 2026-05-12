from __future__ import annotations

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("draftlens_api.main:app", host="127.0.0.1", port=8000, reload=True)
