import os
import json
import datetime
import shutil
from pathlib import Path
from dotenv import load_dotenv

import google.generativeai as genai
from google.generativeai import GenerativeModel

load_dotenv()


def newest_file(files):
    """Return the newest file from a list of Path objects."""
    if not files:
        return None
    return max(files, key=lambda f: f.stat().st_mtime)


class AuthorizerAgent:
    """
    Policy Authorizer Agent using gemini-2.5-pro.
    """

    def __init__(self):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = GenerativeModel(model_name="gemini-2.5-pro")

    def read_latest_files(self, input_dir: Path) -> dict:
        """Reads the newest summary, json, and raw text files from the monitored snapshot folder."""

        # Match summary: monitored_file_summary.TIMESTAMP.txt
        summary_files = list(input_dir.glob("monitored_file_summary.*.txt"))

        # Match json: monitored_file.TIMESTAMP.json
        json_files = list(input_dir.glob("monitored_file.*.json"))

        # Match raw text: raw_monitored_file.TIMESTAMP.txt
        raw_files = list(input_dir.glob("raw_monitored_file.*.txt"))

        latest_summary = newest_file(summary_files)
        latest_json = newest_file(json_files)
        latest_raw = newest_file(raw_files)

        data = {}

        if latest_summary:
            data["summary_file"] = latest_summary
            data["summary_text"] = latest_summary.read_text(encoding="utf-8")

        if latest_json:
            data["json_file"] = latest_json
            try:
                data["json_obj"] = json.loads(latest_json.read_text(encoding="utf-8"))
            except:
                data["json_obj"] = {}

        if latest_raw:
            data["raw_text_file"] = latest_raw
            data["raw_text"] = latest_raw.read_text(encoding="utf-8")

        return data

    async def analyze_and_process(self, input_dir: Path, output_dir: Path):
        output_dir.mkdir(parents=True, exist_ok=True)

        files = self.read_latest_files(input_dir)
        summary_text = files.get("summary_text", "")
        json_obj = files.get("json_obj", {})
        raw_text = files.get("raw_text", "")

        # Construct analysis prompt
        prompt = f"""
            You are an advanced Policy Authorizer & Source Validity Evaluator with internet-level validation capabilities.

            Use google_search needed to:
            - Verify if the policy content aligns with official sources.
            - Verify if the policy names, versions, or dates appear real or tampered.
            - Check if referenced metadata matches real-world policy standards.
            - Check if timestamps or legal references exist externally.

            INPUT DATA:
            SUMMARY:
            {summary_text}

            JSON CONTENT:
            {json.dumps(json_obj, indent=2)}

            RAW TEXT:
            {raw_text}

            OUTPUT FORMAT (strict JSON only):
            {{
            "should_update": true,
            "issues_detected": [],
            "corrected_summary": "",
            "corrected_json": {{}},
            "corrected_raw_text": ""
            }}
        """

        resp = self.model.generate_content(prompt)

        # HARD JSON ENFORCEMENT
        raw_output = resp.text.strip()

        if raw_output.startswith("```"):
            raw_output = raw_output.strip("```json").strip("```").strip()

        try:
            result = json.loads(raw_output)
        except Exception:
            raise ValueError("Gemini returned invalid JSON:\n" + raw_output)

        should_update = result.get("should_update", False)

        # CASE 1: NO UPDATE → copy originals
        if not should_update:
            for f in input_dir.glob("*"):
                shutil.copy(f, output_dir / f.name)
            return {"decision": "UNCHANGED", "details": result}

        # CASE 2: UPDATE → write authorized files
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        (output_dir / f"summary_authorized_{timestamp}.txt").write_text(
            result.get("corrected_summary", ""),
            encoding="utf-8"
        )

        (output_dir / f"policy_authorized_{timestamp}.json").write_text(
            json.dumps(result.get("corrected_json", {}), indent=2),
            encoding="utf-8"
        )

        (output_dir / f"raw_authorized_{timestamp}.txt").write_text(
            result.get("corrected_raw_text", ""),
            encoding="utf-8"
        )

        return {"decision": "UPDATED", "details": result}
