#!/usr/bin/env python3

import os
import signal
import time

def start_gphoto():
	id = os.fork()
	args = ["gphoto2", "--capture-image-and-download", "-I 5"]
	if id == 0:
		os.execv('/usr/bin/gphoto2', args)
	
	return id

def stop_gphoto(pid):
	print("Killing gphoto2 @ %d" % (pid, ))
	os.kill(pid, signal.SIGTERM)

if __name__ == "__main__":
	gphoto_pid = start_gphoto()
	time.sleep(60)
	stop_gphoto(gphoto_pid)
