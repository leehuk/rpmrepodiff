# rpmrepodiff
## Overview
rpmrepodiff will determine the differences between two repositories published via
http(s).

rpmrepodiff locates the primary XML metadata within the repositories and runs sha
hash comparisons on them to determine if they are identical.  If not, it will parse
the metadata into associative arrays and determine the exact set of differences
between the two repositories -- returning the results as JSON or human readable text.

## Requirements
rpmrepodiff requires:

* python
* python-requests

Most versions of the requests module should work, so you can install this either via
the OS or via pip.

For pip:
```
pip install requests
```

For CentOS:
```
yum install python-requests
```

For Debian:
```
apt-get update && apt-get install python-requests
```

## Installation
Install the requirements above, download it and run it.

Preferably dont run it as root.

## Usage
```
[16:43 leeh@initium:~/rpmrepodiff]# ./rpmrepodiff.py -h
usage: rpmrepodiff.py [-h] -s SOURCE -d DEST [-b] [-q] [-t]

optional arguments:
  -h, --help  show this help message and exit
  -s SOURCE   Source Repo URL.
  -d DEST     Dest Repo URL.
  -b          Brief mode. Output sync status only.
  -q          Quick mode. Skip the XML parsing stage and only analyse the sha
              hashes. May return incorrect results. Enables brief mode.
  -t          Text mode. Output results in human text form rather than JSON.
```

The Repo URLs need to point to the folder which *contains* the 'repodata' folder.  If
you're unsure, locate the repomd.xml file within the repodata folder, then strip the 
'repodata/repomd.xml' from the URL before passing it to rpmrepodiff.

## Errors
rpmrepodiff will exit with a non-zero return value if it encounters an error and will
print an appropriate message to stderr, generally with no data sent to stdout.

## Quick Mode
In Quick Mode, rpmrepodiff will stop after the sha hash comparisons of the metadata and
wont do nested comparisons.  It is a lot quicker for large repositories, but not generally
recommended because some repositories regenerate their metadata on a nightly basis,
leading to different sha hashes even when the actual content is identical.

## Output Format
### Full Mode (Default)
rpmrepodiff will return a JSON assoc array '{key: value}' with parameters:

* key - The name of the package.
* value - A nested JSON assoc array.

The nested JSON assoc array '{nestkey: nestvalue}' has parameters:

* nestkey - One of the following items:
  * added - Indicates the given package exists in DEST but not SOURCE
  * removed - Indicates the given package exists in SOURCE but not DEST
  * version_added - Indicates the given package exists in both SOURCE and DEST, but has
    versions that only exist in DEST.
  * version_removed - Indicates the given package exists in both SOURCE and DEST, but has
    versions that only exist in SOURCE.
* nestvalue - An array '[]' containing a list of all the version numbers that have changed
  between SOURCE and DEST.

If there are no differences between the repos, rpmrepodiff returns an empty JSON assoc array '{}'.

#### Full Mode Example
The below example has been pretty-printed and will be outputted from rpmrepodiff as a single line:
```
{
   "kernel":{
      "version_added":[
         "3.10.0-229.1.2.el7.x86_64",
         "3.10.0-229.11.1.el7.x86_64"
      ],
      "version_removed":[
         "3.10.0-123.13.1.el7.x86_64",
         "3.10.0-123.4.2.el7.x86_64"
      ]
   },
   "iputils":{
      "added":[
         "20121221-6.el7_1.1.x86_64"
      ]
   },
   "rpm-devel":{
      "removed":[
         "4.11.1-18.el7_0.x86_64",
         "4.11.1-18.el7_0.i686"
      ]
   }
}
```

### Brief Mode
rpmrepodiff will return a JSON assoc array with a single key 'synced', which has a boolean
value indicating whether the repo is synced (true) or unsynced (false):

#### Brief Mode Example
```
{"synced": false}
```

### Text Mode
rpmrepodiff will return the data in human readable form rather than JSON.  For Brief Mode,
this is basically either the word "Synced" or "Unsynced".  For Full Mode, this is a visual
tree showing the relevant changes if any.

#### Text Mode Example (Brief)
```
[15:59 leeh@c7dev:~/rpmrepodiff]$ ./rpmrepodiff.py -s http://repo.example.com/tmp/7.0-updates/ -d http://repo.example.com/tmp/7.1-updates/ -tbq
Unsynced
```

#### Text Mode Example (Full)
````
[16:00 leeh@c7dev:~/rpmrepodiff]$ ./rpmrepodiff.py -s http://repo.example.com/tmp/7.0-updates/ -d http://repo.example.com/tmp/7.1-updates/ -t
iputils
       Added              20121221-6.el7_1.1.x86_64

kernel
       Version Removed    3.10.0-123.13.1.el7.x86_64
                          3.10.0-123.4.2.el7.x86_64
       Version Added      3.10.0-229.1.2.el7.x86_64
                          3.10.0-229.11.1.el7.x86_64

rpm-devel
       Removed            4.11.1-18.el7_0.i686
                          4.11.1-18.el7_0.x86_64
````
