import tkinter as tk
from dynamixel_sdk import *
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

# ---------------- DYNAMIXEL SETTINGS ----------------

# Some troubleshooting: 
# There is no status packet1: 
    # Verify you're flashed to Protocol 2.0 By using the Recovery option (Update won't upgrade from Protocol 1 to 2)
    # Using the proper motor ID (Flashing with prior step will set the ID to 1)
    # Your COM/Serial port is correct; this file is formatted for the mac system of doing thing
    # Your QTM is ok
# I'm getting out-of-range errors
    # Go into the Wizard, and below the second to the right that shows various operating modes (velocity, etc.)
    # Select "Extended Position." If that doesn't show up, verify you're on firmware version 44/2C(?


MY_DXL = 'X_SERIES'

ADDR_TORQUE_ENABLE = 64
ADDR_GOAL_POSITION = 116
ADDR_PRESENT_POSITION = 132

DXL_MINIMUM_POSITION_VALUE = 0
DXL_MAXIMUM_POSITION_VALUE = 4095

BAUDRATE = 57600
PROTOCOL_VERSION = 2.0
DXL_IDs = [1, 2]

DEVICENAME = '/dev/tty.usbserial-FT763GF8'

TORQUE_ENABLE = 1
TORQUE_DISABLE = 0

# ---------------- APP STATE ----------------

goal_position = 0

def clamp(value, lo, hi):
    return max(lo, min(hi, value))

# ---------------- TKINTER GUI ----------------

root = tk.Tk()
root.title("Dynamixel OSC Position Control")
root.geometry("450x180")

title_label = tk.Label(root, text="OSC Dynamixel Position Control", font=("Arial", 14, "bold"))
title_label.pack(pady=(12, 6))

value_label = tk.Label(root, text=f"Goal Position: {goal_position}", font=("Arial", 12))
value_label.pack(pady=4)

status_label = tk.Label(root, text="Waiting for OSC on /goal ...", font=("Arial", 10))
status_label.pack(pady=4)

present_label = tk.Label(root, text="Present Position: ---", font=("Arial", 12))
present_label.pack(pady=4)

# ---------------- OSC SERVER ----------------

def osc_goal_handler(address, *args):
    global goal_position

    if not args:
        return

    try:
        new_goal = int(float(args[0]))
        new_goal = clamp(new_goal, DXL_MINIMUM_POSITION_VALUE, DXL_MAXIMUM_POSITION_VALUE)
        goal_position = new_goal

        # Tkinter UI updates must be scheduled on the Tk thread
        root.after(0, lambda: value_label.config(text=f"Goal Position: {goal_position}"))
        root.after(0, lambda: status_label.config(
            text=f"Last OSC: {address} {goal_position}"
        ))

    except (ValueError, TypeError):
        root.after(0, lambda: status_label.config(
            text=f"Invalid OSC payload on {address}"
        ))

dispatcher = Dispatcher()
dispatcher.map("/goal", osc_goal_handler)

OSC_IP = "localhost" #"35.3.79.98"
OSC_PORT = 6000

osc_server = ThreadingOSCUDPServer((OSC_IP, OSC_PORT), dispatcher)

# ---------------- DYNAMIXEL SETUP ----------------

portHandler = PortHandler(DEVICENAME)
packetHandler = PacketHandler(PROTOCOL_VERSION)

if not portHandler.openPort():
    print("Failed to open port")
    raise SystemExit

if not portHandler.setBaudRate(BAUDRATE):
    print("Failed to set baudrate")
    portHandler.closePort()
    raise SystemExit

dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(
    portHandler, DXL_ID, ADDR_TORQUE_ENABLE, TORQUE_ENABLE
)

if dxl_comm_result != COMM_SUCCESS:
    print(packetHandler.getTxRxResult(dxl_comm_result))
    portHandler.closePort()
    raise SystemExit

if dxl_error != 0:
    print(packetHandler.getRxPacketError(dxl_error))
    portHandler.closePort()
    raise SystemExit

print("Dynamixel connected")
print(f"OSC server listening on {OSC_IP}:{OSC_PORT}")
print("Send OSC messages to /goal with one numeric argument")

status_label.config(text=f"Listening for OSC on {OSC_IP}:{OSC_PORT} at /goal")

# ---------------- MOTOR UPDATE LOOP ----------------

def update_motor():
    goal = goal_position

    dxl_comm_result, dxl_error = packetHandler.write4ByteTxRx(
        portHandler, DXL_ID, ADDR_GOAL_POSITION, goal
    )

    if dxl_comm_result != COMM_SUCCESS:
        print(packetHandler.getTxRxResult(dxl_comm_result))
    elif dxl_error != 0:
        print(packetHandler.getRxPacketError(dxl_error))

    dxl_present_position, dxl_comm_result, dxl_error = packetHandler.read4ByteTxRx(
        portHandler, DXL_ID, ADDR_PRESENT_POSITION
    )

    if dxl_comm_result != COMM_SUCCESS:
        print(packetHandler.getTxRxResult(dxl_comm_result))
        present_label.config(text="Present Position: read error")
    elif dxl_error != 0:
        print(packetHandler.getRxPacketError(dxl_error))
        present_label.config(text="Present Position: packet error")
    else:
        present_label.config(text=f"Present Position: {dxl_present_position}")
        print(f"[ID:{DXL_ID:03d}] Goal:{goal:04d}  Present:{dxl_present_position:04d}")

    root.after(1, update_motor)

# ---------------- CLEAN EXIT ----------------

def on_close():
    try:
        osc_server.shutdown()
        osc_server.server_close()
    except Exception:
        pass

    try:
        packetHandler.write1ByteTxRx(
            portHandler, DXL_ID, ADDR_TORQUE_ENABLE, TORQUE_DISABLE
        )
    except Exception:
        pass

    try:
        portHandler.closePort()
    except Exception:
        pass

    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

# Start OSC server in its own thread
osc_server.serve_forever_thread = __import__("threading").Thread( # type: ignore
    target=osc_server.serve_forever,
    daemon=True
)
osc_server.serve_forever_thread.start() # type: ignore

# Start periodic motor update
root.after(1, update_motor)

root.mainloop()