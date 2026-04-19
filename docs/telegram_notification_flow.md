# Telegram Notification Flow

This implementation keeps Telegram as the delivery surface only.

Flow:

1. A backend service or watcher creates a `notifications` row through `NotificationService`.
2. The notification is stored with backend-owned state such as `user_id`, optional `task_id` / `calendar_block_id`, `channel`, `scheduled_for`, `status`, and `metadata_json`.
3. `NotificationService.enqueue_delivery(...)` pushes a delivery job onto the notifications queue.
4. `deliver_notification_job(...)` loads the notification, acquires a delivery lock, verifies it is still `queued`, and only then proceeds.
5. `TelegramNotificationDispatcher` converts the notification metadata into short Telegram text plus optional inline keyboards.
6. Delivery uses the existing `TelegramService.send_linked_message(...)` path.
7. On success the notification is marked `sent` with `sent_at` and optional `provider_message_id`.
8. On failure the notification is marked `failed` and the error is recorded in metadata and logs.

Supported proactive shapes:

- generic reminder
- internal calendar suggestion reminder
- task due-soon alert
- fatigue check prompt

Inline buttons reuse the existing Telegram callback path so action handling continues through `AgentService` and domain services rather than the delivery worker.
