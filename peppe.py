#!/usr/bin/env python3

import os, sys
import subprocess
import signal
import time
import re
import atexit

import dropbox
import dbauth
from daylight import sunrise, sunset

def dropbox_authorise():
	"Authorise the application to use a specific user's Dropbox"
	flow = dropbox.client.DropboxOAuth2FlowNoRedirect(dbauth.DB_APP_KEY, dbauth.DB_APP_SECRET)
	authorize_url = flow.start()

	print("As this is your first run, you'll need to grant Peppe access to your Dropbox")
	print('1. Go to: ' + authorize_url)
	print('2. Click "Allow" (you might have to log in first)')
	auth_code = input("3. Enter the authorization code here: ").strip()
	
	access_token, user_id = flow.finish(auth_code)

	with open('access_token', 'w') as auth_file:
		auth_file.write(access_token)

	return access_token

def current_time():
	"24 hour time represented as 4 digits, eg. 0800 for 8am"
	now = time.localtime() # Make sure your clock is right
	the_time = (now.tm_hour*100) + now.tm_min
	this_month = time.strftime("%b", now).lower()
	return (the_time, this_month)

if __name__ == "__main__":
	print("~ Peppe, the Raspberry Pi time-lapse photographer ~")	

	# ~ Connect to Dropbox  ~ #
	# ----------------------- #
	
	# Fetch access token from disk, or the user
	if os.path.isfile(os.path.relpath('access_token')):
		with open('access_token', 'r') as auth_file:
			access_token = auth_file.read().strip()
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

	# Keep track of the number of photos taken
	counter = 0

	# Keep track of whether gphoto is running
	running = False

	# Compile a regex to match files from gphoto
	regex = re.compile("capt") 

	# Commandline arguments to gphoto
	args = ["gphoto2", "--capture-image-and-download", "-I", str(interval)]

	# Run forever, but only take photos during the day
	while True:
		the_time, this_month = current_time()

		while (the_time >= sunrise[this_month]) and (the_time <= sunset[this_month]):
			
			# Start gphoto if it isn't running
			if not running:
				print("Started a fresh gphoto.")
				gphoto = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
				running = True
				atexit.register(gphoto.terminate)

				# Wait a quarter of a cycle
				time.sleep(interval//4)
		
			# Check for new photos
			for file in sorted(os.listdir()):
				if regex.search(file):
					# Rename
					new_name = "img%05d.jpg" % (counter, )
					os.rename(file, new_name)
					counter += 1

					# Upload to Dropbox
					print("Uploading " + new_name, end="")
					dbpath = '/Photos/' + project_name + "/" + new_name
					with open(new_name, 'rb') as f:
						response = client.put_file(dbpath, f)

					print(" [done]")
			# Check gphoto status
			if gphoto.poll():
				running = False

			# Wait for new photos
			time.sleep(interval)

			# Update time
			the_time, this_month = current_time()

		# Quit gphoto at night
		if running:
			gphoto.terminate()
			running = False

		# Wait out the night
		print("Sleeping, night")
		time.sleep(interval)
