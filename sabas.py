import sys
import os
import math
import hashlib
import argparse

from PyQt5.QtCore import QDateTime, Qt, QTimer, pyqtSignal, QThreadPool
from PyQt5.QtWidgets import (QFileDialog, QApplication, QCheckBox, QComboBox, QDateTimeEdit,
        QDial, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QProgressBar, QPushButton, QRadioButton, QScrollBar, QSizePolicy,
        QSlider, QSpinBox, QStyleFactory, QTableWidget, QTabWidget, QTextEdit,
        QVBoxLayout, QWidget, QMainWindow, QMessageBox, QInputDialog)

from PyQt5.QtGui import QPalette, QColor


from sabas_core import sabas_core
from sabas_threads import worker_signals, worker


class sabas(QMainWindow):
	
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
	cline_flag = False
	# Should we check SHA1 
	checksum_flag = False	

	def __init__(self, parent=None):
		super(sabas, self).__init__(parent)
		# self.check_sudo()
		self.process_arguments(sys.argv)

	def check_sudo(self):
		''' 
			Checks the uid of the running process to check if
			we have sudo priviliges for dd
		'''
		if(os.getuid() > 0):
			raise ValueError("Please run with sudo.")


	def process_arguments(self, args=None):
		'''
			Handles passed arguments or lack thereof.

			If command line arguments are passed, there's no need for the GUI
			to be loaded, everything can be done on the command line
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
			# self.cline_flag = True
			self.sabas_obj.cline_flag = True
			# print("We have arguments!")

			# Check the input file exists
			if not os.path.isfile(args.input):
				raise FileNotFoundError(args.input + " not found.")
			
			self.sabas_obj.iso_filename = args.input

			# Check we have a decent drive path
			if "/dev/" not in args.output:
				raise ValueError("Please input a correct drive name. For example /dev/sdc")
			self.sabas_obj.selection = args.output

			self.sabas_obj.run()

		# Start the GUI
		else:
			self.setup_gui()
			self.initial_selection()
			self.setup_threads()


	def initial_selection(self):
		'''
			Sets the first drive found to the selected one
		'''
		# self.sabas_obj._write_status = 5

		self.selectDrive(0)
		self.refreshDriveInfo()	


	def setup_threads(self):
		# Create a threadpool
		self.threadpool = QThreadPool()
		print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

	# Replace with actual get drive function
	def get_drives(self):
		'''	
			Returns names and basic info about attached USB drives

		'''
		self.sabas_obj.find_drives()
		return self.sabas_obj.create_drive_list()


	def checksum_state_changed(self, val):
		if val:
			self.checksum_flag = True
		else:
			self.checksum_flag = False

	def setup_gui(self):

		self.setWindowTitle("Sabas")

		driveComboBox = QComboBox()
		driveComboBox.addItems(self.get_drives())

		driveLabel = QLabel("&Drive :")
		driveLabel.setBuddy(driveComboBox)

		driveComboBox.activated[int].connect(self.selectDrive)

		driveComboBox.currentIndexChanged.connect(self.selectDrive)
		driveComboBox.currentIndexChanged.connect(self.refreshDriveInfo)
		
		checksumsCheckBox = QCheckBox("&Check checksums")

		checksumsCheckBox.stateChanged.connect(self.checksum_state_changed)

		topLayout = QHBoxLayout()
		topLayout.addWidget(driveLabel)
		topLayout.addWidget(driveComboBox)
		topLayout.addStretch(1)
		topLayout.addWidget(checksumsCheckBox)

		# Top line is independent of these functions and is added below
		# Create each group in turn
		self.createDriveInfoBox()
		self.createISOInfoBox()
		self.createConfirmationBox()

		# Put this into a View menu
		# self.useStylePaletteCheckBox.toggled.connect(self.changePalette)

		wid = QWidget(self)
		self.setCentralWidget(wid)

		# Main grid, add the top line to this grid
		mainLayout = QGridLayout()

		mainLayout.addLayout(topLayout, 0, 0, 1, 2)
		mainLayout.addWidget(self.DriveInfoBox, 1, 0)
		mainLayout.addWidget(self.ISOInfoBox, 1, 1)
		mainLayout.addWidget(self.confirmationBox, 2, 0)

		mainLayout.setRowStretch(0, 1)
		mainLayout.setRowStretch(1, 1)
		mainLayout.setRowStretch(2, 0)
		mainLayout.setRowStretch(3, 0)

		mainLayout.setColumnStretch(0, 1)
		mainLayout.setColumnStretch(1, 1)

		# Set a status bar
		self.statusbar = self.statusBar()
		self.update_statusbar("Ready")
		
		wid.setLayout(mainLayout)


	# Thse can be incorporated into a View -> Theme menu option

	# def changeStyle(self, styleName):
	# 	QApplication.setStyle(QStyleFactory.create(styleName))
	# 	self.changePalette()

	# def changePalette(self):
	# 	if (self.useStylePaletteCheckBox.isChecked()):
	# 	    QApplication.setPalette(QApplication.style().standardPalette())
	# 	else:
	# 	    QApplication.setPalette(self.originalPalette)


	def selectDrive(self, drive_number):
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

	def getFileInfo(self):
		'''	
			Returns a properly formatted string of text
			to be used in ISODetailText() and createISOInfoBox()

			Return : string
		'''
		fstat = os.stat(self.iso_filename)

		file_stat = "Filename : " + self.iso_filename + "\n" \
					"Size : " + self.sabas_obj.convert_size(fstat.st_size) + "\n"
					
		

		if self.checksum_flag:
			self.update_statusbar("Calculating checksum...")
			self.sha1_checksum = self.sabas_obj.get_checksum(self.iso_filename)
			file_stat += "SHA1 : " + self.sha1_checksum
			self.update_statusbar("Checksum calculated")

		return file_stat

		
	def getDriveInfo(self):
		'''	
			Returns a properly formatted string of text
			to be used in DriveDetailText() and createDriveInfoBox()

			Return : string
		'''

		# Parse the drive data, set the mount point and display size nicely
		drive_number = self.drive_selected
		drive_name = str(self.sabas_obj.drive_data[drive_number][1])
		self.dev_name = str(self.sabas_obj.drive_data[drive_number][2])
		size = self.sabas_obj.drive_data[drive_number][3]

		tidy_info = "Drive number " + str(drive_number) + " selected" + "\n" \
					"Drive name : " + drive_name + "\n" \
					"Device : /dev/" + self.dev_name + "\n" \
					"Size : " + "{:1.3f}".format(size) + " GB"
		
		return tidy_info



	# This will go top left
	def createDriveInfoBox(self):
		'''
			This creates the box display information about the drive
			Size, name, manufacturer etc

		'''
		self.DriveInfoBox = QGroupBox("Drive details")

		self.DriveDetailText = QTextEdit()
		self.DriveDetailText.setPlainText(self.drive_info)
		self.DriveDetailText.setReadOnly(True)

		# Have a vertical box layout
		layout = QVBoxLayout()
		layout.addWidget(self.DriveDetailText)
		layout.addStretch(1)
		self.DriveInfoBox.setLayout(layout)



	def refreshDriveInfo(self):
		'''
			Used to update the information shown about the drive
			with changes in the combobox selection
		'''
		self.drive_info = self.getDriveInfo()
		self.DriveDetailText.setPlainText(self.drive_info)

	
	def refreshFileInfo(self):
		''' 
			Refreshes the file information about the selected ISO
		'''
		# print("Refreshing file info")
		self.file_info = self.getFileInfo()
		self.ISODetailText.setPlainText(self.file_info)

	def compare_checksums(self):
		given_sha1, okPressed = QInputDialog.getText(self, "Checksum","Please enter the SHA1 checksum: ", QLineEdit.Normal, "")
		
		# if given_sha1 != iso.sha1_checksum:
		# 	print("Error : checksums do not match")

		check_my_sum =  QMessageBox()
		if okPressed and given_sha1 != '' and given_sha1 == self.sha1_checksum:
			check_my_sum.setText("Checksums match")
			check_my_sum.exec()
		else:
			check_my_sum.setText("Error with checksum")
			check_my_sum.exec()

	# def progress_update(self, n):
	# 	'''
	# 		Updates the progress in the status bar
	# 		and the progress bar when implemented
	# 	'''
	# 	self.update_statusbar()
	def thread_complete(self):
		self.update_statusbar("Finished writing.")

	def write_usb(self):
		'''	
			Confirms the write decision with the user and then
			spawns a new worker thread to call dd and write to the drive
		'''

		filename = self.iso_filename.split("/")[-1]

		# Enter the checksum for comparison
		checksum_conf = None
		if self.checksum_flag == True:
			checksum_conf = self.compare_checksums()

		confirmation = QMessageBox.question(self, "Confirmation", "Are you sure you want to write \n"
										   + filename + " to /dev/" + self.dev_name  + "?",	\
		 								   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

		if confirmation == QMessageBox.Yes:

			self.update_statusbar("Writing to /dev/" + self.dev_name)
			self.cancel_button.setDisabled(False)

			# Create the worker
			dd_worker = worker(self.sabas_obj.write_dd(self.iso_filename))
			# Connect it with the signals defined in the worker_signals class
			# dd_worker.signals.result.connect(self.print_output)
			dd_worker.signals.finished.connect(self.thread_complete)
			dd_worker.signals.progress.connect(self.update_statusbar)

			# Pass the worker to the threadpool to start work
			self.threadpool.start(dd_worker)
			
			self.update_statusbar("Finished")
			# Update the status bar with the output from dd



	# Top right
	def createISOInfoBox(self):
		'''
			This creates the box display information
			about the ISO, size, checksums etc
		'''
		self.ISOInfoBox = QGroupBox("ISO details")

		self.ISODetailText = QTextEdit()
		self.ISODetailText.setPlainText(self.file_info)
		self.ISODetailText.setReadOnly(True)

		# Have a vertical box layout
		layout = QVBoxLayout()
		layout.addWidget(self.ISODetailText)
		layout.addStretch(1)
		self.ISOInfoBox.setLayout(layout)   


	def fileOpenDialog(self):
		try:
			fname = QFileDialog.getOpenFileName(self, 'Open file', '~')
			self.iso_filename = fname[0]
			self.file_info = self.getFileInfo()
			# Refresh the file information box
			self.write_button.setDisabled(False)
			self.refreshFileInfo()
		except OSError as e:
			print("Error, no file selected.")


	def createConfirmationBox(self):
		self.confirmationBox = QGroupBox("File")

		open_button = QPushButton("Open")

		self.write_button = QPushButton("Write")

		open_button.clicked.connect(self.fileOpenDialog)
		self.write_button.clicked.connect(self.write_usb)
		self.write_button.setDisabled(True)
				
		# Horizontal baby
		confLayout = QHBoxLayout()
		confLayout.addWidget(open_button)
		confLayout.addWidget(self.write_button)
		confLayout.addStretch(1)

		self.confirmationBox.setLayout(confLayout)

	def update_progress(self):
		# Read the data from dd - take the amount of data copied and 
		# the file size and then use the transfer rate to update the progress
		# bar
		self.progressBar.setValue(0)


	def createProgressBar(self):
		self.progressBar = QProgressBar()
		self.progressBar.setRange(0, 10000)
		self.progressBar.setValue(0)

		timer = QTimer(self)
		timer.timeout.connect(self.advanceProgressBar)
		timer.start(1000)





if __name__ == '__main__':

	sabas_app = QApplication(sys.argv)
	sabas_instance = sabas()
	sabas_instance.show()
	sys.exit(sabas_app.exec_()) 
