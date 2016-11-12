# rpmrepodiff
## Overview
rpmrepodiff will determine the differences between two repositories published via
http(s).

rpmrepodiff parses the XML metadata within the repositories into associative arrays
and then determines the differences between them, returning the results as JSON.

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
[21:56 leeh@c7dev:~/rpmrepodiff]$ ./rpmrepodiff.py -h
usage: rpmrepodiff.py [-h] -s SOURCE -d DEST [-b] [-q]

optional arguments:
  -h, --help  show this help message and exit
  -s SOURCE   Source Repo URL.
  -d DEST     Dest Repo URL.
  -b          Brief mode. Output sync status only.
  -q          Quick mode. Use hash comparisons to determine sync status.
              Enables brief mode.
  -t          Text mode. Output results in human text form rather than JSON.
```

The Repo URLs need to point to the folder which *contains* the 'repodata' folder.  If
you're unsure, locate the repomd.xml file within the repodata folder, then strip the 
'repodata/repomd.xml' from the URL before passing it to rpmrepodiff.

## Errors
rpmrepodiff will exit with a non-zero return value if it encounters an error and will
print an appropriate message to stderr, generally with no data sent to stdout.

## Quick Mode
In Quick Mode, rpmrepodiff will download the main XML metadata containing the list
of RPMs, uncompresses it as necessary and then compares the sha256 hash of the
metadata, rather than parsing and doing a nested comparison.

It is generally accurate and a lot faster for large repos, but may report the repos
as unsynced if the metadatas regenerated on a schedule even when the content hasnt 
changed as the hashes will then likely be different.

## Output Format
### Full Mode (Default)
rpmrepodiff will return a JSON assoc array with the keys as the names of the packages
that are different and the corresponding values being a nested assoc array.  The nested 
assoc arrays will have one of the following keys:

* added - Indicates the given package exists in DEST but not SOURCE
* removed - Indicates the given package exists in SOURCE but not DEST
* upgraded_src and upgraded_dst - Indicates the given package exists in both SOURCE and DEST, but at their respective different versions

The nested assoc arrays value is set to an array with a list of all the version numbers
that have changed between the SOURCE and DEST.

If there are no differences between the repos, rpmrepodiff returns an empty JSON assoc array.

#### Full Mode Example
The below example has been pretty-printed and will be outputted from rpmrepodiff as a single line:
```
{
   "kernel":{
      "upgraded_dst":[
         "3.10.0-229.1.2.el7.x86_64",
         "3.10.0-229.11.1.el7.x86_64"
      ],
      "upgraded_src":[
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
