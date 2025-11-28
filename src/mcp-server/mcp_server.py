# mcp_server.py
import os
import sys
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn
import uuid
import time
import json

# Add src folder to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agents.monitor_agent import run_monitor_once

load_dotenv()

app = FastAPI()


# ================================================================
# MCP MODELS
# ================================================================

class MCPRequest(BaseModel):
    id: str | int | None = None
    method: str
    params: dict | None = None
    jsonrpc: str = "2.0"


class MCPResponse(BaseModel):
    id: str | int | None
    result: dict | None = None
    error: dict | None = None
    jsonrpc: str = "2.0"


# ================================================================
# HEALTH CHECK
# ================================================================
@app.get("/health")
async def health():
    return {"status": "ok"}


# ================================================================
# MCP MAIN ENDPOINT
# ================================================================
@app.post("/mcp")
async def mcp_handler(request: Request):
    payload = await request.json()

    try:
        req = MCPRequest(**payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid MCP request format")

    # Basic MCP handshake (required)
    if req.method == "initialize":
        return MCPResponse(
            id=req.id,
            result={
                "capabilities": {
                    "tool.use": True,
                    "text.generate": False,
                    "resource.fetch": False,
                },
                "serverInfo": {
                    "name": "PolicyComplianceGuardian-MCP",
                    "version": "1.0.0",
                }
            }
        )

    # Example tool call
    if req.method == "tool/run-monitor":
        try:
            snapshot = await run_monitor_once(return_json=True)
            return MCPResponse(id=req.id, result=snapshot)
        except Exception as e:
            return MCPResponse(id=req.id, error={"message": str(e)})

    # Unhandled MCP method
    return MCPResponse(
        id=req.id,
        error={"message": f"Unknown MCP method '{req.method}'"}
    )


# ================================================================
# DIRECT FASTAPI ENDPOINT FOR DEBUGGING
# ================================================================
@app.get("/run-monitor")
async def run_monitor():
    try:
        return await run_monitor_once(return_json=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================================================
# SERVER ENTRYPOINT
# ================================================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("mcp_server:app", host="0.0.0.0", port=port)
