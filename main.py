import json
import time
import uuid
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

EMAIL = "23f1001027@ds.study.iitm.ac.in"
START = time.time()

request_count = 0
LOGS = deque(maxlen=2000)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observe(request: Request, call_next):
    global request_count
    request_count += 1
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        if request.url.path != "/logs/tail":
            entry = {
                "level": "INFO" if status < 400 else "ERROR",
                "ts": datetime.now(timezone.utc).isoformat(),
                "path": request.url.path,
                "request_id": request_id,
                "method": request.method,
                "status": status,
                "duration_ms": round((time.perf_counter() - start) * 1000, 3),
            }
            LOGS.append(entry)
            print(json.dumps(entry), flush=True)


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/work")
def work(n: int = 1):
    total = 0
    for i in range(min(max(n, 0), 1_000_000)):   # K units of (tiny) work
        total += i
    return {"email": EMAIL, "done": n}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return (
        "# HELP http_requests_total Total HTTP requests received.\n"
        "# TYPE http_requests_total counter\n"
        f"http_requests_total {request_count}\n"
    )


@app.get("/healthz")
def healthz():
    return {"status": "ok", "uptime_s": round(time.time() - START, 3)}


@app.get("/logs/tail")
def logs_tail(limit: int = 10):
    limit = max(0, limit)
    return list(LOGS)[-limit:] if limit else []
