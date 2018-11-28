import sys
import os
import argparse

from PyQt5.QtCore import QProcess

from PyQt5.QtWidgets import (QFileDialog, QApplication, QCheckBox, QComboBox,
							QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
							QProgressBar, QPushButton, QTextEdit, QVBoxLayout, QWidget, 
							QMainWindow, QMessageBox, QInputDialog)

# Currently unused
# QStyleFactory
# from PyQt5.QtGui import QPalette, QColor

from sabas_core import sabas_core


''' 
Sabas - a simple tool to create bootable USB drives from ISOs

Licensed under the GPL 3.0 (see licence file)

Gareth Jones 2018
'''

class sabas(QMainWindow):
	''''
	This class handles the input arguments and the GUI for Sabas

	If command line arguments are passed the GUI isn't created and instead
	the program is run from the command line
	'''
	
	# Some handy member variables
	# Create a local sabas object
	sabas_obj = sabas_core()	
	# Which drive we want to write to
	drive_selected = 0	
	# Used in the Drive Info box
	drive_info = ""
	dev_name = ""	
	# Used in the file info box
	file_info = ""
	# Save in case comparison is requested
	sha1_checksum = ""
	# Filename for ISO file to be written to USB
	iso_filename = None
	# Use the command line or GUI version?
	# cline_flag = False
	# Should we check SHA1 
	checksum_flag = False	

	def __init__(self, parent=None):
		super(sabas, self).__init__(parent)
		# self.check_sudo()
		self.process_arguments(sys.argv)



	def check_sudo(self):
		''' Checks if the program has uid of greater than zero for sudo privileges'''

		if os.getuid() > 0:
			raise ValueError("Please run with sudo.")


	def process_arguments(self, args=None):
		''' 
		Handles passed arguments or lack thereof.

		If command line arguments are passed, there's no need for the GUI
		to be loaded, everything can be done on the command line

		Arguments:

		args -- arguments taken from the command line
				by sys.argv			

		'''
		
		parser = argparse.ArgumentParser(description="Sabas - a small ISO to USB writing tool")
		parser.add_argument("-i", "--input", type=str, help="Used to specify the input file")
		parser.add_argument("-o", "--output", type=str, help="Used to specify the drive to write to")
		args = parser.parse_args()

		# If the command line is going to be used instead of the GUI we need
		# both input and output data
		if args.input and args.output is None:
   			parser.error("If using command lines both input and output parameters must be passed.")
		elif args.input and args.output:
			
			self.sabas_obj.cline_flag = True
			# Check the input file exists
			if not os.path.isfile(args.input):
				raise FileNotFoundError(args.input + " not found.")
			
			self.sabas_obj.iso_filename = args.input

			# Check we have a decent drive path
			if "/dev/" not in args.output:
				raise ValueError("Please input a correct drive name. For example /dev/sdc")
			self.sabas_obj.selection = args.output

			self.sabas_obj.run()

		else:
			# Start the GUI
			self.setup_gui()
			self.initial_selection()
			

	def initial_selection(self):
		'''	Sets the first drive found to the selected one '''

		self.select_drive(0)
		self.refresh_drive_info()	


	def get_drives(self):
		'''	 Returns names and basic info about attached USB drives	'''

		self.sabas_obj.find_drives()
		return self.sabas_obj.create_drive_list()


	def checksum_state_changed(self, val):
		''' Do we want to calculate the checksum of the ISO to be written '''

		if val:
			self.checksum_flag = True
		else:
			self.checksum_flag = False

	def setup_gui(self):
		'''	 
		This function creates the structure of the interface.

		Each of the main sections are created in their own separate
		function for modularity.

		'''

		self.setWindowTitle("Sabas")

		drive_combobox = QComboBox()
		drive_combobox.addItems(self.get_drives())

		drive_label = QLabel("&Drive :")
		drive_label.setBuddy(drive_combobox)

		drive_combobox.activated[int].connect(self.select_drive)

		drive_combobox.currentIndexChanged.connect(self.select_drive)
		drive_combobox.currentIndexChanged.connect(self.refresh_drive_info)
		
		checksums_checkbox = QCheckBox("&Check checksums")

		checksums_checkbox.stateChanged.connect(self.checksum_state_changed)

		# Create a layout for the top line
		top_layout = QHBoxLayout()
		top_layout.addWidget(drive_label)
		top_layout.addWidget(drive_combobox)
		top_layout.addStretch(1)
		top_layout.addWidget(checksums_checkbox)

		# Create a process for writing
		self.write_process = QProcess(self)

		# Top line is independent of these functions and is added below
		
		# Create each group in turn
		self.create_drive_box()
		self.create_iso_box()
		self.create_conf_box()

		self.progress_bar = QProgressBar()
		self.progress_bar.setRange(0, 100)
		self.progress_bar.setValue(0)

		# Put this into a View menu
		# self.useStylePaletteCheckBox.toggled.connect(self.changePalette)

		# Need a central widget so we're not operating
		# directly on a QMainWindow
		main_widget = QWidget(self)
		self.setCentralWidget(main_widget)

		# Main grid, add the top line to this grid
		main_layout = QGridLayout()

		main_layout.addLayout(top_layout, 0, 0, 1, 2)
		main_layout.addWidget(self.drive_box, 1, 0)
		main_layout.addWidget(self.iso_box, 1, 1)
		main_layout.addWidget(self.conf_box, 2, 0)
		main_layout.addWidget(self.progress_bar, 2, 1)


		main_layout.setRowStretch(0, 1)
		main_layout.setRowStretch(1, 1)
		main_layout.setRowStretch(2, 0)
		main_layout.setRowStretch(3, 0)

		main_layout.setColumnStretch(0, 1)
		main_layout.setColumnStretch(1, 1)

		# Set a status bar
		self.statusbar = self.statusBar()
		self.update_statusbar("Ready")


		
		main_widget.setLayout(main_layout)


	# Thse can be incorporated into a View -> Theme menu option

	# def changeStyle(self, styleName):
	# 	QApplication.setStyle(QStyleFactory.create(styleName))
	# 	self.changePalette()

	# def changePalette(self):
	# 	if (self.useStylePaletteCheckBox.isChecked()):
	# 	    QApplication.setPalette(QApplication.style().standardPalette())
	# 	else:
	# 	    QApplication.setPalette(self.originalPalette)


	def select_drive(self, drive_number):
		'''
			Selects the drive we want to use
		'''
		self.sabas_obj.set_selection(drive_number)
		self.drive_selected = drive_number


	def update_statusbar(self, sbar_text):
		'''
			Updates the statusbar with the string passed
		'''
		self.statusbar.showMessage(str(sbar_text))

	def get_file_info(self):
		'''	
		Returns a properly formatted string of text
		to be used in iso_info_text() and create_iso_box()			
		'''

		# Get file information and save for later use
		self.iso_fstat = os.stat(self.iso_filename)

		# Get just the filename from the absolute path
		filename = self.iso_filename.split("/")[-1]

		file_info = "Filename : " + filename + "\n" \
					"Size : " + self.sabas_obj.convert_size(self.iso_fstat.st_size) + "\n"					
		

		if self.checksum_flag:
			self.update_statusbar("Calculating checksum...")
			
			self.sha1_checksum = self.sabas_obj.get_checksum(self.iso_filename)
			
			file_info += "SHA1 : " + self.sha1_checksum
			
			self.update_statusbar("Checksum calculated")

		return file_info

		
	def get_drive_info(self):
		'''	
		Returns a properly formatted string of text
		to be used in drive_detail_text() and create_drive_box()

		'''

		# Parse the drive data, set the mount point and display size nicely
		drive_number = self.drive_selected

		drive_name = str(self.sabas_obj.drive_data[drive_number][1])
		
		self.dev_name = str(self.sabas_obj.drive_data[drive_number][2])
		
		drive_size = self.sabas_obj.drive_data[drive_number][3]

		drive_info = "Drive number " + str(drive_number) + " selected" + "\n" \
					"Drive name : " + drive_name + "\n" \
					"Device : /dev/" + self.dev_name + "\n" \
					"Size : " + "{:1.3f}".format(drive_size) + " GB"
		
		return drive_info




	def create_drive_box(self):
		'''
		This creates the box display information about the drive
		size, name, manufacturer etc

		'''
		self.drive_box = QGroupBox("Drive details")

		self.drive_detail_text = QTextEdit()
		self.drive_detail_text.setPlainText(self.drive_info)
		self.drive_detail_text.setReadOnly(True)

		# Have a vertical box layout
		layout = QVBoxLayout()
		layout.addWidget(self.drive_detail_text)
		layout.addStretch(1)

		self.drive_box.setLayout(layout)



	def refresh_drive_info(self):
		'''
		Used to update the information shown about the drive
		with changes in the combobox selection
		'''
		self.drive_info = self.get_drive_info()
		self.drive_detail_text.setPlainText(self.drive_info)

	
	def refresh_file_info(self):
		''' Refreshes the file information about the selected ISO'''

		self.file_info = self.get_file_info()
		self.iso_info_text.setPlainText(self.file_info)

	def compare_checksums(self):
		''' Compares the user given SHA1 and the calculate hash'''

		given_sha1, okPressed = QInputDialog.getText(self, "Checksum","Please enter the SHA1 checksum: ", QLineEdit.Normal, "")
		
		check_my_sum = QMessageBox()
		if okPressed and given_sha1 != '' and given_sha1 == self.sha1_checksum:
			check_my_sum.setText("Checksums match")
			check_my_sum.exec()
		else:
			check_my_sum.setText("Checksum error")
			check_my_sum.exec()


	def write_usb(self):
		'''	
		Confirms the write decision with the user and then
		calls the writing functions to write to the drive
		'''

		filename = self.iso_filename.split("/")[-1]

		# Enter the checksum for comparison
		if self.checksum_flag:
			checksum_conf = self.compare_checksums()

		confirmation = QMessageBox.question(self, "Confirmation", "Are you sure you want to write \n"
						+ filename + " to /dev/" + self.dev_name  + "?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
							

		if confirmation == QMessageBox.Yes:

			self.update_statusbar("Writing to /dev/" + self.dev_name)
			self.cancel_button.setDisabled(False)
			self.do_write()


	def get_status(self):
		''' Gets the status of the write and updates the status bar and progress bar '''
		
		# As readAll returns a QByteArray we need to decode it
		dd_bytes = self.write_process.readAll()
		
		dd_output = str(dd_bytes.data(), encoding="utf-8")
		
		# Update progress bar and the status bar
		self.update_progress(dd_output)
		
		self.update_statusbar(dd_output)


	def do_write(self):
		''' 
		Sets up the QProcess for writing and calls the
		sabas_core function write_dd to write the file to drive
		'''

		# So we read everything coming out of dd
		self.write_process.setProcessChannelMode(QProcess.MergedChannels)		

		# Pass the QProcess and filename to the sabas_core function
		self.sabas_obj.write_dd(self.iso_filename, self.write_process)

		# Connect the writing process with the status update function
		self.write_process.readyRead.connect(self.get_status)

		self.write_process.started.connect(lambda: self.write_button.setDisabled(True))
		self.write_process.finished.connect(lambda: self.update_statusbar("Finished"))	


	def create_iso_box(self):
		'''
		This creates the box display information
		about the ISO, size, checksums etc
		'''
		self.iso_box = QGroupBox("ISO details")

		self.iso_info_text = QTextEdit()
		self.iso_info_text.setPlainText(self.file_info)
		self.iso_info_text.setReadOnly(True)

		# Have a vertical box layout
		layout = QVBoxLayout()
		layout.addWidget(self.iso_info_text)
		layout.addStretch(1)

		self.iso_box.setLayout(layout)   


	def file_open_dialog(self):
		'''
		Sets the file dialog window settings and controls 
		button activation
		'''

		try:
			filename = QFileDialog.getOpenFileName(self, 'Open file', '~')
		
			self.iso_filename = filename[0]
			self.file_info = self.get_file_info()
		
			# Refresh the file information box
			self.write_button.setDisabled(False)
			
			# Update the ISO info text
			self.refresh_file_info()
		
		except OSError as e:
			print("Error, no file selected.")


	def create_conf_box(self):
		''' Creates the box containing the Open and Write buttons '''

		self.conf_box = QGroupBox("File")

		# Make some buttons
		open_button = QPushButton("Open")
		self.write_button = QPushButton("Write")

		# Connect some buttons
		open_button.clicked.connect(self.file_open_dialog)
		self.write_button.clicked.connect(self.write_usb)

		# Initially set to be disabled		
		self.write_button.setDisabled(True)

		conf_layout = QHBoxLayout()
		conf_layout.addWidget(open_button)
		conf_layout.addWidget(self.write_button)
		conf_layout.addStretch(1)

		self.conf_box.setLayout(conf_layout)
	

	def update_progress(self, dd_output):
		'''
		Uses the amount of data transferred by dd to calculate the progress
		of the transfer
		'''
		# Get the size of the file in bytes
		iso_in_bytes = self.iso_fstat.st_size

		# We only want the number of bytes transferred
		dd_list = dd_output.split()	

		progress = 0

		# The first output from dd is an empty string to we want to ignore that
		if len(dd_list) > 0:
			bytes_written = dd_list[0]

			# Make sure it's not some weird output
			if bytes_written.isdigit():
				progress = 100 * (int(bytes_written)/int(iso_in_bytes))
				self.progress_bar.setValue(progress)


if __name__ == '__main__':

	sabas_app = QApplication(sys.argv)
	sabas_instance = sabas()
	sabas_instance.show()
	sys.exit(sabas_app.exec_()) 
