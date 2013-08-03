#!/usr/bin/env python3

import os, sys
import subprocess
import time
import re
import atexit

from daylight import sunrise, sunset

# Perform one-off compilation of the regular expressions
GP_REGEX = re.compile("capt")
PHOTO_REGEX = re.compile("img")

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

	question = "Upload to Dropbox [y/N]: "
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
	"""Return the hours and minutes since midnight and the current month.

	Time: Combined hours and minutes, eg. 2005 for 8:05pm
	Month name: abbreviated, eg. 'jun' for June
	"""
	now = time.localtime() # Make sure your clock is right
	the_time = (now.tm_hour*100) + now.tm_min
	this_month = time.strftime("%b", now).lower()
	return (the_time, this_month)

def create_project():
	"""Create a new photography project and return its information.

	Return:
	1) The project's name.
	2) The (absolute) path to store photos in.
	3) The number to begin new photo labels at (normally 0).
	"""
	
	project_name = input("Project name: ").strip()

	default_path = "photos/%s" % (project_name, )
	question = "Project path [%s]: " % (default_path, )
	project_path = input(question).strip()

	default_path = os.path.abspath(default_path) # avoid printing abspath

	if project_path == "":
		project_path = default_path
	else:
		project_path = os.path.expanduser(project_path)

	# Raw files from gphoto get stored in a sub-directory
	raw_photo_dir = os.path.join(project_path, "raw/")

	# In most cases, start the numbering from zero
	n_start = 0

	if os.path.exists(project_path):
		contents = os.listdir(project_path)

		# Early return for empty folders
		if len(contents) == 0:
			os.makedirs(raw_photo_dir)
			return (project_name, project_path, n_start)

		question = "Folder not empty. Continue project [Y/n]? "
		answer = input(question).strip().lower()

		if answer in ["n", "no"]:
			print("Goodbye!")
			sys.exit(0)


		# Check that the files in the project dir are photos
		for file in contents:
			filepath = os.path.join(project_path, file)
			
			if os.path.isfile(filepath):
				if not PHOTO_REGEX.search(file):
					print("Invalid project directory.")
					sys.exit(1)
			else:
				# Filter out directories
				contents.remove(file)

		# Get the numbering of the last photo taken
		if len(contents) > 0:
			contents = sorted(contents)
			last_photo = contents[len(contents) - 1]
			n_start = re.search(r"[0-9]{5}", last_photo).group()
			n_start = int(n_start)
			n_start += 1 # begin new numbering one higher

		# Deal with the raw directory
		if os.path.isdir(raw_photo_dir):
			for file in sorted(os.listdir(raw_photo_dir)):
				new_file = "img%05d.jpg" % (n_start, )
				new_file = os.path.join(project_path, new_file)
				old_file = os.path.join(raw_photo_dir, file)
				os.rename(old_file, new_file)
				n_start += 1
		else:
			os.makedirs(raw_photo_dir)
	else:
		# Make the project directory, and raw
		os.makedirs(raw_photo_dir)

	return (project_name, project_path, n_start)

def poll_night_mode():
	question = "Night mode [y/N]: "
	answer = input(question).strip().lower()

	if answer in ["y", "ye", "yes"]:
		return True
	else:
		return False

def get_interval():
	"""Fetch and return the time interval to wait between taking photos."""
	
	question = "Time period (seconds): "

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

	# Wait 3 seconds after each photo is taken before checking for files
	offset = 3

	while (the_time >= sunrise[this_month] and
	       the_time <= sunset[this_month]) or night_mode:

		# Start gphoto if it isn't running
		if not running:
			gphoto = subprocess.Popen(gp_args,
						  stdin=subprocess.DEVNULL,
						  stdout=subprocess.DEVNULL)
			running = True
			gp_start_t = int(time.time())
			gp_runs = 1
			atexit.register(gphoto.terminate)
			print("Started a fresh gphoto.")
			time.sleep(offset)
		
		# Check for new photos
		for file in sorted(os.listdir()):
			# Move files to the parent directory (we are in raw)
			new_file = "../img%05d.jpg" % (counter, )
			os.rename(file, new_file)
			counter += 1

			# Upload to Dropbox if desired
			if db_client:
				dropbox_upload(new_file, project_name,
							 db_client)
		
		# Check that gphoto hasn't died
		if gphoto.poll():
			atexit.unregister(gphoto.terminate)
			running = False

		# Wait for gphoto to take a new photo
		wait_until = gp_start_t + gp_runs*interval + offset
		
		while int(time.time()) < wait_until:
			time.sleep(interval//4)

		# Update for the next round
		the_time, this_month = current_time()
		gp_runs += 1
	
	# Quit gphoto at night
	if running:
		atexit.unregister(gphoto.terminate)
		gphoto.terminate()

	return counter

def main():
	print("~ Peppe, the Raspberry Pi time-lapse photographer ~")	

	project_name, project_path, counter = create_project()

	interval = get_interval()

	night_mode = poll_night_mode()
	
	db_client = dropbox_connect()	

	# Perform the actual photo-taking in the project's "raw" directory
	os.chdir(os.path.join(project_path, "raw/"))

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
