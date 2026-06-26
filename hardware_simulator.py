"""
hardware_simulator.py — hardware simulation layer for testing.

Patches app.py hardware objects (IRSensor, RGBLED, Buzzer, CoinButton)
with controllable simulators. Does NOT modify original hardware/* code.

Usage:
    from hardware_simulator import HardwareSimulator
    sim = HardwareSimulator()
    sim.press_coin()          # simulate coin button press
    sim.press_coin(times=3)   # press 3 times
    sim.simulate_pickup()     # simulate IR detection (customer took mask)
    sim.simulate_timeout()    # simulate IR timeout (30s no pickup)
    sim.reset()               # reset all spy state
    print(sim.led_history)    # check RGB LED calls
    print(sim.buzzer_history) # check buzzer calls
"""

import time
import sys
import os

# Ensure project root in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class SpyRGBLED:
    """Records all LED operations for verification."""

    def __init__(self):
        self.history = []
        self._current_color = (False, False, False)

    def set_color(self, r, g, b):
        self._current_color = (bool(r), bool(g), bool(b))
        self.history.append(("set_color", r, g, b))

    def set_channel(self, channel):
        colors = {0: (1, 0, 0), 1: (0, 1, 0), 2: (0, 0, 1)}
        r, g, b = colors.get(channel, (0, 0, 0))
        self._current_color = (bool(r), bool(g), bool(b))
        self.history.append(("set_channel", channel))

    def off(self):
        self._current_color = (False, False, False)
        self.history.append(("off",))

    @property
    def is_on(self):
        return any(self._current_color)

    @property
    def current_channel(self):
        """Infer channel from color."""
        r, g, b = self._current_color
        if r and not g and not b:
            return 0
        if not r and g and not b:
            return 1
        if not r and not g and b:
            return 2
        return None


class SpyBuzzer:
    """Records all buzzer operations for verification."""

    def __init__(self):
        self.history = []

    def beep(self, freq=1000, duration=0.2):
        self.history.append(("beep", freq, duration))

    def off(self):
        self.history.append(("off",))


class SimulatedIRSensor:
    """Controllable IR sensor — can be set to blocked or clear."""

    def __init__(self):
        self._blocked = False

    def is_blocked(self):
        return self._blocked

    def set_blocked(self, blocked=True):
        self._blocked = blocked

    def set_clear(self):
        self._blocked = False


class HardwareSimulator:
    """
    Patches app.py hardware objects with controllable simulators.
    Use as a context manager or manually call patch() / unpatch().
    """

    def __init__(self):
        self.spy_led = SpyRGBLED()
        self.spy_buzzer = SpyBuzzer()
        self.sim_ir = SimulatedIRSensor()
        self._originals = {}
        self._app = None

    def patch(self):
        """Replace app.py hardware objects with simulators."""
        import app as app_module
        self._app = app_module

        # Save originals
        self._originals["rgb"] = app_module.rgb
        self._originals["buzzer"] = app_module.buzzer
        self._originals["ir"] = app_module.ir

        # Replace
        app_module.rgb = self.spy_led
        app_module.buzzer = self.spy_buzzer
        app_module.ir = self.sim_ir

        return self

    def unpatch(self):
        """Restore original hardware objects."""
        if not self._app:
            return
        for name, obj in self._originals.items():
            setattr(self._app, name, obj)
        self._app = None

    def __enter__(self):
        return self.patch()

    def __exit__(self, *args):
        self.unpatch()

    # ---- Coin Button ----
    def press_coin(self, times=1):
        """Simulate coin button press by directly calling state machine."""
        for _ in range(times):
            self._app.sm.add_coin()

    # ---- IR Sensor ----
    def simulate_pickup(self):
        """Simulate customer picking up mask (IR blocked)."""
        self.sim_ir.set_blocked(True)

    def simulate_no_pickup(self):
        """Simulate customer NOT picking up (IR clear)."""
        self.sim_ir.set_blocked(False)

    def simulate_timeout(self):
        """Wait for IR timeout thread to call sm.cancel().

        The wait_for_pickup thread polls every IR_DETECT_INTERVAL seconds
        for IR_RETRY_COUNT iterations. With default config: 0.5s * 60 = 30s.

        For testing, this blocks for the full timeout. Use simulate_pickup()
        after dispense for normal flow testing instead.
        """
        if self._app:
            from config import IR_DETECT_INTERVAL, IR_RETRY_COUNT
            wait_time = IR_DETECT_INTERVAL * IR_RETRY_COUNT + 0.5
            time.sleep(wait_time)

    # ---- State Helpers ----
    @property
    def state(self):
        if not self._app:
            return None
        return self._app.sm.state

    @property
    def state_name(self):
        if not self._app:
            return None
        return self._app.sm.get_state()["state_name"]

    @property
    def balance(self):
        if not self._app:
            return None
        return self._app.sm.balance

    @property
    def selected_channel(self):
        if not self._app:
            return None
        return self._app.sm.selected_channel

    @property
    def led_history(self):
        return list(self.spy_led.history)

    @property
    def buzzer_history(self):
        return list(self.spy_buzzer.history)

    def reset(self):
        """Reset simulator state and app state."""
        self.spy_led = SpyRGBLED()
        self.spy_buzzer = SpyBuzzer()
        self.sim_ir = SimulatedIRSensor()
        if self._app:
            self._app.rgb = self.spy_led
            self._app.buzzer = self.spy_buzzer
            self._app.ir = self.sim_ir
            # Reset state machine
            self._app.sm.state = 0
            self._app.sm.balance = 0
            self._app.sm.selected_channel = None
            # Reset inventory data directly (not via HTTP API)
            from config import CHANNEL_CONFIG
            self._app.inv.channels = []
            for ch in CHANNEL_CONFIG:
                self._app.inv.channels.append({
                    "id": ch["id"],
                    "name": ch["name"],
                    "price": ch["price"],
                    "stock": ch["init_stock"]
                })
            self._app.inv.transactions = []
            self._app.inv.save()
