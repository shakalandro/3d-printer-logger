#!/usr/bin/python

from settings import *
import time, json, httplib, os, atexit, thread
import RPi.GPIO as io
import time
import datetime
import select
from evdev import InputDevice, list_devices, categorize, ecodes
from parse_rest.connection import register
from parse_rest.datatypes import Object, Function

# V+ is bottom row, third from the left.
# V- is top-leftmost pin.
POWER_PIN = 25

KEYCODES = {
	'KEY_0': '0', 'KEY_1': '1', 'KEY_2': '2', 'KEY_3': '3', 'KEY_4': '4', 
	'KEY_5': '5', 'KEY_6': '6', 'KEY_7': '7', 'KEY_8': '8', 'KEY_9': '9'
}

ALLOW_TIME_BUMPS = True
BUMP_INCREMENT = 60 * 60 * 1

class PrinterLog(Object):
    pass

def get_scanner_device():
    devices = map(InputDevice, list_devices())
    device = None
    for dev in devices:
        if dev.name == 'RFIDeas USB Keyboard':
            device = dev
            break
    return device

def init(device):
	io.setwarnings(False)
	io.setmode(io.BCM)
	io.setup(POWER_PIN, io.OUT)
	io.output(POWER_PIN, False)
	register(APPLICATION_ID, REST_API_KEY)

	atexit.register(cleanup, device)

	device.grab()

def cleanup(device):
	device.ungrab()
	io.output(POWER_PIN, False)

def log(badgenum, sequence_num, allowed):
        ts = time.time()
        ts_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
	newlog = PrinterLog(badge_num=badgenum, time=ts, time_str=ts_str, sequence_number=sequence_num, allowed_time=allowed)
	newlog.save()

def get_input(device):
	val = ''
        none_time_start = 0
	while True:
                event = device.read_one()
                if event is None:
                        if none_time_start == 0:
                            none_time_start = time.time()
                        if time.time() - none_time_start > 1:
                            break
                        else:
                            continue
                none_time_start = 0
		ev = categorize(event)
		if event.type == ecodes.EV_KEY and ev.keystate == ev.key_down:
			if ev.keycode == 'KEY_ENTER':
				break
			val += KEYCODES[ev.keycode]
	return val if val != '' else None 

if __name__ == "__main__":
	device = get_scanner_device()
	if str(device) == 'None':
		print "Device not found! Exiting!"

	init(device)
        started = 0
        allowed = 0
        sequence_num = 0
	while True:
                if (time.time() - started) < allowed:
                        io.output(POWER_PIN, True)
                else:
                        io.output(POWER_PIN, False)
                        allowed = 0
                        started = 0
                        sequence_num = 0
                try:    
                        badgenum = int(get_input(device))
                        if badgenum is not None:
                                if allowed == 0:
                                        io.output(POWER_PIN, True)
                                        started = time.time()
                                allowed += BUMP_INCREMENT    
                                sequence_num += 1
                                thread.start_new_thread(log, (badgenum,sequence_num,allowed))
                except Exception:
                        time.sleep(0.1)
                time.sleep(0.1)
                        

