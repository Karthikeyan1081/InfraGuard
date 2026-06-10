import os
import asyncio
import logging
import requests
from .agent_llm import AgentLLM


class AgentService:
    """Simple orchestrator agent that watches the `uploads/` folder and
    triggers a reconciliation run via the local API when a CMDB + Actual
    pair is detected.

    Designed as a minimal, safe prototype for hosted deployments. Uses
    environment variables for configuration and does not perform
    destructive actions.
    """

    def __init__(self, api_base: str | None = None, watch_dir: str | None = None, poll_interval: int = 8):
        self.api_base = api_base or os.environ.get("ASSETSYNC_API_BASE", "http://127.0.0.1:8000")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.watch_dir = watch_dir or os.path.join(base_dir, "uploads")
        self.poll_interval = int(os.environ.get("AGENT_POLL_INTERVAL", poll_interval))
        self._seen = set()
        self._task: asyncio.Task | None = None
        self.session = requests.Session()
        # LLM helper (lazy init)
        self._llm: AgentLLM | None = None

    async def _watch_loop(self):
        logging.info("Agent watcher running, monitoring: %s", self.watch_dir)
        while True:
            try:
                entries = sorted(os.listdir(self.watch_dir))
            except Exception:
                entries = []

            for fn in entries:
                if fn in self._seen:
                    continue
                path = os.path.join(self.watch_dir, fn)
                if not os.path.isfile(path):
                    continue

                # Simple filename heuristics used by the project samples
                is_cmdb = fn.lower().startswith("cmdb") or fn.lower().endswith(".csv")
                is_actual = fn.lower().startswith("actual") or fn.lower().endswith(".json")
                if not (is_cmdb or is_actual):
                    # not an inventory file we care about
                    self._seen.add(fn)
                    continue

                # mark seen and attempt to find a counterpart
                self._seen.add(fn)
                await self.handle_new_upload(path)

            await asyncio.sleep(self.poll_interval)

    async def handle_new_upload(self, file_path: str):
        logging.info("Agent detected new upload: %s", file_path)

        # Find counterpart file (simple heuristic)
        try:
            for other in os.listdir(self.watch_dir):
                if other == os.path.basename(file_path):
                    continue
                if (other.lower().startswith("cmdb") and os.path.basename(file_path).lower().startswith("actual")) or (
                    other.lower().startswith("actual") and os.path.basename(file_path).lower().startswith("cmdb")
                ):
                    counterpart = os.path.join(self.watch_dir, other)
                    if os.path.isfile(counterpart):
                        await self._trigger_analyze(file_path, counterpart)
                        return

            # If no counterpart yet, log and wait for the next poll
            logging.info("No counterpart found yet for %s; will retry later.", file_path)
        except Exception:
            logging.exception("Error while handling new upload: %s", file_path)

    async def _trigger_analyze(self, file_a: str, file_b: str):
        # Determine which is CMDB vs Actual by filename
        a_name = os.path.basename(file_a).lower()
        b_name = os.path.basename(file_b).lower()
        if a_name.startswith("cmdb") or a_name.endswith(".csv"):
            cmdb_path, actual_path = file_a, file_b
        else:
            cmdb_path, actual_path = file_b, file_a

        payload = {
            "name": f"Agent auto run - {os.path.basename(cmdb_path)}",
            "cmdb_file_path": cmdb_path,
            "actual_file_path": actual_path,
        }

        try:
            url = f"{self.api_base}/api/analyze"
            logging.info("Triggering analyze via %s", url)
            resp = self.session.post(url, json=payload, timeout=60)
            logging.info("Analyze response: %s (HTTP %s)", resp.text[:400], resp.status_code)
        except Exception:
            logging.exception("Failed to call analyze endpoint")

    async def run_and_summarize(self, cmdb_path: str, actual_path: str) -> dict:
        """Trigger analyze via API, fetch the created analysis, index discrepancies and return an LLM summary.

        Returns a dict: {"analysis_id": str, "summary": str}
        """
        url = f"{self.api_base}/api/analyze"
        payload = {
            "name": f"Agent triggered run - {os.path.basename(cmdb_path)}",
            "cmdb_file_path": cmdb_path,
            "actual_file_path": actual_path,
        }

        def do_post():
            return self.session.post(url, json=payload, timeout=60)

        # Run blocking request in thread to avoid blocking event loop
        resp = await asyncio.to_thread(do_post)
        if resp.status_code not in (200, 201):
            logging.error("Analyze API failed: %s", resp.text)
            return {"error": "analyze_failed", "http_status": resp.status_code, "body": resp.text}

        # Expect response contains analysis id
        try:
            body = resp.json()
            analysis_id = body.get("id") or body.get("analysis_id")
        except Exception:
            analysis_id = None

        # If id not returned, attempt to fetch latest run list and pick matching name
        if not analysis_id:
            list_url = f"{self.api_base}/api/analyses"
            list_resp = await asyncio.to_thread(self.session.get, list_url, {})
            try:
                analyses = list_resp.json()
                # pick the most recent run that matches name
                for a in analyses:
                    if a.get("name", "").startswith("Agent triggered run"):
                        analysis_id = a.get("id")
                        break
            except Exception:
                logging.exception("Failed to parse analyses list")

        if not analysis_id:
            return {"error": "no_analysis_id"}

        # Fetch analysis detail
        detail_url = f"{self.api_base}/api/analyses/{analysis_id}"
        detail_resp = await asyncio.to_thread(self.session.get, detail_url)
        try:
            detail = detail_resp.json()
        except Exception:
            logging.exception("Failed to fetch analysis detail for %s", analysis_id)
            return {"error": "detail_fetch_failed"}

        discrepancies = detail.get("discrepancies", [])

        # Initialize LLM helper and index
        if self._llm is None:
            self._llm = AgentLLM()

        try:
            self._llm.index_discrepancies(discrepancies)
        except Exception:
            logging.exception("Failed to index discrepancies")

        try:
            summary = self._llm.summarize_discrepancies(discrepancies)
        except Exception:
            logging.exception("LLM summarization failed")
            summary = "LLM summarization unavailable"

        return {"analysis_id": analysis_id, "summary": summary}

    def start(self):
        if self._task is not None:
            logging.info("Agent already started")
            return

        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._watch_loop())
        logging.info("Agent started")

    def stop(self):
        if self._task:
            self._task.cancel()
            self._task = None
            logging.info("Agent stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = AgentService()
    try:
        agent.start()
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        agent.stop()
