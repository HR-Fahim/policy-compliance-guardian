# mcp_server.py
import os
from fastapi import FastAPI, Request
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn
import sys
import os

# Add src folder to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.monitor_agent import run_monitor_once


load_dotenv()

app = FastAPI()

class MCPPayload(BaseModel):
    data: dict | None = None

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/mcp")
async def mcp(request: Request):
    body = await request.json()
    return {
        "ok": True,
        "received": body,
        "info": "Local MCP stub for development"
    }
# mcp_server.py
import os, sys
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agents.monitor_agent import run_monitor_once

load_dotenv()
app = FastAPI()

class MCPPayload(BaseModel):
    data: dict | None = None

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/mcp")
async def mcp(request: Request):
    return {"ok": True, "received": await request.json(), "info": "Local MCP stub"}

@app.get("/run-monitor")
async def run_monitor():
    try:
        return await run_monitor_once(return_json=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("mcp_server:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

from fastapi import FastAPI, HTTPException
import asyncio


@app.get("/run-monitor")
async def run_monitor():
    """
    Run monitor workflow and return JSON snapshot directly.
    """
    try:
        snapshot_json = await run_monitor_once(return_json=True)
        return snapshot_json
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("mcp_server:app", host="0.0.0.0", port=port)
