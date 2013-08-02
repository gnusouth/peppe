Peppe
=====

Peppe is a time-lapse photographer for the Raspberry Pi (or indeed any computer). It is basically a front-end to the wonderful `gphoto2`.

### Setup ###

* Make sure you have Python 3 or greater installed (`python3`)

* Install `gphoto2` (available in repositories)

* Connect your camera via USB

* Run peppe.py from the command-line!

### Dropbox ###

Peppe has the ability to upload photos to dropbox as they are taken, this requires a few extra steps.

* Install the Python tool, `pip` if you haven't already got it (get the Python 3 version)

* Install the Python interface to Dropbox. On Ubuntu 13.04:  
    `sudo pip3 install dropbox`

* Create a free Dropbox account if you don't already have one

### Recommendations ###

* Disable your camera's auto-sleep function (or make it longer than the photo period)

* You can setup your camera to take photos however you like. Manual focus with automatic shutter/aperture seems a good choice.
