#!/usr/bin/env python3

import os, sys
import signal
import time
import re
import atexit

import dropbox
import dbauth

def dropbox_authorise():
	"Authorise the application to use a specific user's Dropbox"
	flow = dropbox.client.DropboxOAuth2FlowNoRedirect(dbauth.DB_APP_KEY, dbauth.DB_APP_SECRET)
	authorize_url = flow.start()

	print("As this is your first run, you'll need to grant Peppe access to your Dropbox")
	print('1. Go to: ' + authorize_url)
	print('2. Click "Allow" (you might have to log in first)')
	auth_code = input("3. Enter the authorization code here: ").strip()
	
	access_token, user_id = flow.finish(auth_code)

	auth_file = open('db_auth', 'w')
	auth_file.write(access_token)
	auth_file.close()

	return access_token

def start_gphoto(interval, project_name):
	id = os.fork()

	if id == 0:
		args = ["gphoto2", "--capture-image-and-download", "-I %d" % interval]
		os.execv('/usr/bin/gphoto2', args)
	
	return id

def stop_gphoto(pid):
	print("Killing gphoto2 @ %d" % (pid, ))
	os.kill(pid, signal.SIGTERM)

if __name__ == "__main__":
	print("~ Peppe, the Raspberry Pi time-lapse photographer ~")	

	# ~ Connect to Dropbox  ~ #
	# ----------------------- #
	
	# Fetch access token from disk, or the user
	if os.path.isfile(os.path.relpath('access_token')):
		auth_file = open('access_token', 'r')
		access_token = auth_file.read().strip()
		auth_file.close()
	else:
		access_token = dropbox_authorise()

	# Try connecting
	ready = False
	while not ready:
		client = dropbox.client.DropboxClient(access_token)
		try:
			client.account_info()
			ready = True
		except dropbox.rest.ErrorResponse as e:
			print("Failed to connect to dropbox. Trying again...")


	# ~ Create a new photography project ~ #
	# ------------------------------------ #

	project_name = input("What would you like to name this photography project? ").strip()

	if os.path.exists(os.path.relpath("photos/" + project_name)):
		print("A project with that name already exists.")
		sys.exit(0)
		# TODO: Handle existing projects

	os.makedirs('photos/' + project_name)

	# Do everything from the project directory
	os.chdir('photos/' + project_name)

	# Obtain the time to wait between photos
	ready = False
	while not ready:
		interval = input("How often would you like to take photos? (seconds) ").strip()
		try:
			interval = int(interval)
			ready = True
		except ValueError as e:
			print("ERROR: Please input a whole number of seconds")


	# ~ Start taking photos ~ #
	# ----------------------- #

	gphoto_pid = start_gphoto(interval, project_name)
	atexit.register(stop_gphoto, gphoto_pid)

	# Keep track of the number of photos taken
	counter = 0
	
	# Don't take photos when it's dark...
	daytime = True

	# Sleep a quarter of an interval, then start watching for files
	time.sleep(interval//4)
	# TODO: This could be better...

	# Compile a regex to match files from gphoto
	regex = re.compile("capt") 

	while daytime:
		for file in os.listdir():
			if regex.search(file):
				os.rename(file, "img%05d.jpg" % (counter, ))
				counter += 1
				# TODO: Upload to Dropbox (need a better cycle system)

		# Run a quarter of a period out of sync with the camera
		time.sleep(interval)
