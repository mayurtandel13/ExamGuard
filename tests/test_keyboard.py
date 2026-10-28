"""
Standalone verification test suite for Keyboard Monitoring Module.
Tests shortcut detection for Alt+Tab, Ctrl+C, Ctrl+V, Windows key, Print Screen,
event frequency calculation, inter-event timing, keyboard penalty scaling, and safe start/stop control.
"""

import time
import unittest
from keyboard.monitor import KeyboardMonitor


class TestKeyboardMonitor(unittest.TestCase):
    def setUp(self):
        self.kb = KeyboardMonitor(decay_seconds=5.0, base_penalty=0.2)

    def test_safe_start_and_stop(self):
        self.assertFalse(self.kb.is_running)
        self.kb.start()
        self.assertTrue(self.kb.is_running)
        self.kb.stop()
        self.assertFalse(self.kb.is_running)

    def test_individual_shortcut_triggers(self):
        shortcuts_to_test = ["alt+tab", "ctrl+c", "ctrl+v", "win", "print_screen"]

        for sc in shortcuts_to_test:
            self.kb.reset()
            self.kb.trigger_simulated_shortcut(sc)
            events = self.kb.get_recent_events()
            
            self.assertEqual(len(events), 1)
            evt = events[0]
            self.assertEqual(evt["shortcut"], sc)
            self.assertEqual(evt["event_type"], "SUSPICIOUS_SHORTCUT")
            self.assertIn("timestamp", evt)
            self.assertIn("inter_event_timing", evt)

    def test_isolated_shortcut_penalty_not_cheating(self):
        self.kb.reset()
        self.kb.trigger_simulated_shortcut("alt+tab")
        telemetry = self.kb.get_telemetry()

        self.assertEqual(telemetry["event_frequency"], 1)
        # Single isolated shortcut should produce low penalty (0.2), NOT cheating
        self.assertEqual(telemetry["keyboard_penalty"], 0.2)

    def test_event_frequency_and_inter_event_timing(self):
        self.kb.reset()
        
        # Trigger first event
        self.kb.trigger_simulated_shortcut("ctrl+c")
        time.sleep(0.1)
        # Trigger second event
        self.kb.trigger_simulated_shortcut("ctrl+v")

        telemetry = self.kb.get_telemetry()
        self.assertEqual(telemetry["event_frequency"], 2)
        self.assertGreater(telemetry["latest_inter_event_timing"], 0.0)
        self.assertGreater(telemetry["keyboard_penalty"], 0.2)

    def test_alt_tab_physical_key_press(self):
        """Verify Alt+Tab detection with Left Alt and Tab."""
        from pynput import keyboard
        self.kb.reset()
        self.kb._on_press(keyboard.Key.alt_l)
        self.kb._on_press(keyboard.Key.tab)
        events = self.kb.get_recent_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["shortcut"], "alt+tab")
        self.kb._on_release(keyboard.Key.tab)
        self.kb._on_release(keyboard.Key.alt_l)

    def test_ctrl_c_windows_key_press(self):
        """Verify Ctrl+C detection with Windows control character \\x03 and vk=67."""
        from pynput import keyboard
        self.kb.reset()
        self.kb._on_press(keyboard.Key.ctrl_l)
        self.kb._on_press(keyboard.KeyCode(char="\x03", vk=67))
        events = self.kb.get_recent_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["shortcut"], "ctrl+c")
        self.kb._on_release(keyboard.KeyCode.from_char("c"))
        self.kb._on_release(keyboard.Key.ctrl_l)

    def test_ctrl_v_windows_key_press(self):
        """Verify Ctrl+V detection with Windows control character \\x16 and vk=86."""
        from pynput import keyboard
        self.kb.reset()
        self.kb._on_press(keyboard.Key.ctrl_l)
        self.kb._on_press(keyboard.KeyCode(char="\x16", vk=86))
        events = self.kb.get_recent_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["shortcut"], "ctrl+v")
        self.kb._on_release(keyboard.KeyCode.from_char("v"))
        self.kb._on_release(keyboard.Key.ctrl_l)

    def test_win_and_print_screen_key_press(self):
        """Verify Windows key and Print Screen detection."""
        from pynput import keyboard
        self.kb.reset()
        self.kb._on_press(keyboard.Key.cmd_l)
        events = self.kb.get_recent_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["shortcut"], "win")
        self.kb._on_release(keyboard.Key.cmd_l)

        self.kb.reset()
        self.kb._on_press(keyboard.Key.print_screen)
        events = self.kb.get_recent_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["shortcut"], "print_screen")
        self.kb._on_release(keyboard.Key.print_screen)

    def test_key_repeat_debouncing(self):
        """Verify held keys don't spam repeated events."""
        from pynput import keyboard
        self.kb.reset()
        self.kb._on_press(keyboard.Key.ctrl_l)
        self.kb._on_press(keyboard.KeyCode(char="\x03", vk=67))
        self.kb._on_press(keyboard.KeyCode(char="\x03", vk=67))  # Auto-repeat 1
        self.kb._on_press(keyboard.KeyCode(char="\x03", vk=67))  # Auto-repeat 2
        events = self.kb.get_recent_events()
        self.assertEqual(len(events), 1, "Key repeat produced duplicate events!")
        self.kb._on_release(keyboard.KeyCode.from_char("c"))
        self.kb._on_release(keyboard.Key.ctrl_l)

    def tearDown(self):
        self.kb.stop()


if __name__ == "__main__":
    unittest.main()
