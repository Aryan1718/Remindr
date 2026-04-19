from __future__ import annotations

import unittest
from unittest.mock import patch

from app.workers.rq import enqueue_connector_sync


class WorkerRQTests(unittest.TestCase):
    @patch("app.workers.rq.get_settings")
    @patch("app.workers.jobs.connector_sync.sync_connector_job")
    def test_enqueue_connector_sync_runs_job_in_eager_mode(self, sync_job: patch, get_settings: patch) -> None:
        get_settings.return_value = type("Settings", (), {"connector_sync_eager": True})()

        result = enqueue_connector_sync(
            connector_id="connector-1",
            user_id="user-1",
            lookahead_days=14,
            lookback_days=7,
            force=False,
        )

        self.assertEqual(result.job_status, "completed")
        sync_job.assert_called_once_with(
            connector_id="connector-1",
            user_id="user-1",
            lookahead_days=14,
            lookback_days=7,
            force=False,
        )

    @patch("app.workers.rq.get_settings")
    def test_enqueue_connector_sync_returns_queued_when_eager_mode_disabled(self, get_settings: patch) -> None:
        get_settings.return_value = type("Settings", (), {"connector_sync_eager": False})()

        result = enqueue_connector_sync(
            connector_id="connector-1",
            user_id="user-1",
            lookahead_days=14,
            lookback_days=7,
            force=False,
        )

        self.assertEqual(result.job_status, "queued")


if __name__ == "__main__":
    unittest.main()
