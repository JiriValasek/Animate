# -*- coding: utf-8 -*-
"""
Created on Sun Apr 21 13:47:29 2019

@author: jirka
"""
#!/usr/bin/env python

############################################################################
# 
#  Copyright (C) 2004-2005 Trolltech AS. All rights reserved.
# 
#  This file is part of the example classes of the Qt Toolkit.
# 
#  This file may be used under the terms of the GNU General Public
#  License version 2.0 as published by the Free Software Foundation
#  and appearing in the file LICENSE.GPL included in the packaging of
#  self file.  Please review the following information to ensure GNU
#  General Public Licensing requirements will be met:
#  http://www.trolltech.com/products/qt/opensource.html
# 
#  If you are unsure which license is appropriate for your use, please
#  review the following information:
#  http://www.trolltech.com/products/qt/licensing.html or contact the
#  sales department at sales@trolltech.com.
# 
#  This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
#  WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
# 
############################################################################

from PySide2 import QtCore, QtGui, QtNetwork

SIZEOF_UINT16 = 2
PORT = 8888


class Thd(QtCore.QThread):
	error = QtCore.Signal(QtNetwork.QTcpSocket.SocketError)
	cmd = QtCore.Signal(str)

	def __init__(self, socketDescriptor, parent):
		super(Thd, self).__init__(parent)
		# Get a QTcpSocket descriptor from the QTcpServer
		self.socketDescriptor = socketDescriptor

	def run(self):
		# Set a QTcpSocket 
		tcpSocket = QtNetwork.QTcpSocket()
		if not tcpSocket.setSocketDescriptor(self.socketDescriptor):
			self.error.emit(tcpSocket.error())
			return

		# instantiate a QByteArray
		block = QtCore.QByteArray()
		# QDataStream class provides serialization of binary data to a QIODevice
		out = QtCore.QDataStream(block, QtCore.QIODevice.ReadWrite)
		# We are using PyQt5 so set the QDataStream version accordingly.
		out.setVersion(QtCore.QDataStream.Qt_4_8)
		out.writeUInt16(0)
		# wait until the connection is ready to read
		tcpSocket.waitForReadyRead()
		# read incomming data
		instr = tcpSocket.readAll()
		# in this case we print to the terminal could update text of a widget if we wanted.
		try:
			self.cmd.emit(str(instr.data()))
			# confirmation response
			message = "DONE"
		except:
			# error response
			message = "FAILED"
		# get a byte array of the message encoded appropriately.
		message = message.encode()
		# now use the QDataStream and write the byte array to it.
		out.writeString(message)
		out.device().seek(0)
		out.writeUInt16(block.size() - 2)
		# get the connection ready for clean up
		tcpSocket.disconnected.connect(tcpSocket.deleteLater)
		# now send the QByteArray.
		tcpSocket.write(block)
		tcpSocket.waitForBytesWritten()
		# now disconnect connection.
		tcpSocket.disconnectFromHost()


@QtCore.Slot(str)
def execute_command(cmd):
	Msg("Executing external command: %s" % cmd)
	exec(cmd)


class Srv(QtNetwork.QTcpServer):
	def __init__(self, parent=None):
		super(Srv, self).__init__(parent)

	def incomingConnection(self, socketDescriptor):
		thread = Thd(socketDescriptor, self)
		thread.cmd.connect(execute_command)
		thread.finished.connect(thread.deleteLater)
		thread.start()

server = Srv()
address = QtNetwork.QHostAddress('127.0.0.1')
if not server.listen(address, PORT): #QtNetwork.QHostAddress("localhost"), PORT):
    Msg( "Unable to start the server: %s." % server.errorString())

Msg("The server is running on port %d.\n" % server.serverPort())
