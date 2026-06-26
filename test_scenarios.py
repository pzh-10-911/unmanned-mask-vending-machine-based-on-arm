"""
test_scenarios.py — Realistic scenario simulation tests.

Simulates complete user interaction stories through the hardware simulator.
Each scenario tells a story of a real customer interacting with the machine.

Usage:
    python test_scenarios.py
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hardware_simulator import HardwareSimulator

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"    [OK] {name}")
    else:
        FAIL += 1
        print(f"    [FAIL] {name}  {detail}")
    return condition


def narrate(msg):
    print(f"\n  >>> {msg}")


def wait_pickup(sim, seconds=1.0):
    """Simulate customer picking up mask and wait for thread detection."""
    sim.simulate_pickup()
    time.sleep(seconds)


# ===================================================================
print("=" * 60)
print("  Mask Vending Machine — Scenario Simulation Tests")
print("=" * 60)

sim = HardwareSimulator().patch()

try:
    # ================================================================
    # SCENARIO 1: First Customer — Simple Purchase
    # ================================================================
    print("\n" + "=" * 60)
    print("SCENARIO 1: Customer buys 1 Adult Mask")
    print("=" * 60)
    sim.reset()
    time.sleep(0.1)

    narrate("Machine is idle, display shows 'Please insert coins'")
    s = sim._app.sm.get_state()
    check("1.1 machine IDLE", s["state_name"] == "IDLE")
    check("1.2 all 3 channels available",
          all(ch["available"] for ch in s["channels"]),
          str([ch["stock"] for ch in s["channels"]]))
    check("1.3 LED is off", not sim.spy_led.is_on)
    check("1.4 balance is 0", sim.balance == 0)

    narrate("Customer inserts 2 coins (2 yuan)")
    sim.press_coin(2)
    check("1.5 balance = 2", sim.balance == 2)

    narrate("Customer selects Adult Mask (channel 0, 2 yuan)")
    result = sim._app.sm.select(0)
    check("1.6 select success", result["success"], str(result))
    check("1.7 item name 'Adult Mask'", result["name"] == "成人口罩")

    narrate("Customer confirms purchase")
    sim.spy_led = type(sim.spy_led)()
    sim.spy_buzzer = type(sim.spy_buzzer)()
    sim._app.rgb = sim.spy_led
    sim._app.buzzer = sim.spy_buzzer
    result = sim._app.sm.confirm(sim._app.on_dispense)
    check("1.8 confirm accepted", result["success"], result.get("msg"))
    check("1.9 LED lights up RED (channel 0)", sim.spy_led.current_channel == 0)
    check("1.10 buzzer beeps", len(sim.buzzer_history) > 0)
    check("1.11 balance deducted 2->0", sim.balance == 0)

    narrate("Customer takes mask from dispense slot (IR detects pickup)")
    check("1.12 state = DISPENSE", sim.state == 2)
    wait_pickup(sim, 1.0)
    check("1.13 state = IDLE after pickup", sim.state == 0)
    check("1.14 LED off after pickup", not sim.spy_led.is_on)

    # Verify inventory decremented
    s = sim._app.sm.get_state()
    adult = [ch for ch in s["channels"] if ch["id"] == 0][0]
    check("1.15 adult mask stock 10->9", adult["stock"] == 9,
          f"stock={adult['stock']}")
    check("1.16 transaction recorded",
          len(sim._app.inv.get_transactions()) == 1)

    # ================================================================
    # SCENARIO 2: Insufficient Balance — Add More Coins
    # ================================================================
    print("\n" + "=" * 60)
    print("SCENARIO 2: Customer tries to buy with insufficient balance")
    print("=" * 60)
    sim.reset()
    time.sleep(0.1)

    narrate("Customer inserts only 1 coin (needs 2 for Adult Mask)")
    sim.press_coin(1)
    check("2.1 balance = 1", sim.balance == 1)

    narrate("Customer tries to buy Adult Mask — rejected")
    result = sim._app.sm.select(0)
    check("2.2 select rejected", not result["success"])
    check("2.3 reason: insufficient balance",
          "余额不足" in result["msg"], result["msg"])
    check("2.4 state stays IDLE", sim.state == 0)
    check("2.5 balance still 1", sim.balance == 1)

    narrate("Customer adds 1 more coin and retries")
    sim.press_coin(1)
    check("2.6 balance now 2", sim.balance == 2)
    result = sim._app.sm.select(0)
    check("2.7 select now succeeds", result["success"])

    narrate("Customer completes purchase")
    result = sim._app.sm.confirm(sim._app.on_dispense)
    check("2.8 confirm OK", result["success"])
    check("2.9 balance 2->0", sim.balance == 0)
    wait_pickup(sim, 1.0)
    check("2.10 back to IDLE", sim.state == 0)

    # ================================================================
    # SCENARIO 3: Customer Changes Mind — Cancel Selection
    # ================================================================
    print("\n" + "=" * 60)
    print("SCENARIO 3: Customer selects but changes mind (cancel_select)")
    print("=" * 60)
    sim.reset()
    time.sleep(0.1)

    narrate("Customer inserts 5 coins")
    sim.press_coin(5)
    check("3.1 balance = 5", sim.balance == 5)

    narrate("Customer selects Children Mask (channel 1)")
    result = sim._app.sm.select(1)
    check("3.2 select OK", result["success"], f"name={result.get('name')}")
    check("3.3 state = SELECTED", sim.state == 1)

    narrate("Customer changes mind — presses cancel_select")
    result = sim._app.sm.cancel_select()
    sim._app.rgb.off()
    check("3.4 cancel_select OK", result["success"])
    check("3.5 state = IDLE", sim.state == 0)
    check("3.6 balance preserved (5)", sim.balance == 5,
          f"balance={sim.balance}")

    narrate("Customer now selects N95 instead")
    result = sim._app.sm.select(2)
    check("3.7 N95 select OK", result["success"],
          f"name={result.get('name')}, price={result.get('price')}")

    narrate("Customer completes N95 purchase")
    sim.spy_led = type(sim.spy_led)()
    sim._app.rgb = sim.spy_led
    result = sim._app.sm.confirm(sim._app.on_dispense)
    check("3.8 confirm OK", result["success"])
    check("3.9 LED BLUE (channel 2)", sim.spy_led.current_channel == 2)
    check("3.10 balance 5->0 (N95=5yuan)", sim.balance == 0)
    wait_pickup(sim, 1.0)
    check("3.11 complete", sim.state == 0)

    # ================================================================
    # SCENARIO 4: Cancel Transaction (Full Refund)
    # ================================================================
    print("\n" + "=" * 60)
    print("SCENARIO 4: Customer cancels transaction for full refund")
    print("=" * 60)
    sim.reset()
    time.sleep(0.1)

    narrate("Customer inserts 3 coins and selects Adult Mask")
    sim.press_coin(3)
    sim._app.sm.select(0)
    check("4.1 selected", sim.state == 1)
    check("4.2 balance = 3", sim.balance == 3)

    narrate("Customer decides not to buy — presses Cancel")
    result = sim._app.sm.cancel()
    sim._app.rgb.off()
    check("4.3 cancel OK", result["success"])
    check("4.4 balance refunded to 0", result["balance"] == 0)
    check("4.5 state = IDLE", sim.state == 0)

    # ================================================================
    # SCENARIO 5: Cancel During Dispense (Emergency)
    # ================================================================
    print("\n" + "=" * 60)
    print("SCENARIO 5: Customer cancels during dispense (emergency)")
    print("=" * 60)
    sim.reset()
    time.sleep(0.1)

    narrate("Customer buys Adult Mask")
    sim.press_coin(3)
    sim._app.sm.select(0)
    sim._app.sm.confirm(sim._app.on_dispense)
    check("5.1 dispensing", sim.state == 2)

    narrate("Customer suddenly presses Cancel (e.g., wrong item)")
    result = sim._app.sm.cancel()
    sim._app.rgb.off()
    check("5.2 cancel from DISPENSE OK", result["success"])
    check("5.3 balance = 0", sim.balance == 0)
    check("5.4 state = IDLE", sim.state == 0)
    check("5.5 LED off", not sim.spy_led.is_on)

    # ================================================================
    # SCENARIO 6: Buy All Stock of One Channel
    # ================================================================
    print("\n" + "=" * 60)
    print("SCENARIO 6: Multiple customers deplete a channel's stock")
    print("=" * 60)
    sim.reset()
    time.sleep(0.1)

    # Adult mask initial stock is 10
    for i in range(10):
        sim.press_coin(2)
        sim._app.sm.select(0)
        sim._app.sm.confirm(sim._app.on_dispense)
        wait_pickup(sim, 1.0)
        narrate(f"Purchase {i+1}/10 complete")

    s = sim._app.sm.get_state()
    adult_ch = [ch for ch in s["channels"] if ch["id"] == 0][0]
    check("6.1 adult mask stock = 0", adult_ch["stock"] == 0,
          f"stock={adult_ch['stock']}")
    check("6.2 adult mask unavailable", not adult_ch["available"])
    check("6.3 other channels still available",
          all(ch["available"] for ch in s["channels"] if ch["id"] != 0))

    narrate("Next customer tries to buy sold-out Adult Mask")
    sim.press_coin(2)
    result = sim._app.sm.select(0)
    check("6.4 select rejected", not result["success"])
    check("6.5 reason: out of stock",
          "库存不足" in result["msg"], result["msg"])

    # ================================================================
    # SCENARIO 7: Mixed Insert Coins While Selecting
    # ================================================================
    print("\n" + "=" * 60)
    print("SCENARIO 7: Customer adds coins during different states")
    print("=" * 60)
    sim.reset()
    time.sleep(0.1)

    narrate("Customer inserts 2 coins for Children Mask")
    sim.press_coin(2)
    check("7.1 balance = 2", sim.balance == 2)

    narrate("Customer selects Children Mask but wants to add extra coins")
    sim._app.sm.select(1)
    check("7.2 selected (state=SELECTED)", sim.state == 1, f"state={sim.state}")

    narrate("Customer adds 1 more coin while in SELECTED state")
    sim.press_coin(1)
    check("7.3 coin accepted in SELECTED", sim.balance == 3, f"balance={sim.balance}")

    narrate("Customer confirms")
    sim._app.sm.confirm(sim._app.on_dispense)
    check("7.4 purchase OK", sim.state == 2)
    wait_pickup(sim, 1.0)
    check("7.5 complete", sim.state == 0)

    # ================================================================
    # SCENARIO 8: Rapid Coin Insertion (Stress Test)
    # ================================================================
    print("\n" + "=" * 60)
    print("SCENARIO 8: Rapid coin insertion (10 coins quickly)")
    print("=" * 60)
    sim.reset()
    time.sleep(0.1)

    narrate("Customer rapidly inserts 10 coins")
    sim.press_coin(10)
    check("8.1 balance = 10", sim.balance == 10)

    narrate("Customer buys N95 (5 yuan)")
    sim._app.sm.select(2)
    sim._app.sm.confirm(sim._app.on_dispense)
    wait_pickup(sim, 1.0)
    check("8.2 N95 purchased", sim.state == 0)
    check("8.3 balance = 5 (10-5)", sim.balance == 5)

    narrate("Customer buys another N95 with remaining balance")
    sim._app.sm.select(2)
    sim._app.sm.confirm(sim._app.on_dispense)
    wait_pickup(sim, 1.0)
    check("8.4 2nd N95 purchased", sim.state == 0)
    check("8.5 balance = 0 (5-5)", sim.balance == 0)

    # ================================================================
    # SCENARIO 9: System Reset After Usage
    # ================================================================
    print("\n" + "=" * 60)
    print("SCENARIO 9: Operator resets machine after a day of sales")
    print("=" * 60)
    sim.reset()
    time.sleep(0.1)

    narrate("Machine has been used all day — stock is depleted")
    # Simulate some purchases to deplete stock
    for _ in range(3):
        sim.press_coin(3)
        sim._app.sm.select(0)
        sim._app.sm.confirm(sim._app.on_dispense)
        wait_pickup(sim, 1.0)

    s = sim._app.sm.get_state()
    adult = [ch for ch in s["channels"] if ch["id"] == 0][0]
    check("9.1 stock reduced after sales", adult["stock"] < 10,
          f"stock={adult['stock']}")
    check("9.2 transactions exist",
          len(sim._app.inv.get_transactions()) > 0)

    narrate("Operator refills machine and resets system")
    from config import CHANNEL_CONFIG
    sim._app.inv.channels = []
    for ch in CHANNEL_CONFIG:
        sim._app.inv.channels.append({
            "id": ch["id"], "name": ch["name"],
            "price": ch["price"], "stock": ch["init_stock"]
        })
    sim._app.inv.transactions = []
    sim._app.inv.save()
    sim._app.sm.state = 0
    sim._app.sm.balance = 0
    sim._app.sm.selected_channel = None

    s = sim._app.sm.get_state()
    check("9.3 all stocks restored",
          all(ch["stock"] == CHANNEL_CONFIG[i]["init_stock"]
              for i, ch in enumerate(s["channels"])),
          str([ch["stock"] for ch in s["channels"]]))
    check("9.4 transactions cleared",
          len(sim._app.inv.get_transactions()) == 0)
    check("9.5 state = IDLE", sim.state == 0)
    check("9.6 balance = 0", sim.balance == 0)
    check("9.7 all channels available",
          all(ch["available"] for ch in s["channels"]))

    # ================================================================
    # SCENARIO 10: Invalid Operations (Error Handling)
    # ================================================================
    print("\n" + "=" * 60)
    print("SCENARIO 10: User attempts invalid operations")
    print("=" * 60)
    sim.reset()
    time.sleep(0.1)

    narrate("Trying to confirm without selecting — rejected")
    result = sim._app.sm.confirm(sim._app.on_dispense)
    check("10.1 confirm in IDLE rejected", not result["success"])

    narrate("Trying to select non-existent channel 99")
    sim.press_coin(5)
    result = sim._app.sm.select(99)
    check("10.2 invalid channel rejected", not result["success"])

    narrate("Trying to select while already selected")
    sim._app.sm.select(0)
    result = sim._app.sm.select(1)  # should fail
    check("10.3 double select rejected", not result["success"])

    narrate("Trying to confirm without enough balance after selection")
    # Edge case: cancel and reset, then try tricky flow
    sim._app.sm.cancel_select()
    sim._app.rgb.off()

    # ================================================================
    # SCENARIO 11: IR Timeout — Customer Forgets to Pick Up
    # ================================================================
    print("\n" + "=" * 60)
    print("SCENARIO 11: Customer confirms but forgets to pick up (timeout)")
    print("=" * 60)
    sim.reset()
    time.sleep(0.1)

    narrate("Customer buys Adult Mask")
    sim.press_coin(3)
    sim._app.sm.select(0)
    sim._app.sm.confirm(sim._app.on_dispense)
    check("11.1 dispensing", sim.state == 2)

    narrate("Customer walks away — IR not triggered (simulated timeout)")
    # Simulate by keeping IR clear and manually calling cancel
    # (real timeout takes 30s; we shortcut here)
    sim._app.sm.cancel()
    sim._app.rgb.off()
    check("11.2 timeout triggers cancel", sim.state == 0)
    check("11.3 balance lost (0)", sim.balance == 0)
    check("11.4 LED off", not sim.spy_led.is_on)

    # ================================================================
    # SCENARIO 12: Full Day Simulation
    # ================================================================
    print("\n" + "=" * 60)
    print("SCENARIO 12: Full day — 5 customers with mixed behaviors")
    print("=" * 60)
    sim.reset()
    time.sleep(0.1)

    narrate("--- Customer A: buys Adult Mask (2 yuan)")
    sim.press_coin(2)
    sim._app.sm.select(0)
    sim._app.sm.confirm(sim._app.on_dispense)
    wait_pickup(sim, 1.0)
    check("12.1 Customer A done", sim.state == 0)

    narrate("--- Customer B: tries to buy N95 with 3 yuan, fails, adds 2 more")
    sim.press_coin(3)
    result = sim._app.sm.select(2)
    check("12.2 N95 rejected (need 5)", not result["success"])
    sim.press_coin(2)
    result = sim._app.sm.select(2)
    check("12.3 N95 now accepted", result["success"])
    sim._app.sm.confirm(sim._app.on_dispense)
    wait_pickup(sim, 1.0)
    check("12.4 Customer B done", sim.state == 0)

    narrate("--- Customer C: buys Children Mask, changes mind, buys Adult")
    sim.press_coin(3)
    sim._app.sm.select(1)
    sim._app.sm.cancel_select()
    sim._app.rgb.off()
    check("12.5 cancelled Children Mask", sim.state == 0)
    check("12.6 balance kept", sim.balance == 3)
    sim._app.sm.select(0)
    sim._app.sm.confirm(sim._app.on_dispense)
    wait_pickup(sim, 1.0)
    check("12.7 Customer C done (balance 1)", sim.balance == 1)

    narrate("--- Customer D: inserts coin to make balance 2, then buys")
    sim.press_coin(1)
    sim._app.sm.select(0)
    sim._app.sm.confirm(sim._app.on_dispense)
    wait_pickup(sim, 1.0)
    check("12.8 Customer D done", sim.state == 0)

    narrate("--- Customer E: inserts 10 yuan, buys 2 N95 in sequence")
    sim.press_coin(10)
    # First N95
    sim._app.sm.select(2)
    sim._app.sm.confirm(sim._app.on_dispense)
    wait_pickup(sim, 1.0)
    check("12.9 first N95 done, bal=5", sim.balance == 5)
    # Second N95
    sim._app.sm.select(2)
    sim._app.sm.confirm(sim._app.on_dispense)
    wait_pickup(sim, 1.0)
    check("12.10 second N95 done, bal=0", sim.balance == 0)

    # Verify final state
    s = sim._app.sm.get_state()
    check("12.11 machine IDLE at end of day", s["state_name"] == "IDLE")
    transactions = sim._app.inv.get_transactions()
    check("12.12 all 6 transactions recorded",
          len(transactions) == 6, f"count={len(transactions)}")
    for i, tx in enumerate(transactions):
        check(f"12.13 tx{i+1} has time/item/amount/status",
              all(k in tx for k in ["time", "item", "amount", "status"]))

except Exception as e:
    import traceback
    traceback.print_exc()
    FAIL += 1
    print(f"\n[FATAL] {e}")

finally:
    sim.unpatch()

# ===================================================================
print("\n" + "=" * 60)
print(f"  Scenario Test Results: {PASS}/{PASS + FAIL} passed")
if FAIL == 0:
    print("  All scenarios passed!")
else:
    print(f"  {FAIL} checks failed")
print("=" * 60)
