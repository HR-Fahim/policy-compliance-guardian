# src/agents/comparison_agent.py

import os
import json
import difflib
from pathlib import Path
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types as genai_types

load_dotenv()  # load .env into os.environ


SNAPSHOT_DIR = Path("data/snapshots")
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


class ComparisonAgent:
    """
    Builds an LlmAgent that compares two policy versions (or snapshots) and
    explains the differences + potential compliance impact.

    It provides tools for:
    - loading JSON snapshots from disk
    - computing a textual diff between two strings
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY is not set. Please export it or pass api_key explicitly."
            )

        self.retry_options = genai_types.HttpRetryOptions(
            attempts=5,
            exp_base=7,
            initial_delay=1,
            http_status_codes=[429, 500, 503, 504],
        )

        self.llm = Gemini(
            model="gemini-2.5-flash-lite",
            api_key=self.api_key,
            retry_options=self.retry_options,
        )

        self.agent = LlmAgent(
            name="comparison_agent",
            model=self.llm,
            description=(
                "Compares two versions of a policy or document and explains "
                "the differences and their potential compliance impact."
            ),
            instruction="""
You are a comparison agent for policy documents.

You will usually be given either:
- two raw text versions of a policy, or
- paths to JSON snapshots created by the monitor agent.

Available tools:
- `load_snapshot(snapshot_path)` to load a JSON snapshot from disk.
- `compute_diff(old_text, new_text)` to get a unified text diff.

Your job:
1. If given snapshot paths, use `load_snapshot` to read them and extract:
   - file_path
   - file_content
   - (optionally) search_result
2. Use `compute_diff` on the old and new file_content to get a unified diff.
3. Analyze the diff and produce a structured explanation covering:
   - High-level summary of changes (bulleted list)
   - Classification of changes: editorial vs substantive vs compliance-impacting
   - Any sections that look riskier or worth legal review
4. In your final answer, clearly separate sections, for example:
   - "Summary of Changes"
   - "Detailed Differences"
   - "Compliance / Risk Assessment"

If tools fail (missing snapshot, invalid JSON, etc.), explain what happened
and what the user should fix.
""",
            tools=[
                self.load_snapshot,
                self.compute_diff,
            ],
        )

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------
    @staticmethod
    def load_snapshot(snapshot_path: str) -> Dict[str, Any]:
        """
        Load a JSON snapshot created by the monitor agent.

        Args:
            snapshot_path: Path to the snapshot JSON file.

        Returns:
            Parsed JSON as a dict.
        """
        path = Path(snapshot_path)
        if not path.is_file():
            raise FileNotFoundError(f"Snapshot not found: {snapshot_path}")

        text = path.read_text(encoding="utf-8")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in snapshot {snapshot_path}: {e}") from e

    @staticmethod
    def compute_diff(
        old_text: str,
        new_text: str,
        context_lines: int = 3,
    ) -> str:
        """
        Compute a unified diff between two text versions.

        Args:
            old_text: The baseline / previous version.
            new_text: The updated / current version.
            context_lines: Number of context lines to include in the diff.

        Returns:
            A unified diff string.
        """
        old_lines: List[str] = old_text.splitlines(keepends=True)
        new_lines: List[str] = new_text.splitlines(keepends=True)

        diff_lines = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile="baseline",
                tofile="updated",
                n=context_lines,
            )
        )
        return "".join(diff_lines) if diff_lines else "[No textual differences detected]"

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def get_agent(self) -> LlmAgent:
        """
        Return the underlying LlmAgent.
        """
        return self.agent
