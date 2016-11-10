#!/usr/bin/env python
#
# rpmrepodiff.py
#	Tool for diffing RPM repositories
#
# https://github.com/leehuk/rpmrepodiff/
#
# Copyright (C) 2016, Lee H <lee@leeh.uk>
# Released under the BSD 2-Clause License

import argparse
import collections
import gzip
import hashlib
import json
import re
import StringIO
import sys
import time
import xml.etree.ElementTree as ET

import requests

def get_repomd(url):
	r = requests.get(url)
	if r.status_code != 200:
		r.raise_for_status()

	return r.content

def parse_repomd(repomdcontent):
	repomddata = {}

	xmldata = ET.fromstring(repomdcontent)
	for mdelem in xmldata.iter('{http://linux.duke.edu/metadata/repo}data'):
		for tag in mdelem:
			if tag.tag == '{http://linux.duke.edu/metadata/repo}location':
				repomddata[mdelem.attrib['type']] = tag.attrib['href']

	return repomddata

def get_primarymd(url):
	r = requests.get(url)
	if r.status_code != 200:
		raise Exception('Error retrieving "' + url + '": Code ' + str(r.status_code))

	primarymdcontent = r.content
	# decompress if necessary
	if re.search('\.gz$', url):
		primarymdcontentgz = StringIO.StringIO(primarymdcontent)
		with gzip.GzipFile(fileobj=primarymdcontentgz) as f:
			primarymdcontent = f.read()

	return primarymdcontent

def parse_primarymd(primarymdcontent):
	rpmdata = {}

	xmldata = ET.fromstring(primarymdcontent)
	for packagedata in xmldata.iter('{http://linux.duke.edu/metadata/common}package'):
		if packagedata.attrib['type'] != 'rpm':
			continue

		tagdata = {}
		for tag in packagedata:
			if tag.tag == '{http://linux.duke.edu/metadata/common}name':
				tagdata['name'] = tag.text
			elif tag.tag == '{http://linux.duke.edu/metadata/common}version':
				tagdata['version'] = tag.attrib['ver'] + '-' + tag.attrib['rel']
			elif tag.tag == '{http://linux.duke.edu/metadata/common}arch':
				tagdata['arch'] = tag.text

		if not tagdata['name'] in rpmdata:
			rpmdata[tagdata['name']] = []

		rpmdata[tagdata['name']].append(tagdata['version'] + '.' + tagdata['arch'])

	return rpmdata

def rpmdiff_set(rpmdiff, name, mode, version):
	if not name in rpmdiff:
		rpmdiff[name] = {}

	if not mode in rpmdiff[name]:
		rpmdiff[name][mode] = []

	rpmdiff[name][mode].append(version)

parser = argparse.ArgumentParser()
parser.add_argument('-s', dest='source', nargs=1, required=True, help='Source Repo URL.')
parser.add_argument('-d', dest='dest', nargs=1, required=True, help='Dest Repo URL.')
parser.add_argument('-b', action='store_true', dest='brief', help='Brief mode.  Output sync status only.')
parser.add_argument('-q', action='store_true', dest='quick', help='Quick mode.  Use hash comparisons to determine sync status.  Enables brief mode.')
args = parser.parse_args()

baseurl_src = args.source[0]
baseurl_dst = args.dest[0]

repomdurl_src = baseurl_src + 'repodata/repomd.xml'
repomdurl_dst = baseurl_dst + 'repodata/repomd.xml'

# Retrieve the repomd files
try:
	repomd_src = get_repomd(repomdurl_src)
	repomd_dst = get_repomd(repomdurl_dst)
except (requests.exceptions.HTTPError, requests.exceptions.MissingSchema) as e:
	print "Fatal Error:", e
	sys.exit(1)

# Parse our repomd files
try:
	repomddata_src = parse_repomd(repomd_src)
except ET.ParseError as e:
	print "Fatal Error: XML Parse Failure in", repomdurl_src + ":", e
	sys.exit(1)

try:
	repomddata_dst = parse_repomd(repomd_dst)
except ET.ParseError as e:
	print "Fatal Error: XML Parse Failure in", repomdurl_dst + ":", e
	sys.exit(1)

# Locate our primary metadata urls within the repomd data
try:
	primarymdurl_src = baseurl_src + repomddata_src['primary']
except KeyError as e:
	print "Fatal Error: Unable to locate primary metadata within:", repomdurl_src
	sys.exit(1)

try:
	primarymdurl_dst = baseurl_dst + repomddata_dst['primary']
except KeyError as e:
	print "Fatal Error: Unable to locate primary metadata within:", repomdurl_dst
	sys.exit(1)

# Retrieve the primary metadata files
try:
	primarymd_src = get_primarymd(primarymdurl_src)
	primarymd_dst = get_primarymd(primarymdurl_dst)
except (requests.exceptions.HTTPError, requests.exceptions.MissingSchema) as e:
	print "Fatal Error:", e
	sys.exit(1)

rpmdiff = {}

if not args.quick:
	try:
		rpmdata_src = parse_primarymd(primarymd_src)
	except ET.ParseError as e:
		print "Fatal Error: XML Parse Failure in", primarymdurl_src + ":", e

	try:
		rpmdata_dst = parse_primarymd(primarymd_dst)
	except ET.ParseError as e:
		print "Fatal Error: XML Parse Failure in", primarymdurl_dst + ":", e

	found_diff_brief = False
	for name, versions in rpmdata_src.items():
		if found_diff_brief:
			break

		if name in rpmdata_dst:
			for version in versions:
				if not version in rpmdata_dst[name]:
					if args.brief:
						rpmdiff['synced'] = False
						found_diff_brief = True
						break
					else:
						rpmdiff_set(rpmdiff, name, 'upgraded_src', version)

			for version in rpmdata_dst[name]:
				if not version in rpmdata_src[name]:
					if args.brief:
						rpmdiff['synced'] = False
						found_diff_brief = True
						break
					else:
						rpmdiff_set(rpmdiff, name, 'upgraded_dst', version)

		# package was removed
		else:
			for version in versions:
				if args.brief:
					rpmdiff['synced'] = False
					found_diff_brief = True
					break
				else:
					rpmdiff_set(rpmdiff, name, 'removed', version)

	for name, versions in rpmdata_dst.items():
		if found_diff_brief:
			break

		if not name in rpmdata_src:
			for version in versions:
				if args.brief:
					rpmdiff['synced'] = False
					found_diff_brief = True
					break
				else:
					rpmdiff_set(rpmdiff, name, 'added', version)

	if args.brief and not found_diff_brief:
		rpmdiff['synced'] = True
else:
	sha_src = hashlib.sha256(primarymd_src).hexdigest()
	sha_dst = hashlib.sha256(primarymd_dst).hexdigest()

	if sha_src == sha_dst:
		rpmdiff['synced'] = True
	else:
		rpmdiff['synced'] = False

print json.dumps(rpmdiff)
