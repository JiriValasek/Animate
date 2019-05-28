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
# -*- coding: utf-8 -*-
"""
Created on Tue May 21 23:23:30 2019

@author: jirka
"""

#------------------------------------------====================================
# this should be moved to a different module for supporting classes

import FreeCAD
from PySide2.QtWidgets import QMessageBox
from PySide2.QtCore import Qt, QThread, QByteArray, QDataStream, QIODevice, Signal, Slot
from PySide2.QtNetwork import QTcpServer, QTcpSocket, QAbstractSocket, QHostAddress

SIZEOF_UINT16 = 2
PORT = 31313
INVALID_ADDRESS = 1
PORT_OCCUPIED = 2
WAIT_TIME_MS = 3000

class CommandThread(QThread):
	error = Signal(QTcpSocket.SocketError)
	cmd = Signal(str)

	def __init__(self, socketDescriptor, parent):
		super(CommandThread, self).__init__(parent)
		self.socketDescriptor = socketDescriptor
		self.blockSize = 0


	def run(self):
		tcpSocket = QTcpSocket()
		if not tcpSocket.setSocketDescriptor(self.socketDescriptor):
			self.error.emit(tcpSocket.error())
			return

		if not tcpSocket.waitForReadyRead(msecs=WAIT_TIME_MS):
			FreeCAD.Console.PrintError("No CMD\n")

		instr = QDataStream(tcpSocket)
		instr.setVersion(QDataStream.Qt_4_0)

		if self.blockSize == 0:
			if tcpSocket.bytesAvailable() < 2:
				return
			self.blockSize = instr.readUInt16()

		if tcpSocket.bytesAvailable() < self.blockSize:
			return

		instr = instr.readString()
		FreeCAD.Console.PrintLog("Server received> " + str(instr) + "\n")
		try:
			self.cmd.emit(str(instr))
			message = "DONE"
		except:
			message = "FAILED"
		FreeCAD.Console.PrintLog("Server sending> " + message + "\n")

		

		block = QByteArray()
		outstr = QDataStream(block, QIODevice.WriteOnly)
		outstr.setVersion(QDataStream.Qt_4_0)
		outstr.writeUInt16(0)
		outstr.writeQString(message)
		outstr.device().seek(0)
		outstr.writeUInt16(block.size() - 2)

		tcpSocket.write(block)
		tcpSocket.disconnectFromHost()
		tcpSocket.waitForDisconnected()



@Slot(str)
def execute_command(cmd):
	FreeCAD.Console.PrintWarning("Executing external command: %s" % cmd)
	try:
		exec(cmd)
	except:
		return False
	else:
		return True


class Srv(QTcpServer):
	def __init__(self, parent=None):
		super(Srv, self).__init__(parent)

	def incomingConnection(self, socketDescriptor):
		thread = CommandThread(socketDescriptor, self)
		thread.cmd.connect(execute_command)
		thread.finished.connect(thread.deleteLater)
		thread.start()

class Client:
	def __init__(self, HOST, PORT):
		self.host = HOST
		self.port = PORT
		self.tcpSocket = QTcpSocket()
		self.blockSize = 0

		self.tcpSocket.connectToHost(self.host, self.port, QIODevice.ReadWrite)
		if not self.tcpSocket.waitForConnected(msecs=WAIT_TIME_MS):
			FreeCAD.Console.PrintError("No connection\n")

		message = 'App.Console.PrintWarning("Finally\\n")\n'

		FreeCAD.Console.PrintMessage("Client sending> " + message + "\n")
		block = QByteArray()
		outstr = QDataStream(block, QIODevice.WriteOnly)
		outstr.setVersion(QDataStream.Qt_4_0)
		outstr.writeUInt16(0)
		outstr.writeQString(message)
		outstr.device().seek(0)
		outstr.writeUInt16(block.size() - 2)

		self.tcpSocket.write(block)
		if not self.tcpSocket.waitForBytesWritten(msecs=WAIT_TIME_MS):
			FreeCAD.Console.PrintError("Bytes not written\n")

		self.tcpSocket.readyRead.connect(self.dealCommunication)
		self.tcpSocket.error.connect(self.displayError)


	def dealCommunication(self):
		instr = QDataStream(self.tcpSocket)
		instr.setVersion(QDataStream.Qt_4_0)

		if self.blockSize == 0:
			if self.tcpSocket.bytesAvailable() < 2:
				return
			self.blockSize = instr.readUInt16()

		if self.tcpSocket.bytesAvailable() < self.blockSize:
			return

		FreeCAD.Console.PrintMessage("Client received> " + instr.readString() + "\n")

	def displayError(self, socketError):
		if socketError == QAbstractSocket.RemoteHostClosedError:
			pass
		else:
			print(self, "The following error occurred: %s." % self.tcpSocket.errorString())


def check_ip_valid(ip):
	if ip.upper() == "LOCALHOST":
		return True
	numbers = ip.split(".")
	if len(numbers) == 4:
		if all([(0 <= int(num) <=255) for num in numbers]):
			return  True
	return False

def startServer(addr, port):
	""" addr = IPv4 address string or localhost"""
	Msg ( str(addr) + "\n")

	if not check_ip_valid(addr):
		return INVALID_ADDRESS

	if addr.upper() == "LOCALHOST":
		addr = QHostAddress(QHostAddress.LocalHost)
	else:
		addr = QHostAddress(addr)
		
	server = Srv()
	if not server.listen(addr, port): 
		FreeCAD.Console.PrintLog( "Unable to start the server: %s.\n" % server.errorString())
		return PORT_OCCUPIED
	else:
		FreeCAD.Console.PrintLog("The server is running on port %d.\n" % server.serverPort())
		return server

#------------------------------------------====================================

import FreeCAD
from os import path

_PATH_RESOURCES = path.join(FreeCAD.getHomePath(),"Mod","Animate","Resources")

class AnimationServer: 

	updated = False
	server = None	

	def __init__(self, obj):
		'''"App two point properties" '''
		obj.addProperty("App::PropertyString","Address","Server settings",
						 "Address address where the server will listen for connection.\n" + 
						 "Valid values are Addressv4 and Addressv6 addresses or 'localhost'."
						 ).Address = "localhost"
		obj.addProperty("App::PropertyIntegerConstraint","Port","Server settings",
						 "Port where the server will listen for connections.\n" +
						 "Valid port numers are in range <0 | 65535>,\n" +
						 "but some may be already taken!"
						 ).Port = (54321,0,65535,1)
		obj.addProperty("App::PropertyBool","Running","Server settings",
						 "If Server Running is true, then AnimationServer listens for new connections."
						 ).Running = False
		obj.Proxy = self

		obj.setEditorMode("Placement",2)
		obj.setEditorMode("Running",1)
   
	def onChanged(self, fp, prop):
		"""
		Event handler for a property change in Data table. The property 
		value validity is checked here.
		
		We check if trajectory is valid and if it is, then we recompute
		current placement with accordance to time.
		
		Parameters
		----------
		fp : Part::FeaturePython AnimationTrajectory object
			`fp` is an object which property has changed.
		prop : String
			`prop` is a name of a changed property.
		"""
		# check that a trajectory has valid format
		pass
	
	def execute(self, fp):
		"""
		Event handler called to recompute the object after a property 
		was changed to new valid value (processed by onChange()). 
		
		We change the placement of connected parts/assemblies to agree with
		computed current placement.
		
		Parameters
		----------
		fp : Part::FeaturePython AnimationTrajectory object
			`fp` is an object which property has changed.
		"""
		pass
			

class ViewProviderAnimationServer:
	
	_icon = None
	
	def __init__(self, vp):
		''' Set this object to the proxy object of the actual view provider '''
		vp.Proxy = self
		
		if vp.Object.Running:
			self._icon = path.join(_PATH_RESOURCES,"Icons",
							       "AnimateServerRunning.xpm")
		else:
			self._icon = path.join(_PATH_RESOURCES,"Icons","AnimateServer.xpm")
			

	def getDefaultDisplayMode(self):
		''' Return the name of the default display mode. It must be defined in getDisplayModes. '''
		return "Flat Lines"

	
	def doubleClicked(self, vp):
		if not vp.Object.Running:
			vp.Object.Proxy.server = startServer(vp.Object.Address, vp.Object.Port)
			if isinstance(vp.Object.Proxy.server,int):
				if vp.Object.Proxy.server == INVALID_ADDRESS: 
					diag = QMessageBox(QMessageBox.Warning, 'Error while starting server',
							 "The address was not in supported format.")
					diag.setWindowModality(Qt.ApplicationModal)
					diag.exec()
				elif vp.Object.Proxy.server == PORT_OCCUPIED:
					diag = QMessageBox(QMessageBox.Warning, 'Error while starting server',
							 "The port requested is already occupied.")
					diag.setWindowModality(Qt.ApplicationModal)
					diag.exec()
			else:
				vp.Object.setEditorMode("Address", 1)
				vp.Object.setEditorMode("Port", 1)
				vp.Object.Running = True
				self._icon = path.join(_PATH_RESOURCES,"Icons",
								       "AnimateServerRunning.xpm")
		elif vp.Object.Running:
			vp.Object.setEditorMode("Address", 0)
			vp.Object.setEditorMode("Port",0)
			vp.Object.Running = False
			self._icon = path.join(_PATH_RESOURCES,"Icons","AnimateServer.xpm")
			
	def getIcon(self):
		""" 
		getIcon(self)
		
		Get the icon in XMP format which will appear in the tree view.
		"""
		return  self.icon
	


class AnimationServerCommand(object):
	"""Create Object command"""

	def GetResources(self):
		return {'Pixmap'  : path.join(_PATH_RESOURCES,"Icons",
									  "AnimateServerCmd.xpm") ,
            'MenuText': "Animation Server" ,
            'ToolTip' : "Create AnimationServer instance."}
 
	def Activated(self):
		doc = FreeCAD.ActiveDocument
		a=doc.addObject("Part::FeaturePython","AnimationServer")
		AnimationServer(a)
		if FreeCAD.GuiUp:
			ViewProviderAnimationServer(a.ViewObject)
		doc.recompute()
		return
   
	def IsActive(self):
		if FreeCAD.ActiveDocument == None:
			return False
		else:
			return True

	def getHelp(self):
		return ["This is help for Animation Server\n",
				"and it needs to be written."]