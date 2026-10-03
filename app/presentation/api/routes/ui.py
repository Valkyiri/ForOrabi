from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse
STATIC_DIR = Path(__file__).resolve().parents[2] / 'static'
INDEX_FILE = STATIC_DIR / 'index.html'
router = APIRouter(tags=['ui'])

@router.get('/', include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(INDEX_FILE)

@router.get('/ui', include_in_schema=False)
async def chat_ui() -> FileResponse:
    return FileResponse(INDEX_FILE)
