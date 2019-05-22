# -*- coding: utf-8 -*-
"""
Created on Tue May 21 23:23:30 2019

@author: jirka
"""

import FreeCAD

class AnimationControl: 

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
		fp : Part::FeaturePython AnimationTrajectory object
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
		fp : Part::FeaturePython AnimationTrajectory object
			`fp` is an object which property has changed.
		"""
		pass

class ViewProviderAnimationControl:
	
	def __init__(self, obj):
		''' Set this object to the proxy object of the actual view provider '''
		obj.Proxy = self

	def getDefaultDisplayMode(self):
		''' Return the name of the default display mode. It must be defined in getDisplayModes. '''
		return "Flat Lines"

a=FreeCAD.ActiveDocument.addObject("Part::FeaturePython","AnimationControl")
AnimationControl(a)
ViewProviderAnimationControl(a.ViewObject)
App.ActiveDocument.recompute()