#!/usr/bin/env python3

import os, sys
import subprocess
import signal
import time
import re
import atexit

from daylight import sunrise, sunset

# Perform one-off compilation of the regex to match files from gphoto
GP_REGEX = re.compile("capt")


def dropbox_authorise():
	"Authorise the application to use a specific user's Dropbox"
	flow = dropbox.client.DropboxOAuth2FlowNoRedirect(dbauth.DB_APP_KEY,
							  dbauth.DB_APP_SECRET)
	authorize_url = flow.start()

	print("Complete this section to allow Peppe to upload to Dropbox")
	print('1. Go to: ' + authorize_url)
	print('2. Click "Allow" (you might have to log in first)')
	auth_code = input("3. Enter the authorization code here: ").strip()
	
	access_token, user_id = flow.finish(auth_code)

	with open('access_token', 'w') as auth_file:
		auth_file.write(access_token)

	return access_token

def dropbox_connect():
	"Connect to dropbox. (Returns a dropbox client object)"
	
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
	
	return client

def dropbox_upload(file_name, project_name, db_client):
	"Upload a named file from the current path to Dropbox"
	print("Uploading " + file_name, end="")
	dbpath = "/Photos/%s/%s" % (project_name, file_name)
	with open(file_name, 'rb') as f:
		db_client.put_file(dbpath, f)
	print(" [done]")
	# Error handling??

def current_time():
	"24 hour time represented as 3 or 4 digits, eg. 800 for 8am"
	now = time.localtime() # Make sure your clock is right
	the_time = (now.tm_hour*100) + now.tm_min
	this_month = time.strftime("%b", now).lower()
	return (the_time, this_month)

def take_photos(interval, project_name, counter, db_client):
	"""Keep gphoto running, monitor for new photos and sleep in between.
	   Returns the updated photo counter"""

	# Local time variables
	the_time, this_month = current_time()

	# Commandline arguments to gphoto
	gp_args = ["gphoto2", "--capture-image-and-download", "-I", str(interval)]


	# Keep track of when gphoto is running
	running = False
	gp_start_t = 0
	gp_runs = 0 # the number of photos taken by this gphoto process

	while (the_time >= sunrise[this_month] and 
	       the_time <= sunset[this_month]):

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

			# Perform other duties 1/4 of a period out of phase 
			time.sleep(interval//4)
		
		# Check for new photos
		for file in sorted(os.listdir()):
			if GP_REGEX.search(file):
				# Rename the files to allow > 10,000
				r_file = "img%05d.jpg" % (counter, )
				os.rename(file, r_file)
				counter += 1

				# Upload to Dropbox if desired
				if db_client:
					dropbox_upload(r_file, project_name,
							       db_client)
		
		# Check that gphoto hasn't died
		if gphoto.poll():
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

	# Create a new photography project
	project_name = input("What would you like to name this photography project? ").strip()

	if os.path.exists(os.path.relpath("photos/" + project_name)):
		print("A project with that name already exists.")
		sys.exit(0)
		# TODO: Handle existing projects
	else:
		os.makedirs('photos/' + project_name)

	# Setup dropbox if desired
	use_dropbox = input("Would you like to upload photos to dropbox [y/N]? ").strip().lower()

	if use_dropbox in ["y", "ye", "yes"]:
		import dropbox
		import dbauth
		db_client = dropbox_connect()
	else:
		db_client = None

	# Now that we've read the dropbox key, hop into the project directory
	os.chdir('photos/' + project_name)

	# Set the time interval to wait between taking photos
	ready = False
	while not ready:
		interval = input("How often would you like to take photos? (seconds) ").strip()
		try:
			interval = int(interval)
			ready = True
		except ValueError as e:
			print("ERROR: Please input a whole number of seconds")

	# Keep track of the number of photos taken
	counter = 0

	# Run forever, but only take photos during the day
	while True:
		the_time, this_month = current_time()

		if (the_time >= sunrise[this_month] and 
		    the_time <= sunset[this_month]):
			
			counter = take_photos(interval, project_name,
						counter, db_client)

		# Wait out the night
		print("Sleeping, night")
		time.sleep(interval//2)

if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt as e:
		print("\nGoodbye!")
