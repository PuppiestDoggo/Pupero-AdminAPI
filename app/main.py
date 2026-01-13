from fastapi import FastAPI, HTTPException, Request
import os
import httpx
import logging
import json
import time
from datetime import datetime

app = FastAPI(title="Pupero Admin API")

# Logger setup
logger = logging.getLogger("pupero_admin_api")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    # Stdout handler
    stdout_handler = logging.StreamHandler()
    logger.addHandler(stdout_handler)
    # Optional File handler
    log_file = os.getenv("LOG_FILE")
    if log_file:
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            from logging import FileHandler
            file_handler = FileHandler(log_file)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.error(json.dumps({"event": "file_logging_setup_failed", "error": str(e)}))

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = int((time.time() - start_time) * 1000)
    
    log_record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": "http_request",
        "service": "admin_api",
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "latency_ms": duration,
        "client": request.client.host if request.client else None,
    }
    logger.info(json.dumps(log_record))
    return response

# Base URLs to existing services (can point to API Manager if present)

def _normalize_service_url(val: str | None, kind: str) -> str:
    # kind: "transactions" or "monero"
    default = "http://api-manager:8000/transactions" if kind == "transactions" else "http://api-manager:8000/monero"
    if not val:
        return default
    v = val.strip().rstrip("/")
    if "://" in v:
        return v
    name = v
    if name in {"api-manager", "pupero-api-manager"}:
        base = f"http://{name}:8000"
        return base + ("/transactions" if kind == "transactions" else "/monero")
    if name in {"transactions", "pupero-transactions"}:
        return f"http://{name}:8003"
    if name in {"monero", "pupero-WalletManager"}:
        return f"http://{name}:8004"
    return default

TRANSACTIONS_BASE = _normalize_service_url(os.getenv("TRANSACTIONS_SERVICE_URL"), "transactions")
MONERO_BASE = _normalize_service_url(os.getenv("MONERO_SERVICE_URL"), "monero")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# Alias for k8s/monitoring expectations
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/user/{user_id}/balance")
def user_balance(user_id: int):
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(f"{TRANSACTIONS_BASE}/balance/{user_id}")
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail=r.text)
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/user/{user_id}/addresses")
def user_addresses(user_id: int):
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(f"{MONERO_BASE}/addresses", params={"user_id": user_id})
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail=r.text)
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/queue")
def queue_stats():
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(f"{MONERO_BASE}/admin/queue")
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail=r.text)
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.post("/drain")
def drain_queue():
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(f"{MONERO_BASE}/admin/drain")
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail=r.text)
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
