#!/usr/bin/env python3

import os
import signal
import time

import dropbox
import dbauth

def dropbox_authorise():
	"Authorise the application to use a specific user's Dropbox"

	flow = dropbox.client.DropboxOAuth2FlowNoRedirect(dbauth.DB_APP_KEY, dbauth.DB_APP_SECRET)

	authorize_url = flow.start()

	print("As this is your first run, you'll need to grant Peppe access to your Dropbox")
	print('1. Go to: ' + authorize_url)
	print('2. Click "Allow" (you might have to log in first)')
	print('3. Copy the authorization code.')
	auth_code = input("Enter the authorization code here: ").strip()
	
	access_token, user_id = flow.finish(auth_code)

	auth_file = open('db_auth', 'w')
	auth_file.write(access_token)
	auth_file.close()

	return access_token

def start_gphoto(interval, project_name):
	id = os.fork()
	args = ["gphoto2", "--capture-image-and-download", "-I %d" % interval]

	if id == 0:
		os.chdir('photos')
		os.execv('/usr/bin/gphoto2', args)
	
	return id

def stop_gphoto(pid):
	print("Killing gphoto2 @ %d" % (pid, ))
	os.kill(pid, signal.SIGTERM)

if __name__ == "__main__":
	print("~ Peppe, the Raspberry Pi time-lapse photographer ~")	

	## Connect to Dropbox ##
	access_token = ""
	
	if os.path.isfile(os.path.relpath('access_token')):
		auth_file = open('access_token', 'r')
		access_token = auth_file.read().strip()
		auth_file.close()
	else:
		access_token = dropbox_authorise()

	client = dropbox.client.DropboxClient(access_token)

	print("Connected to Dropbox successfully!")
	print("")

	## Create a new photography project ##
	project_name = input("What would you like to name this photography project? ").strip()

	if os.path.exists(os.path.relpath("photos/" + project_name)):
		print("A project with that name already exists.")
		return

	os.makedirs('photos' + project_name)

	## Start taking photos ##
	interval = 10 # seconds

	gphoto_pid = start_gphoto(interval, project_name)

	# Sleep half an interval, then start watching for files
	time.sleep(interval//2)
	counter = 0

	# Files todo:
	# More sensible naming; img00001.jpg. Allow multiple gphoto starts 
	# Upload to Dropbox
	# 

	# General todo: Quit gphoto at night!

	while (true):
		
