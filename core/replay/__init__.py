"""
BOS Replay Engine — Public API
================================
Event Store = truth archive.
Replay Engine = time machine.
Time machine must never change history.

Imports are deferred to avoid circular import during app loading.
Use: from core.replay.event_replayer import replay_events
"""
