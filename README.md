# sabas
A small ISO to USB writer for creating bootable USB drives

### Usage
```
sudo python sabas.py
```

This will load the graphical interface that allows selection of the USB drive to write to and
browsing for the required .iso file.

It can also be used from the command line

```
sudo python sabas.py -i openbsd_6p4.iso -o /dev/sdc
```

This will then ask you confirm your selection and will then write the file to the drive using the Linux dd command.

### Requirements

PyQt5

### Acknowledgements

Pete Batard - Rufus - https://github.com/pbatard/rufus - the excellent ISO writing tool

Balazs Saros  - https://github.com/balzss - for the some inspiration for the drive information and mount checking
functions
