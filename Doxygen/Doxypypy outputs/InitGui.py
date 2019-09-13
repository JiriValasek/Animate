# -*- coding: utf-8 -*-

# ***************************************************************************
# *                                                                         *
# *   Animate workbench - FreeCAD Workbench for lightweight animation       *
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

##@package InitGui
#This module is used by FreeCAD to add the `Animate` workbench.
#
#When the module is imported by FreeCAD, the `Animate` workbench class is added
#to FreeCAD Gui. The `Animate` class encapsulates all necessary workbench
#behavior and changes to the FreeCAD Gui.
#

import FreeCAD
import FreeCADGui


## @brief Animate workbench class according to the PythonWorkbench template.
#
#This class represents the workbench in the FreeCAD Gui i.e. it imports
#commands, shows them on a toolbar and in a menu when workbench is activated.
#It contains information to make and item in the workbench toolbar listbox.
#
#
#

class Animate(FreeCADGui.Workbench):

    ## @property		Icon
    # A path to an image to be shown on the workbench toolbar.

    ## @property		MenuText
    # A str text to be shown in the listbox on the workbench toolbar.

    ## @property		ToolTip
    # A str tooltip for the `Animate` workbench.

    ## @property		list
    # A list of str which are the names of imported commands.

    ## @brief Initialization method for `Animate` workbench.
    #
    #A class instance is created, an static attributes `Icon`, `MenuText` and
    #`ToolTip` are added to the class. The `Icon` is a path to an image to be shown
    #on the workbench toolbar. The `MenuText` is a str text to be shown in
    #the listbox on the workbench toolbar. The `ToolTip` is a str tooltip
    #for the `Animate` workbench.
    #

    def __init__(self):
        import os
        self.__class__.Icon = os.path.join(FreeCAD.getHomePath(), "Mod",
                                           "Animate", "Resources", "Icons",
                                           "Animate.xpm")
        self.__class__.MenuText = "Animate"
        self.__class__.ToolTip = "Animation workbench"

    ## @brief Method used to setup workbench upon being selected on the workbench toolbar.
    #
    #This function is executed when user clicks on `Animate` workbench in
    #the workbench listbox situated on the workbench toolbar. After that commands
    #are added to the FreeCAD Gui by importing their modules. The names
    #of imported commands are then saved in the `list` attribute.
    #Afterwards a toolbar and a menu with some of those commands are created.
    #

    def Initialize(self):
        # import here all the needed files that create your FreeCAD commands
        import Server
        import Control
        import Trajectory
        import CollisionDetector
        # A list of command names created in the line above
        self.list = ["ServerCommand", "ControlCommand", "TrajectoryCommand",
                     "CollisionDetectorCommand"]
        # creates a new toolbar with your commands
        self.appendToolbar("Animate", self.list)
        # creates a new menu
        self.appendMenu("Animate", self.list)
        # appends a submenu to an existing menu
        # self.appendMenu(["An existing Menu","My submenu"], self.sublist)

    ## @brief This function is executed when the workbench is activated.
    #
    #For now it's used just to inform a user about the fact via console message.
    #

    def Activated(self):
        FreeCAD.Console.PrintMessage("Animate workbench activated\n")

    ## @brief This function is executed when the workbench is deactivated.
    #
    #For now it's used just to inform a user about the fact via console message.
    #

    def Deactivated(self):
        FreeCAD.Console.PrintMessage("Animate workbench deactivated\n")

    ## @brief Method to add custom commands to a context menu with respect to a recipient.
    #
    #This method is executed whenever the user right-clicks in a Tree View or the
    #View box. It's possible to only add commands via `self.appendContextMenu()`.
    #
    #
    # @param		recipient	A str equal to "Tree" or "View" according to where user clicked.
    #

    def ContextMenu(self, recipient):
        # Log who is the recipient
        # FreeCAD.Console.PrintLog("Preparing context menu for " + recipient
        #                          + "\n")
        # Add commands to the context menu if necessary
        # self.appendContextMenu("My commands", self.list)
        pass

    ## @brief Mandatory method for full python workbenches.
    #
    # @return
    #    A str with C++ binding class for this workbench.
    #

    def GetClassName(self):
        return "Gui::PythonWorkbench"


FreeCADGui.addWorkbench(Animate())
