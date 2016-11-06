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
import json
import re
import StringIO
import time
import xml.etree.ElementTree as ET

from urlgrabber import urlread

def parse_repomd(url):
	xmldata = ET.fromstring(urlread(url))
	for mdelem in xmldata.iter('{http://linux.duke.edu/metadata/repo}data'):
		if mdelem.attrib['type'] != 'primary':
			continue

		for tag in mdelem:
			if tag.tag == '{http://linux.duke.edu/metadata/repo}location':
				return tag.attrib['href']

	return None

def parse_primarymd(url):
	rpmdata = {}
	primarymdcontent = urlread(url)

	# decompress if necessary
	if re.search('\.gz$', url):
		primarymdcontentgz = StringIO.StringIO(primarymdcontent)
		with gzip.GzipFile(fileobj=primarymdcontentgz) as f:
			primarymdcontent = f.read()

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

print json.dumps(rpmdiff)
