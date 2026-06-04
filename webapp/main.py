from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from dijkstrabot.filters import FilterConfig, AudienceConfig, CreatorConfig, PerformanceConfig, OutputConfig
from main import run_discovery
import asyncio
import os

app = FastAPI(title="DijkstraBot Web Interface")

# Mount static files
app.mount("/static", StaticFiles(directory="webapp/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    with open("webapp/static/index.html", "r") as f:
        return f.read()

@app.post("/run")
async def run_bot(
    category: str = Form(...),
    hashtags: str = Form(""),
    follower_min: int = Form(1000),
    follower_max: int = Form(1000000),
    keywords: str = Form(""),
    location: str = Form("")
):
    # Construct FilterConfig from form data
    config = FilterConfig(
        audience=AudienceConfig(
            follower_min=follower_min,
            follower_max=follower_max,
            location_country=location if location else None
        ),
        creator=CreatorConfig(
            category=category,
            bio_hashtags=[h.strip() for h in hashtags.split(",") if h.strip()],
            bio_keywords=[k.strip() for k in keywords.split(",") if k.strip()]
        ),
        output=OutputConfig(max_results=50) # Limit for web preview
    )
    
    # Run discovery in the background
    asyncio.create_task(run_discovery(config, no_sheets=True))
    
    return {"status": "started", "config": config}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
