import os
import sys
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn
import json
from pathlib import Path

# Add src/ to module path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Core agent + configuration
from agents.monitor_agent import monitor

load_dotenv()
app = FastAPI()

# Directory to store snapshots and updated files
SNAPSHOT_DIR_MONITORED = Path(__file__).parent.parent /"temp/data/monitored_snapshots"
SNAPSHOT_DIR_AUTHORIZED = Path(__file__).parent.parent /"temp/data/authorized_snapshots"

# print("Snapshot directory:", SNAPSHOT_DIR)

# Default user email from environment
DEFAULT_USER_EMAIL = os.getenv("USER_EMAIL")
user_email = DEFAULT_USER_EMAIL


# ------------------------------------------------------------
# MCP Models
# ------------------------------------------------------------
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


# ------------------------------------------------------------
# Health check
# ------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}


# ------------------------------------------------------------
# MCP Handler
# ------------------------------------------------------------
@app.post("/mcp")
async def mcp_handler(request: Request):
    payload = await request.json()

    try:
        req = MCPRequest(**payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid MCP request format")

    # Standard MCP handshake
    if req.method == "initialize":
        return MCPResponse(
            id=req.id,
            result={
                "capabilities": {"tool.use": True},
                "serverInfo": {"name": "PolicyComplianceGuardian-MCP", "version": "1.0.0"},
            }
        )

    # Tool call: run monitor once
    if req.method == "tool/monitord-file":
        try:
            snapshot = await monitor(return_json=True)
            return MCPResponse(id=req.id, result=snapshot)
        except Exception as e:
            return MCPResponse(id=req.id, error={"message": str(e)})

    # Unknown method
    return MCPResponse(
        id=req.id,
        error={"message": f"Unknown MCP method '{req.method}'"}
    )


# ------------------------------------------------------------
# Direct run endpoint for debug/testing
# ------------------------------------------------------------
@app.get("/monitored-file")
async def run_monitor():
    try:
        return await monitor(return_json=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------
# Returns latest JSON snapshot for this user
# GET /{default_user_email}/monitored-file
# ------------------------------------------------------------
@app.get("/{user_email}/monitored-file")
async def get_latest_snapshot(user_email: str):
    if user_email != DEFAULT_USER_EMAIL:
        raise HTTPException(status_code=404, detail="not found")

    user_dir = Path(SNAPSHOT_DIR_MONITORED) / f"{user_email}_monitored_file"
    if not user_dir.exists():
        raise HTTPException(status_code=404, detail="not found")

    # Match files like: email.monitored_file.YYYYMMDD_HHMMSS.json
    json_files = list(user_dir.glob(f"monitored_file.*.json"))
    if not json_files:
        raise HTTPException(status_code=404, detail="not found")

    # Extract timestamp from filename to sort correctly
    def extract_timestamp(path: Path) -> str:
        # filename format: monitored_file.<timestamp>.json
        return path.stem.split(".")[1] # returns <timestamp>

    latest_file = max(json_files, key=lambda f: extract_timestamp(f))

    try:
        content = json.loads(latest_file.read_text(encoding="utf-8"))
        return {"file": latest_file.name, "data": content}
    except Exception:
        raise HTTPException(status_code=500, detail="failed to read snapshot")

# ------------------------------------------------------------
# Returns latest JSON snapshot for this user
# GET /{default_user_email}/authorized-file
# ------------------------------------------------------------
@app.get("/{user_email}/authorized-file")
async def get_latest_snapshot(user_email: str):
    if user_email != DEFAULT_USER_EMAIL:
        raise HTTPException(status_code=404, detail="not found")      

    user_dir = Path(SNAPSHOT_DIR_AUTHORIZED) / f"{user_email}_authorized_file"
    if not user_dir.exists():
        raise HTTPException(status_code=404, detail="not found")

    # Match files like: email.monitored_file.YYYYMMDD_HHMMSS.json
    json_files = list(user_dir.glob(f"policy_authorized.*.json"))
    if not json_files:
        raise HTTPException(status_code=404, detail="not found")

    # Extract timestamp from filename to sort correctly
    def extract_timestamp(path: Path) -> str:
        # filename format: monitored_file.<timestamp>.json
        return path.stem.split(".")[1] # returns <timestamp>

    latest_file = max(json_files, key=lambda f: extract_timestamp(f))

    try:
        content = json.loads(latest_file.read_text(encoding="utf-8"))
        return {"file": latest_file.name, "data": content}
    except Exception:
        raise HTTPException(status_code=500, detail="failed to read snapshot")
    
# ------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("mcp_server:app", host="0.0.0.0", port=port)
