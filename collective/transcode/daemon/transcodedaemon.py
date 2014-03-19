#!/usr/bin/env python
# encoding: utf-8
"""
transcodedaemon.py

Created by unweb.me <we@unweb.me> on 2009-11-01.
Based on Darksnow ConvertDaemon by Jean-Nicolas Bès <jean.nicolas.bes@darksnow.org>
Copyright (c) 2009 unweb.me.

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

import os

from twisted.application import strports, service
from twisted.web import server, resource, static, http
from twisted.internet import reactor

from collective.transcode.daemon.xmlrpc import XMLRPCConvert
from collective.transcode.daemon.scheduler import JobSched

application = service.Application("TranscodeDaemon")

class TranscodeWebRoot(resource.Resource):
    def render(self, request):
        return "OK!"


class TranscodeDaemon(JobSched):

    @property
    def root(self):
        if "TRANSCODEDAEMON_ROOT" in os.environ.keys():
            return os.environ["TRANSCODEDAEMON_ROOT"]
        else:
            return os.getcwd()

    def rel(self, path):
        return os.path.join(self.root, path.lstrip('/'))

    def __init__(self, application):
        print "Initializing"
        JobSched.__init__(self)
        try:
            import imp
            config = imp.load_source('config',self.rel("config.py"))
        except:
            from collective.transcode.daemon import config
        self.config = {}
        self.config['profiles'] = eval(config.profiles)
        self.config['listen_host'] = config.listen_host
        self.config['listen_port'] = config.listen_port
        self.config['videofolder'] = config.videofolder
        self.config['secret'] = config.secret
        self.config['override_callback_url'] = config.override_callback_url or None

        self.launchHttp(application)
        reactor.callInThread(self.run)
        print "Launched TranscodeDaemon scheduler thread...."

        # Comment out the following to enable a Twisted SSH Manhole for debugging
        """
        from twisted.cred import portal, checkers
        from twisted.conch import manhole, manhole_ssh

        def getManholeFactory(namespace):
            realm = manhole_ssh.TerminalRealm()
            def getManhole(_):
                return manhole.Manhole(namespace)
            realm.chainedProtocolFactory.protocolFactory = getManhole
            p = portal.Portal(realm)
            p.registerChecker(checkers.InMemoryUsernamePasswordDatabaseDontUse(admin='foobar'))
            f = manhole_ssh.ConchFactory(p)
            return f
        reactor.listenTCP(2222, getManholeFactory({'self': self}))
        """

    def launchHttp(self, application):
        root = TranscodeWebRoot()
        root.putChild('', root)
        root.putChild('RPC2', XMLRPCConvert(self))
        root.putChild(self.config['videofolder'], static.File(self.config['videofolder'], defaultType='video/webm'))
        host = self.config['listen_host'].encode('ascii')
        port = self.config['listen_port'].encode('ascii')
        site = server.Site(root)

        thyStopFact = site.stopFactory
        def myStopFact():
            thyStopFact()
            self.stop(stopReactor=False)
        site.stopFactory = myStopFact

        self.service = strports.service('tcp:%s:interface=%s' % (port, host), site)
        self.service.setServiceParent(application)
        print "Launched http channel"

    def stop(self, stopReactor = True):
        self.running=False
        self.queue.put(None)
        if stopReactor:
            reactor.stop()
        print "reactor stopped"

    def __del__(self):
        if self.running:
            self.stop()

TranscodeDaemon(application)


