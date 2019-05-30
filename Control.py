# -*- coding: utf-8 -*-
"""
Created on Tue May 21 23:23:30 2019

@author: jirka
"""

import FreeCAD, FreeCADGui

from os import path

_PATH_ICONS = path.join(FreeCAD.getHomePath(),"Mod","Animate","Resources",
						"Icons")

class Control: 

	updated = False
	
	def __init__(self, obj):
		'''"App two point properties" '''
		obj.addProperty("App::PropertyFloatConstraint","StartTime","Timing",
						 "Animation start time. \nRange is < - inf | Stop Time - Step Time >."
						 ).StartTime = (0,-float("inf"),9.5,0.5)
		obj.addProperty("App::PropertyFloatConstraint","StepTime","Timing",
						 "Animation step time. \nRange is < 0.01 | Stop Time - Start Time >."
						 ).StepTime = (0.5,0.01,10,0.1)
		obj.addProperty("App::PropertyFloatConstraint","StopTime","Timing",
						 "Animation stop time. \nRange is < Start Time + Step Time | inf >."
						 ).StopTime = (10,0.5,float("inf"),0.5)
		obj.Proxy = self
   
	def onChanged(self, fp, prop):
		"""
		Event handler for a property change in Data table. The property 
		value validity is checked here.
		
		We check if trajectory is valid and if it is, then we recompute
		current placement with accordance to time.
		
		Parameters
		----------
		fp : Part::FeaturePython Trajectory object
			`fp` is an object which property has changed.
		prop : String
			`prop` is a name of a changed property.
		"""
		# check that a trajectory has valid format
		
		if self.updated:
			self.updated = False
		else:
			if prop == "StartTime":
				self.updated = True
				fp.StopTime = (fp.StopTime, fp.StartTime + fp.StepTime, float("inf"),
							   0.5)
				fp.StepTime = (fp.StepTime, 0.01, fp.StopTime - fp.StartTime, 0.1)
			elif prop == "StopTime":
				self.updated = True
				fp.StartTime = (fp.StartTime, -float("inf"), fp.StopTime - fp.StepTime, 
								0.5)
				fp.StepTime = (fp.StepTime, 0.01, fp.StopTime - fp.StartTime, 0.1)
			elif prop == "StepTime":
				self.updated = True
				fp.StopTime = (fp.StopTime, fp.StartTime + fp.StepTime, float("inf"), 0.5)
				self.updated = True
				fp.StartTime = (fp.StartTime, -float("inf"), fp.StopTime - fp.StepTime, 0.5)

			
	def execute(self, fp):
		"""
		Event handler called to recompute the object after a property 
		was changed to new valid value (processed by onChange()). 
		
		We change the placement of connected parts/assemblies to agree with
		computed current placement.
		
		Parameters
		----------
		fp : Part::FeaturePython Trajectory object
			`fp` is an object which property has changed.
		"""
		pass

class ViewProviderControl:
	
	def __init__(self, obj):
		''' Set this object to the proxy object of the actual view provider '''
		obj.setEditorMode("AngularDeflection", 2)
		obj.setEditorMode("BoundingBox", 2)
		obj.setEditorMode("Deviation", 2)
		obj.setEditorMode("DisplayMode", 2)
		obj.setEditorMode("DrawStyle", 2)
		obj.setEditorMode("Lighting", 2)
		obj.setEditorMode("LineColor", 2)
		obj.setEditorMode("LineWidth", 2)
		obj.setEditorMode("PointColor", 2)
		obj.setEditorMode("PointSize", 2)
		obj.setEditorMode("Selectable", 2)
		obj.setEditorMode("SelectionStyle", 2)
		obj.setEditorMode("ShapeColor", 2)
		obj.setEditorMode("Transparency", 2)
		obj.setEditorMode("Visibility", 2)
		obj.Proxy = self

	def getDefaultDisplayMode(self):
		''' Return the name of the default display mode. It must be defined in getDisplayModes. '''
		return None
	
	def getIcon(self):
		""" 
		getIcon(self)
		
		Get the icon in XMP format which will appear in the tree view.
		"""
		return path.join(_PATH_ICONS, "Control.xpm")


class ControlCommand(object):
	"""Create Object command"""

	def GetResources(self):
		return {'Pixmap'  : path.join(_PATH_ICONS, "ControlCmd.xpm") ,
            'MenuText': "Control" ,
            'ToolTip' : "Create Control instance."}
 
	def Activated(self):
		doc = FreeCAD.ActiveDocument
		a=doc.addObject("Part::FeaturePython","Control")
		Control(a)
		if FreeCAD.GuiUp:
			ViewProviderControl(a.ViewObject)
		doc.recompute()
		return
   
	def IsActive(self):
		if FreeCAD.ActiveDocument == None:
			return False
		else:
			return True

	def getHelp(self):
		return ["This is help for  Control\n",
				"and it needs to be written."]
		
if FreeCAD.GuiUp:
	FreeCADGui.addCommand('ControlCommand', ControlCommand())