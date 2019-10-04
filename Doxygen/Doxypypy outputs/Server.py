# -*- coding: utf-8 -*-

# ***************************************************************************
# *                                                                         *
# *   Animate workbench - FreeCAD Workbench for lightweigh animation        *
# *   Copyright (c) 2019 Jiří Valášek jirka362@gmail.com                    *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful,            *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Lesser General Public License for more details.                   *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with FreeCAD; if not, write to the Free Software        *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************/

##@package Server
#Classes related to the Server component of the Animate Workbench.
#
#The classes in this module provide funcionality for a `FeaturePython` Server
#instance (except an interprocess communication which is in the `communication`
#module) and creates a command to be used in a workbench.
#

import FreeCAD
import FreeCADGui
import communication as com

from PySide2.QtWidgets import QMessageBox
from os import path

## Path to a folder with the necessary icons.
PATH_TO_ICONS = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                          "Icons")


## @brief Proxy class for a `FeaturePython` Server instance.
#
#A ServerProxy instance adds properties to a `FeaturePython` Server
#instance and responds to theirs changes. It provides a communication.
#CommandServer `cmd_server` when `Running` is set to True by double-clicking on
#it in the Tree View or right clicking and selecting *Connect Server* option
#from context menu. It closes the `cmd_server` when `Running` is set to False or
#an `AnimateDocumentObserver` detects that a document with Server instance is
#closing
#
#Because communication.CommandServer `cmd_server` occupies a `Port` at selected
#`Address`, you cannot have duplicit Servers running simultaneously in a file,
#a FreeCAD window nor on one computer.
#
#
#
#To connect this `Proxy` object to a `FeaturePython` Server do:
#
# @code
#        a = FreeCAD.ActiveDocument.addObject("App::FeaturePython", "Server")
#        ServerProxy(a)
#

class ServerProxy(object):

    ## @property		cmd_server
    # A CommandServer instance to handle external commands.

    cmd_server = None

    ## @brief Initialization method for ServerProxy.
    #
    #A class instance is created and made a `Proxy` for a generic `FeaturePython`
    #Server object. During initialization number of properties are specified and
    #preset.
    #
    #
    # @param		fp	A barebone `FeaturePython` Server object to be extended.
    #

    def __init__(self, fp):
        self.setProperties(fp)
        fp.Proxy = self

    ## @brief Method called when document is restored to make sure everything is as it was.
    #
    # 	Reinitialization	it creates properties and sets them to
    #default values, if they were not restored automatically. It restarts a
    #cmd_server if it was running when document was closed. Properties of
    #connected `ViewObject` are also recreated and reset if necessary.
    #
    #
    # @param		fp	A restored `FeaturePython` Server object.
    #

    def onDocumentRestored(self, fp):
        self.setProperties(fp)
        fp.ViewObject.Proxy.setProperties(fp.ViewObject)

    #Method called by `AnimateDocumentObserver` when document with this class
    #instance is closing.
    #
    #This method is to be called from ServersDocumentObserver so that
    #the `Port` is freed when document is closed.
    #

    def onDocumentClosed(self):
        # Check there is a cmd_server to close and close it
        if isinstance(self.cmd_server, com.CommandServer):
            FreeCAD.Console.PrintMessage("Closing server with it's document\n")
            self.cmd_server.close()

    ## @brief Method to set properties during initialization or document restoration.
    #
    #The properties are set if they are not already present. Constrained properties
    #have their boundaries reset even if present, because constrains are not saved.
    #Also `cmd_server` is restarted if it was running previously and
    #an `AnimateDocumentObserver` is recreated.
    #
    #
    # @param		fp	A restored or barebone `FeaturePython` Server object.
    #

    def setProperties(self, fp):
        # Check properties are present and create them if not
        if not hasattr(fp, "Address"):
            fp.addProperty("App::PropertyString", "Address", "Server settings",
                           "IP address where the server will listen for "
                           + "connection.\nValid values are IPv4 and "
                           + "IPv6 addresses or 'localhost'string."
                           ).Address = "localhost"
        if not hasattr(fp, "Port"):
            fp.addProperty("App::PropertyIntegerConstraint", "Port",
                           "Server settings", "Port where the server will "
                           + "listen for connections.\n" +
                           "Valid port numers are in range <0 | 65535>,\n"
                           + "but some may be already taken!"
                           ).Port = (54321, 0, 65535, 1)
        else:
            fp.Port = (fp.Port, 0, 65535, 1)
        if not hasattr(fp, "Running"):
            fp.addProperty("App::PropertyBool", "Running", "Server settings",
                           "If Server Running is true, then Server listens "
                           + "for new connections."
                           ).Running = False

        # hide Placement property as there is nothing to display/move
        fp.setEditorMode("Placement", 2)
        # make Running property read-only as it's set from context menu/
        # by double clicking
        fp.setEditorMode("Running", 1)

        # try to start cmd_server, if it was running before closing
        if fp.Running:
            self.cmd_server = com.startServer(fp.Address, fp.Port)
            if self.cmd_server == com.SERVER_ERROR_INVALID_ADDRESS:
                fp.ViewObject.Proxy._icon = path.join(PATH_TO_ICONS,
                                                      "Server.xpm")
                QMessageBox.warning(None, 'Error while starting server',
                                    "The address was not in supported format.")
                fp.Running = False
            elif self.cmd_server == com.SERVER_ERROR_PORT_OCCUPIED:
                fp.ViewObject.Proxy._icon = path.join(PATH_TO_ICONS,
                                                      "Server.xpm")
                QMessageBox.warning(None, 'Error while starting server',
                                    "The port requested is already occupied.")
                fp.Running = False
            else:
                fp.setEditorMode("Address", 1)
                fp.setEditorMode("Port", 1)
                fp.Running = True
                fp.ViewObject.Proxy._icon = path.join(PATH_TO_ICONS,
                                                      "ServerRunning.xpm")

        # Make an document observer to be notified when document will be closed
        import AnimateDocumentObserver
        AnimateDocumentObserver.addObserver()
        FreeCAD.animate_observer.addServerToNotify(self,
                                                   FreeCAD.ActiveDocument.Name)

    ## @brief Necessary method to avoid errors when trying to save unserializable objects.
    #
    #This method is used by JSON to serialize unserializable objects during
    #autosave. Without this an Error would rise when JSON would try to do
    #that itself.
    #
    #We need this for unserializable `cmd_server` attribute, but we don't
    #serialize them, because it's enough to reset it when object is restored.
    #
    # @return
    #    None, because we don't serialize anything.
    #

    def __getstate__(self):
        return None

    ## @brief Necessary method to avoid errors when trying to restore unserializable objects.
    #
    #This method is used during a document restoration. We need this for
    #unserializable `cmd_server` attribute, but we do not restore it,
    #because it's enough to reset them from saved parameters.
    #
    # @return
    #    None, because we don't restore anything.
    #

    def __setstate__(self, state):
        return None


## @brief Proxy class for a `Gui.ViewProviderDocumentObject` Server.ViewObject.
#
#A ViewProviderServerProxy instance changes a `FeaturePython` Server's icon in
#the Tree view to show if Server is `Running` or not. It also closes/starts
#ServerProxy's `cmd_server` if the `FeaturePython` is double-clicked, deleted or
#chosen to be connected/disconnected through its context view. The context view
#is also provided by this class.
#
#
#
#To connect this `Proxy` object to a `Gui.ViewProviderDocumentObject`
#Server.ViewObject do:
#
# @code
#        a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Server")
#        ViewProviderServerProxy(a.ViewObject)
#

class ViewProviderServerProxy(object):

    ## @property		_icon
    # A path to the icon image to be displayed in the Tree View.

    ## @var _icon
    # @hideinitializer
    # @protected
    _icon = path.join(PATH_TO_ICONS, "Server.xpm")

    ## @brief Initialization method for ViewProviderServerProxy.
    #
    #A class instance is created and made a `Proxy` for a generic
    #`Gui.ViewProviderDocumentObject` Server.ViewObject. This method selects
    # appropriate icon for `FeaturePython` Server and hides unnecessary unused
    # View properties.
    #
    #
    # @param		vp	A barebone `Gui.ViewProviderDocumentObject` Server.ViewObject.
    #

    def __init__(self, vp):
        self.setProperties(vp)
        vp.Proxy = self

    ## @brief Method called when `FeaturePython` Server is about to be deleted.
    #
    #This method is used to close ServerProxy's `cmd_server` as not to leave
    #a `Port` occupied.
    #
    #
    # @param		vp	A `Gui.ViewProviderDocumentObject` Server.ViewObject being closed.
    # @param		subelements	An unused argument from C++ binding.
    #
    # @return
    #    True to specify that it was implemented and executed.
    #

    def onDelete(self, vp, subelements):
        if vp.Object.Running:
            FreeCAD.Console.PrintMessage("Deleting server safely.\n")
            vp.Object.Proxy.cmd_server.close()
        return True

    ## @brief Method called when `FeaturePython` Server is double-clicked in the Tree View.
    #
    #This methods tries to start ServerProxy's `cmd_server` if it wasn't running and
    #closes it in the opposite case. It shows warning dialogs if something failed.
    #If action is successful, then the icon in the Tree View is changed
    #(You may need to recompute the document to see the change).
    #
    #
    #
    # @param		vp	A double-clicked `Gui.ViewProviderDocumentObject` Server.ViewObject.
    #
    # @return
    #    True to specify that it was implemented and executed.
    #

    def doubleClicked(self, vp):
        if not vp.Object.Running:
            vp.Object.Proxy.cmd_server = com.startServer(vp.Object.Address,
                                                         vp.Object.Port)
            if isinstance(vp.Object.Proxy.cmd_server, int):
                if vp.Object.Proxy.cmd_server == \
                        com.SERVER_ERROR_INVALID_ADDRESS:
                    QMessageBox.warning(None, 'Error while starting server',
                                        "The address was not in supported "
                                        + "format.")
                elif vp.Object.Proxy.cmd_server == \
                        com.SERVER_ERROR_PORT_OCCUPIED:
                    QMessageBox.warning(None, 'Error while starting server',
                                        "The port requested is already "
                                        + "occupied.")
            else:
                vp.Object.setEditorMode("Address", 1)
                vp.Object.setEditorMode("Port", 1)
                vp.Object.Running = True
                self._icon = path.join(PATH_TO_ICONS, "ServerRunning.xpm")
        elif vp.Object.Running:
            vp.Object.Proxy.cmd_server.close()
            vp.Object.setEditorMode("Address", 0)
            vp.Object.setEditorMode("Port", 0)
            vp.Object.Running = False
            self._icon = path.join(PATH_TO_ICONS, "Server.xpm")
        return True

    ## @brief Method called by the FreeCAD to customize a context menu for a Server.
    #
    #The *Transform* and *Set colors...* items are removed from the context menu
    #shown upon right click on `FeaturePython` Server in the Tree View.
    #The option to *Disconnect Server*, or *Connect Server* is added instead.
    #
    #
    # @param		vp	A right-clicked `Gui.ViewProviderDocumentObject` Server.ViewObject.
    # @param		menu	A Qt's QMenu to be edited.
    #

    def setupContextMenu(self, vp, menu):
        menu.clear()
        if vp.Object.Running:
            action = menu.addAction("Disconnect Server")
            action.triggered.connect(lambda f=self.doubleClicked,
                                     arg=vp: f(arg))
        else:
            action = menu.addAction("Connect Server")
            action.triggered.connect(lambda f=self.doubleClicked,
                                     arg=vp: f(arg))

    ## @brief Method used to get a path to an icon which will appear in the tree view.
    #
    # @return
    #    A path to the icon stored in `_icon`.
    #

    def getIcon(self):
        return self._icon

    ## @brief Method to hide properties and select appropriate icon to show it the Tree View.
    #
    #This method is called during initialization or document restoration. All unused
    #unnecessary view properties are hidden and icon is chosen in accordance with
    #ServerProxy's `Running` state.
    #
    #
    # @param		vp	A `Gui.ViewProviderDocumentObject` Server.ViewObject.
    #

    def setProperties(self, vp):
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

        if vp.Object.Running:
            self._icon = path.join(PATH_TO_ICONS, "ServerRunning.xpm")
        else:
            self._icon = path.join(PATH_TO_ICONS, "Server.xpm")


## @brief ServerCommand class specifing Animate workbench's Server button/command.
#
#This class provides resources for a toolbar button and a menu button.
#It controls their behaivor(Active/Inactive) and responds to callbacks after
#either of them was clicked(Activated).
#

class ServerCommand(object):

    ## @brief Method used by FreeCAD to retrieve resources to use for this command.
    #
    # @return
    #    A dict with items `PixMap`, `MenuText` and `ToolTip` which contain
    #    a path to a command icon, a text to be shown in a menu and
    #    a tooltip message.
    #

    def GetResources(self):
        return {'Pixmap': path.join(PATH_TO_ICONS, "ServerCmd.xpm"),
                'MenuText': "Server",
                'ToolTip': "Create Server instance."}

    ## @brief Method used as a callback when the toolbar button or the menu item is clicked.
    #
    #This method creates a Server instance in currently active document.
    #Afterwards it adds a ServerProxy as a `Proxy` to this instance as well as
    #ViewProviderServerProxy to its `ViewObject.Proxy`, if FreeCAD runs in the
    #Graphic mode.
    #

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        a = doc.addObject("Part::FeaturePython", "Server")
        ServerProxy(a)
        if FreeCAD.GuiUp:
            ViewProviderServerProxy(a.ViewObject)
        doc.recompute()

    ## @brief Method to specify when the toolbar button and the menu item are enabled.
    #
    #The toolbar button `Server` and menu item `Server` are set to be active only
    #when there is an active document in which a `FeaturePython` Server instance
    #can be created.
    #
    # @return
    #    True if buttons shall be enabled and False otherwise.
    #

    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            return True


if FreeCAD.GuiUp:
    # Add command to FreeCAD Gui when importing this module in InitGui
    FreeCADGui.addCommand('ServerCommand', ServerCommand())
