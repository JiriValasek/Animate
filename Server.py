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

import FreeCAD, FreeCADGui
import communication as com

from PySide2.QtWidgets import QMessageBox
from os import path

_PATH_ICONS = path.join(FreeCAD.getHomePath(),"Mod","Animate","Resources",
						"Icons")


class ServersDocumentObserver:
	
	featurepython_proxy = None
	target_doc = None
	
	def __init__(self, fp_proxy):
		self.featurepython_proxy = fp_proxy
		
	def slotDeletedDocument(self, doc):
		if doc == self.target_doc:
			self.featurepython_proxy.onDocumentClosed()

class Server: 

	server = None	
	observer = None

	def __init__(self, fp):
		'''"App two point properties" '''
		self.setProperties(fp)
		fp.Proxy = self
			
		
	def onDocumentRestored(self,fp):
		self.setProperties(fp)
		fp.ViewObject.Proxy.setProperties(fp.ViewObject)
		
	def onDocumentClosed(self):
		if isinstance(self.server,com.Srv):
			FreeCAD.Console.PrintMessage("Closing server with it's document\n")
			self.server.close()
		
		
	def setProperties(self,fp):
		if not hasattr(fp,"Address"):
			fp.addProperty("App::PropertyString","Address","Server settings",
					       "Address address where the server will listen for connection.\n" + 
						   "Valid values are Addressv4 and Addressv6 addresses or 'localhost'."
						 ).Address = "localhost"
		if not hasattr(fp,"Port"):
			fp.addProperty("App::PropertyIntegerConstraint","Port","Server settings",
						 "Port where the server will listen for connections.\n" +
						 "Valid port numers are in range <0 | 65535>,\n" +
						 "but some may be already taken!"
						 ).Port = (54321,0,65535,1)
		if not hasattr(fp,"Running"):
			fp.addProperty("App::PropertyBool","Running","Server settings",
						 "If Server Running is true, then Server listens for new connections."
						 ).Running = False

		fp.setEditorMode("Placement",2)
		fp.setEditorMode("Running",1)
		
		if fp.Running:
			self.server = com.startServer(fp.Address, fp.Port)
			if self.server == com.INVALID_ADDRESS: 
				fp.ViewObject.Proxy._icon = path.join(_PATH_ICONS, 
													  "Server.xpm")
				QMessageBox.warning(None, 'Error while starting server',
							 "The address was not in supported format.")
				fp.Running = False
			elif self.server == com.PORT_OCCUPIED:
				fp.ViewObject.Proxy._icon = path.join(_PATH_ICONS, 
													  "Server.xpm")
				QMessageBox.warning(None, 'Error while starting server',
								    "The port requested is already occupied.")
				fp.Running = False
			else:
				fp.setEditorMode("Address", 1)
				fp.setEditorMode("Port", 1)
				fp.Running = True
				fp.ViewObject.Proxy._icon = path.join(_PATH_ICONS, 
													  "ServerRunning.xpm")
			
		self.observer = ServersDocumentObserver(self)
		FreeCAD.addDocumentObserver(self.observer)
		self.observer.target_doc = FreeCAD.ActiveDocument
		
	def __getstate__(self):
		"""
		__getstate__(self)
		
		When saving the document this object gets stored using Python's
		cPickle module. Since we have some un-pickable here -- the Coin
		stuff -- we must define this method to return a tuple of all pickable 
		objects or None.
		"""
		# necessary to avoid JSON Serializable errors while trying to autosave
		# server and documentobserver
		return None

	def __setstate__(self,state):
		"""
		__setstate__(self,state)
		
		When restoring the pickled object from document we have the chance 
		to set some internals here. Since no data were pickled nothing needs
		to be done here.
		"""
		# necessary to avoid JSON Serializable errors while trying to autosave
		# server and documentobserver
		return None

class ViewProviderServer:
	
	_icon = path.join(_PATH_ICONS, "Server.xpm")
	
	def __init__(self, vp):
		''' Set this object to the proxy object of the actual view provider '''
		self.setProperties(vp)
			
	def onDelete(self, vp, subelements):
		if vp.Object.Running:
			FreeCAD.Console.PrintMessage("Deleting server safely.\n")
			vp.Object.Proxy.server.close()
		return True

	def doubleClicked(self, vp):
		if not vp.Object.Running:
			vp.Object.Proxy.server = com.startServer(vp.Object.Address, vp.Object.Port)
			if isinstance(vp.Object.Proxy.server,int):
				if vp.Object.Proxy.server == com.INVALID_ADDRESS: 
					QMessageBox.warning(None, 'Error while starting server',
							 "The address was not in supported format.")
				elif vp.Object.Proxy.server == com.PORT_OCCUPIED:
					QMessageBox.warning(None, 'Error while starting server',
								    "The port requested is already occupied.")
			else:
				vp.Object.setEditorMode("Address", 1)
				vp.Object.setEditorMode("Port", 1)
				vp.Object.Running = True
				self._icon = path.join(_PATH_ICONS, "ServerRunning.xpm")
		elif vp.Object.Running:
			vp.Object.Proxy.server.close()
			vp.Object.setEditorMode("Address", 0)
			vp.Object.setEditorMode("Port",0)
			vp.Object.Running = False
			self._icon = path.join(_PATH_ICONS, "Server.xpm")
		
		FreeCAD.Console.PrintLog("Server is running: " + str(vp.Object.Running) + " and icon is " + str(self._icon))
		vp.Object.touch()
		return True
	
	
	def setupContextMenu(self, vp, menu):
		menu.clear()
		if vp.Object.Running:	 
			action = menu.addAction("Disconnect Server")
			action.triggered.connect(lambda f=self.doubleClicked, arg=vp:f(arg))
		else:
			action = menu.addAction("Connect Server")
			action.triggered.connect(lambda f=self.doubleClicked, arg=vp:f(arg))

	def getIcon(self):
		""" 
		getIcon(self)
		
		Get the icon in XMP format which will appear in the tree view.
		"""
		return  self._icon

	def __getstate__(self):
		"""
		__getstate__(self)
		
		When saving the document this object gets stored using Python's
		cPickle module. Since we have some un-pickable here -- the Coin
		stuff -- we must define this method to return a tuple of all pickable 
		objects or None.
		"""
		return None

	def __setstate__(self,state):
		"""
		__setstate__(self,state)
		
		When restoring the pickled object from document we have the chance 
		to set some internals here. Since no data were pickled nothing needs
		to be done here.
		"""
		return None
	
	def setProperties(self,vp):
		vp.setEditorMode("AngularDeflection", 2)
		vp.setEditorMode("BoundingBox", 2)
		vp.setEditorMode("Deviation", 2)
		vp.setEditorMode("DisplayMode", 2)
		vp.setEditorMode("DrawStyle", 2)
		vp.setEditorMode("Lighting", 2)
		vp.setEditorMode("LineColor", 2)
		vp.setEditorMode("LineWidth", 2)
		vp.setEditorMode("PointColor", 2)
		vp.setEditorMode("PointSize", 2)
		vp.setEditorMode("Selectable", 2)
		vp.setEditorMode("SelectionStyle", 2)
		vp.setEditorMode("ShapeColor", 2)
		vp.setEditorMode("Transparency", 2)
		vp.setEditorMode("Visibility", 2)
		vp.Proxy = self
		
		if vp.Object.Running:
			self._icon = path.join(_PATH_ICONS, "ServerRunning.xpm")
		else:
			self._icon = path.join(_PATH_ICONS,"Server.xpm")
	


class ServerCommand(object):
	"""Create Object command"""

	def GetResources(self):
		return {'Pixmap'  : path.join(_PATH_ICONS, "ServerCmd.xpm") ,
            'MenuText': " Server" ,
            'ToolTip' : "Create Server instance."}
 
	def Activated(self):
		doc = FreeCAD.ActiveDocument
		a=doc.addObject("Part::FeaturePython","Server")
		Server(a)
		if FreeCAD.GuiUp:
			ViewProviderServer(a.ViewObject)
		doc.recompute()
		return
   
	def IsActive(self):
		if FreeCAD.ActiveDocument == None:
			return False
		else:
			return True

	def getHelp(self):
		return ["This is help for  Server\n",
				"and it needs to be written."]
		
if FreeCAD.GuiUp:
	FreeCADGui.addCommand('ServerCommand',ServerCommand())