# sabas
A small ISO to USB writer for creating bootable USB drives on Linux

### Usage
```
sudo python sabas.py
```

This will load the graphical interface that allows selection of the USB drive to write to and
browsing for the required .iso file.

![Alt text](/img/main_window.png?raw=true "Main Window")

If the "Check checksums" box is ticked the SHA1 hash of the ISO file will be requested for comparison
with the one calculated by the program.

![Alt text](/img/sha1_comparison.png?raw=true "SHA1 request")


Sabas can also be used from the command line

```
sudo python sabas.py -i openbsd_6p4.iso -o /dev/sdc
```

This will then ask you confirm your selection and will then write the file to the drive using the Linux dd command.

### Requirements

Python, PyQt5, Linux core utilities

### Acknowledgements

Pete Batard - Rufus - https://github.com/pbatard/rufus - the excellent ISO writing tool

Balazs Saros  - https://github.com/balzss - inspiration for the drive information and mount checking functions
