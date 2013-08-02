#!/usr/bin/env python3

import os, sys
import subprocess
import time
import re
import atexit

from daylight import sunrise, sunset

# Perform one-off compilation of the regex to match files from gphoto
GP_REGEX = re.compile("capt")

def dropbox_authorise():
	"""Authorise the application to use a specific user's Dropbox"""
	flow = dropbox.client.DropboxOAuth2FlowNoRedirect(dbauth.DB_APP_KEY,
							  dbauth.DB_APP_SECRET)
	authorize_url = flow.start()

	print('1. Go to: ' + authorize_url)
	print('2. Click "Allow" (you might have to log in first)')
	auth_code = input("3. Enter the authorization code here: ").strip()
	
	access_token, user_id = flow.finish(auth_code)

	with open('access_token', 'w') as auth_file:
		auth_file.write(access_token)

	return access_token

def dropbox_connect():
	"""Connect to Dropbox if desired, and return the client object.

	Return None if the user doesn't want Dropbox.
	"""

	question = "Would you like to upload photos to dropbox [y/N]? "
	use_dropbox = input(question).strip().lower()

	if use_dropbox in ["n", "no", ""]:
		return None

	import dropbox
	import dbauth

	# Fetch access token from disk, or the user
	if os.path.isfile(os.path.relpath('access_token')):
		with open('access_token', 'r') as auth_file:
			access_token = auth_file.read().strip()
	else:
		access_token = dropbox_authorise()

	# Try to connect
	ready = False
	while not ready:
		client = dropbox.client.DropboxClient(access_token)
		try:
			client.account_info()
			ready = True
		except dropbox.rest.ErrorResponse as e:
			print("Failed to connect to Dropbox. Trying again...")
	
	return client

def dropbox_upload(file_name, project_name, db_client):
	"""Upload a named file from the current path to Dropbox."""
	
	print("Uploading " + file_name, end="")
	dbpath = "/Photos/%s/%s" % (project_name, file_name)
	with open(file_name, 'rb') as f:
		db_client.put_file(dbpath, f)
	print(" [done]")
	# TODO: Error handling??

def current_time():
	"""Return the current time and month as a duple.

	24 hour time represented as 3 or 4 digits, eg. 2005 for 8:05pm
	The abbreviated month name, eg. 'jun' for June
	"""
	now = time.localtime() # Make sure your clock is right
	the_time = (now.tm_hour*100) + now.tm_min
	this_month = time.strftime("%b", now).lower()
	return (the_time, this_month)

def create_project():
	"""Create a new photography project and return its name and path."""
	
	question = "What would you like to name this photography project? "
	project_name = input(question).strip()

	# TODO: Implement this, handle existing projects
	question = "Where would you like to store the photos? (full path) "

	# Default
	project_path = "photos/" + project_name

	if os.path.exists(os.path.relpath(project_path)):
		print("A project with that name already exists.")
		sys.exit(0)
	else:
		os.makedirs(project_path)
	
	return (project_name, project_path)

def poll_night_mode():
	question = "Would you like to take photos all through the night [y/N]? "
	answer = input(question).strip().lower()

	if answer in ["y", "ye", "yes"]:
		return True
	else:
		return False

def get_interval():
	"""Fetch and return the time interval to wait between taking photos."""
	
	question = "How often would you like to take photos (seconds)?"

	while True:
		interval = input(question).strip()
		try:
			interval = int(interval)
			return interval
		except ValueError as e:
			print("ERROR: Please input a whole number of seconds.")

def take_photos(interval, project_name, counter, db_client, night_mode):
	"""Manage the taking of photos using gphoto.

	Keep gphoto running, monitor for new photos and sleep in between.
	Return the updated photo counter.
	"""

	# Local time variables
	the_time, this_month = current_time()

	# Commandline arguments to gphoto
	gp_args = ["gphoto2", "--capture-image-and-download", 
		   "-I", str(interval)]

	# Keep track of when gphoto is running
	running = False
	gp_start_t = 0
	gp_runs = 0 # the number of photos taken by this gphoto process

	while (the_time >= sunrise[this_month] and
	       the_time <= sunset[this_month]) or night_mode:

		# Start gphoto if it isn't running
		if not running:
			print("Started a fresh gphoto.")
			gphoto = subprocess.Popen(gp_args,
						  stdin=subprocess.DEVNULL,
						  stdout=subprocess.DEVNULL)
			running = True
			gp_start_t = int(time.time())
			gp_runs = 0
			atexit.register(gphoto.terminate)
		
		# Check for new photos
		for file in sorted(os.listdir()):
			if GP_REGEX.search(file):
				# Rename the files (for flexibility)
				r_file = "img%05d.jpg" % (counter, )
				os.rename(file, r_file)
				counter += 1

				# Upload to Dropbox if desired
				if db_client:
					dropbox_upload(r_file, project_name,
							       db_client)
		
		# Check that gphoto hasn't died
		if gphoto.poll():
			atexit.unregister(gphoto.terminate)
			running = False

		# Wait for gphoto's next photo period
		while int(time.time()) < (gp_start_t + gp_runs*interval):
			time.sleep(interval//4)

		# Update time
		the_time, this_month = current_time()
	
	# Quit gphoto at night
	if running:
		atexit.unregister(gphoto.terminate)
		gphoto.terminate()

	return counter

def main():
	print("~ Peppe, the Raspberry Pi time-lapse photographer ~")	

	project_name, project_path = create_project()

	interval = get_interval()

	night_mode = poll_night_mode()
	
	db_client = dropbox_connect()	

	# Perform the actual photo-taking in the project directory
	os.chdir(project_path)

	# Keep track of the number of photos taken
	counter = 0

	# Run forever, but only take photos during the day
	while True:
		the_time, this_month = current_time()

		if (the_time >= sunrise[this_month] and 
		    the_time <= sunset[this_month]) or night_mode:
			
			counter = take_photos(interval, project_name,
					counter, db_client, night_mode)

		# Wait out the night
		print(".", end="")
		time.sleep(interval//2)

if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt as e:
		print("\nGoodbye!")
