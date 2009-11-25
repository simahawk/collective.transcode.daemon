#!/usr/bin/env python
# encoding: utf-8
"""
xmlrpc.py

Created by unweb.me <we@unweb.me>. on 2009-11-02. 
Based on Darksnow ConvertDaemon by Jean-Nicolas Bès <jean.nicolas.bes@darksnow.org>
Copyright (c) 2009 unweb.me

# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

"""

"""
$Id$
"""

import os
import xmlrpclib
from twisted.internet import reactor
from twisted.web2 import xmlrpc
from scheduler import Job

def hex(bytes):
    hexbytes = ""
    for c in bytes:
        hexbytes += "%02x" % ord(c)
    return hexbytes

def unhex(hexbytes):
    bytes = ""
    for i in xrange(len(hexbytes)/2):
        bytes+= "%c" % int(hexbytes[i*2:i*2+2])
    return bytes

class XMLRPCConvert(xmlrpc.XMLRPC):
    
    def __init__(self, master):
        self.allowNone = True
        self.master = master
    
    def xmlrpc_getAvailableProfiles(self, request):
	ret = [i['id'] for i in self.master.config['profiles']]
	print ret
	return ret

    def xmlrpc_convert(self,  request, input, profileId, options, callbackURL):
        inURL = input['path']
	videofolder = self.master.config['videofolder']
	splittedURL = inURL.split('/')[2:]
	path = videofolder + '/' + '/'.join(splittedURL) + '/' + profileId
	try:
	    os.makedirs(path)
	except:
	    pass	
	outFile = path + '/' + '.'.join(inURL.split('/')[-1].split('.')[:-1]) + '.flv'
        output = dict(path=outFile,type='video/x-flv')
	profile = None
	for p in self.master.config['profiles']:
            if profileId == p['id']: profile = p	
	if not profile:
            return "ERROR: Invalid profile %s" % profileId
	
	if input['type'] not in profile['supported_mime_types']:
	    return "ERROR: Unsupported mimetype %s. Profile %s supports only %s" % (input['type'], profileId, profile['supported_mime_types'])
        job = Job(input, output, profile, options, callbackURL=callbackURL)
        job.defer.addCallback(self.callback, job)
        job.defer.addErrback(self.errback, job)
        jobid = self.master.addjob(job)
        if not jobid:
            return "ERROR couldn't get a jobid"
        if callbackURL:
            return hex(jobid)
        else:
            return job.defer
    
    def xmlrpc_stat(self, request, UJId):
        return "ok"
    
    def xmlrpc_stop(self, request):
        reactor.callLater(0.1, self.master.stop)
        return True
    
    def xmlrpc_cancel(self, request, UJId):
        self.master.delJob(UJId)
        return True
    
    def callback(self, ret, job):
        print "called back!"
        print "callbackURL =",job['callbackURL']
        server=xmlrpclib.Server(job['callbackURL'])
        server.conv_done_xmlrpc(ret)
        return True

    def errback(self, ret, job):
        print "errored back!"
        print "callbackURL =",job['callbackURL']
        server=xmlrpclib.Server(job['callbackURL'])
        server.conv_done_xmlrpc(ret)
        return True

