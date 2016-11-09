#!/usr/bin/env python
#
# rpmrepodiff.py
#	Tool for diffing RPM repositories
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
import time
import xml.etree.ElementTree as ET

import requests

def parse_repomd(url):
	r = requests.get(url)
	if r.status_code != 200:
		raise Exception('Error retrieving "' + url + '": Code ' + str(r.status_code))

	xmldata = ET.fromstring(r.content)
	for mdelem in xmldata.iter('{http://linux.duke.edu/metadata/repo}data'):
		if mdelem.attrib['type'] != 'primary':
			continue

		for tag in mdelem:
			if tag.tag == '{http://linux.duke.edu/metadata/repo}location':
				return tag.attrib['href']

	return None

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

def parse_primarymd(url):
	rpmdata = {}
	primarymdcontent = get_primarymd(url)

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
parser.add_argument('-s', dest='source', nargs=1, required=True, help='Source Repo URL')
parser.add_argument('-d', dest='dest', nargs=1, required=True, help='Dest Repo URL')
parser.add_argument('-q', action='store_true', dest='quick', help='Quick mode.  Determines sync status but not differences')
args = parser.parse_args()

baseurl_src = args.source[0]
baseurl_dst = args.dest[0]

repomdurl_src = baseurl_src + 'repodata/repomd.xml'
repomdurl_dst = baseurl_dst + 'repodata/repomd.xml'

primarymd_src_info = parse_repomd(repomdurl_src)
primarymd_dst_info = parse_repomd(repomdurl_dst)

primarymd_src = baseurl_src + parse_repomd(repomdurl_src)
primarymd_dst = baseurl_dst + parse_repomd(repomdurl_dst)

rpmdiff = {}

if not args.quick:
	rpmdata_src = parse_primarymd(primarymd_src)
	rpmdata_dst = parse_primarymd(primarymd_dst)

	for name, versions in rpmdata_src.items():
		if name in rpmdata_dst:
			for version in versions:
				if not version in rpmdata_dst[name]:
					rpmdiff_set(rpmdiff, name, 'upgraded_src', version)
			for version in rpmdata_dst[name]:
				if not version in rpmdata_src[name]:
					rpmdiff_set(rpmdiff, name, 'upgraded_dst', version)
		# package was removed
		else:
			for version in versions:
				rpmdiff_set(rpmdiff, name, 'removed', version)

	for name, versions in rpmdata_dst.items():
		if not name in rpmdata_src:
			for version in versions:
				rpmdiff_set(rpmdiff, name, 'added', version)
else:
	sha_src = hashlib.sha256(get_primarymd(primarymd_src)).hexdigest()
	sha_dst = hashlib.sha256(get_primarymd(primarymd_dst)).hexdigest()

	if sha_src == sha_dst:
		rpmdiff['synced'] = True
	else:
		rpmdiff['synced'] = False

print json.dumps(rpmdiff)
