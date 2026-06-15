import unittest

from eqgps.markers import Marker
from eqgps.timer_sound import TimerSoundNotifier, default_windows_sound_path


class TimerSoundTests(unittest.TestCase):
    def test_default_windows_sound_path_prefers_windows_media_notify_sound(self):
        path = default_windows_sound_path(system_root="C:/Windows", exists=lambda candidate: candidate.endswith("Windows Notify System Generic.wav"))

        self.assertEqual(path, "C:/Windows/Media/Windows Notify System Generic.wav")

    def test_notifier_fires_once_when_timer_becomes_ready_and_rearms_after_restart(self):
        marker = Marker(zone_key="qeynos", x=0, y=0, label="spawn", id="spawn1", timer_minutes=1, timer_started_at=0.0)
        notifier = TimerSoundNotifier()

        self.assertEqual(notifier.ready_marker_ids([marker], now=30.0), [])
        self.assertEqual(notifier.ready_marker_ids([marker], now=61.0), ["spawn1"])
        self.assertEqual(notifier.ready_marker_ids([marker], now=90.0), [])

        marker.timer_started_at = 200.0
        self.assertEqual(notifier.ready_marker_ids([marker], now=230.0), [])
        self.assertEqual(notifier.ready_marker_ids([marker], now=261.0), ["spawn1"])

    def test_notifier_uses_mmss_timer_seconds(self):
        marker = Marker(zone_key="qeynos", x=0, y=0, label="spawn", id="short", timer_seconds=45, timer_started_at=0.0)
        notifier = TimerSoundNotifier()

        self.assertEqual(notifier.ready_marker_ids([marker], now=44.0), [])
        self.assertEqual(notifier.ready_marker_ids([marker], now=45.0), ["short"])

    def test_notifier_ignores_markers_without_active_timer(self):
        marker = Marker(zone_key="qeynos", x=0, y=0, label="plain", id="plain")
        notifier = TimerSoundNotifier()

        self.assertEqual(notifier.ready_marker_ids([marker], now=999.0), [])


if __name__ == "__main__":
    unittest.main()
