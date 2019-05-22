# -*- coding: utf-8 -*-
"""
Created on Mon Apr 22 23:32:41 2019

@author: jirka
"""
import FreeCAD, FreeCADGui, Workbench


class AnimationServer(Workbench):
    
    MenuText = "Animation Server"
    ToolTip = "Creates animations based on external data."
    Icon =  """
            /* XPM */ 
            static const unsigned char * animationserver_xpm[] = {
            "16 16 11 1",
            " 	c None",
            "!	c white",
            "#	c #F8F8F8",
            "$	c #FF0000",
            "%	c #FFFBF0",
            "&	c #00BA00",
            "'	c #6DFF24",
            "(	c #00D900",
            ")	c black",
            "*	c #007C00",
            "+	c #EBEBEB",
            "!!!!!!!!!!!!!!!!",
            "###########$%$##",
            "##########$$$$$#",
            "##########$$$$$#",
            "#%&&&&&&&&$$$$$#",
            "#'((((((((($$$%#",
            "#'((()))(((($&%#",
            "#'((()(*)((($&%#",
            "#'((()((*)(($&%#",
            "#'((()(((*)($&%#",
            "#'((()((')(((&%#",
            "+'((()(')((((&%#",
            "#'((()))(((((&%#",
            "#''((((((((((&%#",
            "#%'''''''''''%%#",
            "################"};"""

    def Initialize(self):
        "This function is executed when FreeCAD starts"
        #import MyModuleA, MyModuleB # import here all the needed files that create your FreeCAD commands
        self.list = ["MyCommand1, MyCommand2"] # A list of command names created in the line above
        self.appendToolbar("My Commands",self.list) # creates a new toolbar with your commands
        self.appendMenu("My New Menu",self.list) # creates a new menu
        self.appendMenu(["An existing Menu","My submenu"],self.list) # appends a submenu to an existing menu

    def Activated(self):
        "This function is executed when the workbench is activated"
        Msg("Animation workbench activated\n")
        return

    def Deactivated(self):
        "This function is executed when the workbench is deactivated"
        Msg("Animation workbench deactivated\n")
        return

    def ContextMenu(self, recipient):
        "This is executed whenever the user right-clicks on screen"
        # "recipient" will be either "view" or "tree"
        self.appendContextMenu("My commands",self.list) # add commands to the context menu

    def GetClassName(self): 
        # this function is mandatory if this is a full python workbench
        return "Gui::PythonWorkbench"
       
Gui.addWorkbench(AnimationServer())