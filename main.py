from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

app = FastAPI(title="Simple HTTPS -> HTTP proxy")

# Разрешенные origin'ы для CORS (добавь сюда свой фронтенд)
ALLOWED_ORIGINS = [
    "https://abobus307.github.io/CpsHubSite/",   # <-- поменяй на свой GitHub Pages
    "https://weao-proxy.onrender.com",    # для тестов прямо с домена Render
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Можно задать базовый URL через переменную окружения, если нужно
TARGET_BASE = os.environ.get("TARGET_BASE", "http://farts.fadedis.xyz")
TIMEOUT = 10.0

# API-ключ (опционально, можешь пока не задавать)
API_KEY = os.environ.get("API_KEY")

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Proxy is running. Use /proxy/<path> to access upstream.",
        "target_base": TARGET_BASE,
    }

@app.get("/proxy/{full_path:path}")
async def proxy_get(full_path: str, request: Request):
    # Проверка API key, если включён
    if API_KEY:
        key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")

    # Собираем полный URL до целевого HTTP-сервера
    # full_path приходит без ведущего "/", поэтому добавим сами
    path_part = "/" + full_path if not full_path.startswith("/") else full_path

    target_url = f"{TARGET_BASE}{path_part}"

    # Добавляем query string, если есть
    query_string = request.scope.get("query_string", b"").decode()
    if query_string:
        join_char = "&" if "?" in target_url else "?"
        target_url = f"{target_url}{join_char}{query_string}"

    # Простейшие заголовки
    headers = {
        "User-Agent": "render-proxy/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(target_url, headers=headers)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {e}")

    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type:
        # Если это JSON
        try:
            data = resp.json()
        except Exception:
            # Если невалидный JSON, вернем как текст
            return PlainTextResponse(status_code=resp.status_code, content=resp.text)
        return JSONResponse(status_code=resp.status_code, content=data)
    else:
        # Всё остальное — как текст
        return PlainTextResponse(status_code=resp.status_code, content=resp.text)
