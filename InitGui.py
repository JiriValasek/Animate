# -*- coding: utf-8 -*-
"""
Created on Mon Apr 22 23:32:41 2019

@author: jirka
"""
import FreeCAD, FreeCADGui, Workbench
from os import path

class Animate(Workbench):
    "Animate workbench object"
	
    def __init__(self):
        self.__class__.Icon = path.join (FreeCAD.getResourceDir(), "Mod",
										 "Animate","Resources","Icons",
										 "Animate.xpm")
        self.__class__.MenuText = "Animate"
        self.__class__.ToolTip = "Animation workbench"
    

    def Initialize(self):
        "This function is executed when FreeCAD starts"
		# import here all the needed files that create your FreeCAD commands
        import AnimationServer, AnimationControl, AnimationTrajectory
		# A list of command names created in the line above
        self.list = ["AnimationServerCommand","AnimationControlCommand",
					 "AnimationTrajectoryCommand"]
		# creates a new toolbar with your commands
        self.appendToolbar("Animation Commands",self.list)
		# creates a new menu
        self.appendMenu("AnimationCommands",self.list)
		# appends a submenu to an existing menu
        #self.appendMenu(["An existing Menu","My submenu"],self.list)

    def Activated(self):
        "This function is executed when the workbench is activated"
        FreeCAD.Console.PrintMessage("Animation workbench activated\n")
        return

    def Deactivated(self):
        "This function is executed when the workbench is deactivated"
        FreeCAD.Console.PrintMessage("Animation workbench deactivated\n")
        return

    def ContextMenu(self, recipient):
        "This is executed whenever the user right-clicks on screen"
        # "recipient" will be either "view" or "tree"
        self.appendContextMenu("My commands",self.list) # add commands to the context menu

    def GetClassName(self): 
        # this function is mandatory if this is a full python workbench
        return "Gui::PythonWorkbench"
       
FreeCADGui.addWorkbench(Animate())