"""
API 网关启动入口
"""
import sys
import os
import time
import uvicorn
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from services.svr_gateway.routes import router
from services.svr_gateway.config import gateway_config
from thirdparty.log import setup_logger, get_logger

setup_logger(log_level="INFO")
logger = get_logger("gateway")

app = FastAPI(
    title="FAMS-NEPU API Gateway",
    description="高校固定资产协同管理系统 API 网关",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration:.3f}s)")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.opt(exception=True).error(f"Unhandled exception on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "data": None},
    )


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "gateway"}


if __name__ == "__main__":
    logger.info(f"Gateway starting on port {gateway_config.HTTP_PORT}, PID={os.getpid()}")
    uvicorn.run(app, host="0.0.0.0", port=gateway_config.HTTP_PORT)
