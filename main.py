from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

app = FastAPI(title="CPS Network Proxy")

# Разрешенные origin'ы для CORS
ALLOWED_ORIGINS = [
    "https://abobus307.github.io",
    "http://localhost:3000",
    "https://weao-proxy.onrender.com",
    "*"  # Для тестирования, потом можно убрать
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Базовый URL для weao.xyz
TARGET_BASE = "https://weao.xyz"
TIMEOUT = 10.0

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "CPS Network Proxy is running",
        "endpoints": {
            "status": "/api/status/exploits",
            "proxy": "/proxy/{path}"
        }
    }

@app.get("/api/status/exploits")
async def get_exploits_status(request: Request):
    """Прямой эндпоинт для статусов эксплойтов"""
    target_url = f"{TARGET_BASE}/api/status/exploits"
    
    headers = {
        "User-Agent": "CPS-Network-Proxy/1.0",
        "Accept": "application/json",
    }
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(target_url, headers=headers)
            response.raise_for_status()
            
            # Парсим JSON ответ
            data = response.json()
            
            return JSONResponse(
                content=data,
                status_code=response.status_code,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "public, max-age=300"  # Кэшируем на 5 минут
                }
            )
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502, 
            detail=f"Upstream request failed: {str(e)}"
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Upstream error: {e.response.status_code}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/proxy/{full_path:path}")
async def proxy_get(full_path: str, request: Request):
    """Общий прокси для любых путей"""
    # Проверка API key, если включён
    API_KEY = os.environ.get("API_KEY")
    if API_KEY:
        key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")

    # Собираем полный URL
    path_part = "/" + full_path if not full_path.startswith("/") else full_path
    target_url = f"{TARGET_BASE}{path_part}"

    # Добавляем query string, если есть
    query_string = request.scope.get("query_string", b"").decode()
    if query_string:
        join_char = "&" if "?" in target_url else "?"
        target_url = f"{target_url}{join_char}{query_string}"

    headers = {
        "User-Agent": "CPS-Network-Proxy/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(target_url, headers=headers)
            resp.raise_for_status()
            
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {e}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Upstream error: {e.response.status_code}")

    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            data = resp.json()
            return JSONResponse(
                content=data,
                status_code=resp.status_code,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        except Exception:
            return PlainTextResponse(
                status_code=resp.status_code, 
                content=resp.text,
                headers={"Access-Control-Allow-Origin": "*"}
            )
    else:
        return PlainTextResponse(
            status_code=resp.status_code, 
            content=resp.text,
            headers={"Access-Control-Allow-Origin": "*"}
        )

# Health check эндпоинт
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "CPS Network Proxy"}

# Эндпоинт для проверки прокси
@app.get("/test")
async def test_proxy():
    """Тестовый эндпоинт для проверки работы прокси"""
    return {
        "message": "Proxy is working correctly",
        "timestamp": "2024-01-01T00:00:00Z",  # Здесь можно добавить реальное время
        "status": "operational"
    }
