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
from PySide2.QtCore import Qt
from os import path

_PATH_ICONS = path.join(FreeCAD.getHomePath(),"Mod","Animate","Resources",
						"Icons")


class Server: 

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
						 "If Server Running is true, then Server listens for new connections."
						 ).Running = False
		obj.Proxy = self

		obj.setEditorMode("Placement",2)
		obj.setEditorMode("Running",1)
			

class ViewProviderServer:
	
	_icon = None
	
	def __init__(self, vp):
		''' Set this object to the proxy object of the actual view provider '''
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
			

	def getDefaultDisplayMode(self):
		''' Return the name of the default display mode. It must be defined in getDisplayModes. '''
		return "Flat Lines"

	
	def doubleClicked(self, vp):
		if not vp.Object.Running:
			vp.Object.Proxy.server = com.startServer(vp.Object.Address, vp.Object.Port)
			if isinstance(vp.Object.Proxy.server,int):
				if vp.Object.Proxy.server == com.INVALID_ADDRESS: 
					diag = QMessageBox(QMessageBox.Warning, 'Error while starting server',
							 "The address was not in supported format.")
					diag.setWindowModality(Qt.ApplicationModal)
					diag.exec()
				elif vp.Object.Proxy.server == com.PORT_OCCUPIED:
					diag = QMessageBox(QMessageBox.Warning, 'Error while starting server',
							 "The port requested is already occupied.")
					diag.setWindowModality(Qt.ApplicationModal)
					diag.exec()
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
			FreeCAD.ActiveDocument.recompute()
		return True
	
	def setupContextMenu(self, menu):
		FreeCAD.Console.PrintLog("Setup called for " + str(menu) + "\n")
		pass
			
	def getIcon(self):
		""" 
		getIcon(self)
		
		Get the icon in XMP format which will appear in the tree view.
		"""
		return  self._icon
	


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