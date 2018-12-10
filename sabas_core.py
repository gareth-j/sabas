import subprocess
import os
import sys
import argparse
import signal
import hashlib
import math

class sabas_core():
	'''
	The core of the program that does most of the work

	The functions in this class can be used straight from the command line
	though sabas.py by passing command line arguments
	'''

	
	# Some useful member variables
	# Hold the drive data for access by other functions	
	drive_data = []
	selection = ""
	status = ""
	iso_filename = None
	selected_drive = None # This could just be selection
	# Are we running just from the command line?
	cline_flag = False

	def __init__(self):
		# Handle Ctrl-C a bit more cleanly
		signal.signal(signal.SIGINT, self.signal_handler)

	def signal_handler(self, sig, frame):
		''' Handles Ctrl+C being pressed and exits the program '''
		
		print('\n\nYou pressed Ctrl+C. Exiting.\n')
		exit()


	def find_drives(self):
		'''
			Checks /dev/disk/by-id for attached USB drives.

			Each drive's information is collected into a tuple and
			appended to the drive_data class member list

		'''

		raw_drive = subprocess.check_output("ls -l /dev/disk/by-id/", shell=True).decode("utf-8")
		
		if 'usb' not in raw_drive:
		    print("No USB drives detected. Please reconnect the device and try again.")
		    exit()

		drive_list = [d for d in raw_drive.split('\n')[:-1] if not d[-1].isdigit() and 'usb' in d]
		
		labels = []
		for i, drive in enumerate(drive_list):
			# Extract the name from the ls command return
			name = ' '.join(drive.split('usb-')[1].split('_')[:-1])	
			# Get block device / /dev point at which the USB is located
			label = drive.split('/')[-1]
			# Save the label for access next
			div_to_GB = (2 * 1024 * 1024)
			size = int(subprocess.check_output("cat /sys/class/block/" + str(label) + "/size", shell=True)) / div_to_GB

			self.drive_data.append((i, name, label, size))


	def create_drive_list(self):
		''' 
		 Creates a list of drives that can be used by the interface or the command line

		 Returns the list of drives found
		'''

		drive_list = []
		for drive in self.drive_data:
			drive_list.append("[" + str(drive[0]) + "] " + str(drive[1]) + " " + "{:1.2f}".format(drive[3])  + " GB")

		return drive_list


	def set_selection(self, user_selection):
		''' 
		Can be called from the command line by drive_selection or
		from the GUI from the combobox

		GUI or command line

		'''
		self.drive_name = self.drive_data[int(user_selection)][2]

		self.selection =  "/dev/" + self.drive_name


	def drive_selection(self):
		'''
		Asks the user to select the USB drive they want to write to

		Command line only

		'''
		print('List of your USB drives:\n')

		drive_list = self.create_drive_list()
		
		user_selection = ""
		while not user_selection.isdigit() or int(user_selection) > (len(self.drive_data)-1):
			user_selection = input("Please select a drive number : ")

		self.set_selection(user_selection)


	def hd_check(self):
		'''Checks to make sure the selected drive isn't a hard-drive'''

		drive_name = self.selection.split("/")[-1]

		result = subprocess.check_output("find /dev/disk/by-id/ -lname " + "'*" + drive_name + "'", shell=True).decode("utf-8")

		if "usb" not in result:
			raise ValueError("Error : this is not a USB drive.")


	def mount_checks(self):
		'''
		Checks the status of the selected drive and its mount status	

		Attempts to unmount the selected drive
		'''
			
		print("Checking if " + self.selection + " is mounted...")
		
		mounted = ""
		try:
			mounted = subprocess.check_output("mount | grep " + self.selection, shell=True).decode("utf-8")
		except subprocess.CalledProcessError as err:
			print("Not mounted")

		# Find is multiple partitions are mounted
		partitions = [x for x in mounted.split(" ") if self.selection in x]

		if mounted:
			print("Attempting to unmount device")
			for part in partitions:					
				try:
					umount_stat = subprocess.check_output("umount " + part, shell=True)
					print("Drive unmounted successfully")
				except subprocess.CalledProcessError as err:
					print("Unable to unmount the drive.")


	# This is a modified version of a function taken from
	# https://stackoverflow.com/a/22058673/10354589
	def get_checksum(self, filename):
		'''	Returns the SHA1 hashsum of the file given by filename'''	

		# Keep memory usage down by reading in small 256 kb chunks
		buffer_size = 262144  

		sha1 = hashlib.sha1()
		md5 = hashlib.md5()

		with open(filename, 'rb') as f:
		    while True:
		        data = f.read(buffer_size)
		        if not data:
		            break
		        sha1.update(data)
		        # md5.update(data)
		
		# print("MD5: {0}".format(md5.hexdigest()))
		# print("SHA1: {0}".format(sha1.hexdigest()))
		
		# Return a tuple with the values
		# return (md5.hexdigest(), sha1.hexdigest())
		return sha1.hexdigest()

	# This function modified from 
	# https://stackoverflow.com/a/14822210/10354589
	def convert_size(self, size_bytes):
		''' Takes a size in bytes and creates a string with sensible units '''
		
		if size_bytes == 0:
			return "0 B"
		
		size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
		
		i = int(math.floor(math.log(size_bytes, 1024)))
		
		p = math.pow(1024, i)
		
		s = round(size_bytes / p, 2)
		
		return "%s %s" % (s, size_name[i])



	def write_cline(self):
		'''This function does the actual writing to USB using the Linux dd command'''

		# If we already have the filename from command line, continue
		if self.iso_filename == None:
			self.iso_filename = str(input("Please enter the path to the ISO file : "))

		confirmation = ""
		valid_confirmations = ["y", "Y", "n", "N"]

		while confirmation not in valid_confirmations:
			confirmation = input("Are you sure you want to continue and write " + self.iso_filename + "to " + self.selection + "? (y / n) : ")

		if confirmation == "y" or confirmation == "Y":
			self.write_dd(self.iso_filename)
			
		elif confirmation == "n" or confirmation == "N":
			print("Exiting.")
			exit()


	def write_dd(self, filename, write_process = None):
		'''
		Does the actual writing, this can be called from either the command
		line or the GUI
		'''
		our_filename = filename

		status = 0
		# If we have a QProcess to write with (passed in from the GUI)
		if write_process:
			status = write_process.start("sudo dd bs=4M if=" + our_filename + " of=" + self.selection + " status=progress oflag=sync")
		else:
			status = subprocess.check_output("sudo dd bs=4M if=" + our_filename + " of=" + self.selection \
											+ " status=progress oflag=sync", shell=True).decode("utf-8")


		if status == 0:
			print("Write successful")
		elif status == 1:
			print("Error writing to device")


	def create_storage_drive(self, filesystem, write_process=None):

		# Set the partition types we want to use with different filesystems

		partition_type = None
		format_flag = " "
		if filesystem == "fat32":
			partition_type = "83"
		elif filesystem == "ntfs":
			partition_type = "07"
			# For fast format of the NTFS partition
			format_flag = " -f"
		elif filesystem == "exfat":
			partition_type = "07"
		else:
			raise ValueError("Error : incorrect filesystem selected.")

		# Check that we're not trying to destroy a HD
		self.hd_check()
		# Ensure the drive isn't mounted
		self.mount_checks()


		print("Warning - this will wipe everything from the drive and create a " + filesystem + " filesystem.")

		confirmation = ""
		valid_confirmations = ["y", "Y", "n", "N"]

		while confirmation not in valid_confirmations:
			confirmation = input("Are you sure you want to continue and write a " + filesystem + " partition to " + self.selection + "? (y / n) : ")

		if confirmation == "y" or confirmation == "Y":
			if write_process:
				try:
					# Wipes all file systems from the drive
					write_process.start("sudo wipefs -a " + self.selection)
					# Creates a partition
					write_process.start("sudo echo \"type=" + partition_type + "\" | sudo sfdisk " + self.selection)
					# Formats the partition
					write_process.start("sudo mkfs." + filesystem + format_flag + self.selection + "1")
				except:
					print("Error writing to drive.")
					exit()
			
			# If we're running this from the command line and don't have a QProcess			
			else:
				try:					
					# Wipes all file systems from the drive
					print("Wiping drive...")
					status = subprocess.check_output("sudo wipefs --all " + self.selection, shell=True).decode("utf-8")
					# Creates a partition
					print("Creating partition...")
					status = subprocess.check_output("sudo echo \"type=" + partition_type + "\" | sudo sfdisk " + self.selection, shell=True).decode("utf-8")
					# Formats the partition
					print("Formatting partition...")
					status = subprocess.check_output("sudo mkfs." + filesystem + format_flag + self.selection + "1", shell=True).decode("utf-8")
					print("Finished")
				except subprocess.CalledProcessError:
					print("Error writing to drive.")
					exit()
		

		elif confirmation == "n" or confirmation == "N":
			print("Exiting.")
			exit()
			

		

		



	def run(self):
		self.find_drives()

		if self.cline_flag == False:
			self.drive_selection()

		self.mount_checks()

		self.hd_check()

		self.write_cline()

		exit()