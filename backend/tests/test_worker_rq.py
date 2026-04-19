from __future__ import annotations

import unittest
from unittest.mock import patch

from app.workers.rq import enqueue_connector_sync, enqueue_memory_distillation, enqueue_notification_delivery


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

    @patch("app.workers.rq.get_settings")
    @patch("app.workers.jobs.memory_distillation.distill_memories_job")
    def test_enqueue_memory_distillation_runs_job_in_eager_mode(self, memory_job: patch, get_settings: patch) -> None:
        get_settings.return_value = type("Settings", (), {"memory_distillation_eager": True})()

        result = enqueue_memory_distillation(user_id="user-1", days_back=30)

        self.assertEqual(result.job_status, "completed")
        memory_job.assert_called_once_with(
            user_id="user-1",
            days_back=30,
            trigger_source=None,
            force=False,
            entity_type=None,
            entity_id=None,
        )

    @patch("app.workers.rq.get_settings")
    def test_enqueue_memory_distillation_returns_queued_when_eager_mode_disabled(self, get_settings: patch) -> None:
        get_settings.return_value = type("Settings", (), {"memory_distillation_eager": False})()

        result = enqueue_memory_distillation(
            user_id="user-1",
            trigger_source="task_complete",
            entity_type="task",
            entity_id="task-1",
        )

        self.assertEqual(result.job_status, "queued")

    @patch("app.workers.rq.get_settings")
    @patch("app.workers.jobs.notification_jobs.deliver_notification_job")
    def test_enqueue_notification_delivery_runs_job_in_eager_mode(self, notification_job: patch, get_settings: patch) -> None:
        get_settings.return_value = type(
            "Settings",
            (),
            {"notification_delivery_eager": True, "database_url": "postgresql://example"},
        )()

        result = enqueue_notification_delivery(notification_id="notification-1")

        self.assertEqual(result.job_status, "completed")
        notification_job.assert_called_once_with(
            database_url="postgresql://example",
            notification_id="notification-1",
        )

    @patch("app.workers.rq.get_settings")
    def test_enqueue_notification_delivery_returns_queued_when_eager_mode_disabled(self, get_settings: patch) -> None:
        get_settings.return_value = type(
            "Settings",
            (),
            {"notification_delivery_eager": False, "database_url": "postgresql://example"},
        )()

        result = enqueue_notification_delivery(notification_id="notification-1")

        self.assertEqual(result.job_status, "queued")


if __name__ == "__main__":
    unittest.main()
