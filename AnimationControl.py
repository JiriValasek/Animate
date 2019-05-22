# -*- coding: utf-8 -*-
"""
Created on Tue May 21 23:23:30 2019

@author: jirka
"""

import FreeCAD

class AnimationControl:
	
    def __init__(self, obj):
         '''"App two point properties" '''
         obj.addProperty("App::PropertyFloatConstrained","StartTime","Timing",
						 "Animation start time."
						 ).StartTime = (0,-float("inf"),10,0.5)
         obj.addProperty("App::PropertyFloatConstrained","StopTime","Timing",
						 "Animation stop time."
						 ).StopTime = (10,0,float("inf"),0.5)
         obj.addProperty("App::PropertyFloatConstrained","StepTime","Timing",
						 "Animation step time."
						 ).StopTime = (0.5,0.01,10,0.01)
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
		if self.is_trajectory_property(prop):
			traj = {}
			traj["RotationAngle"] = fp.RotationAngle
			traj["RotationAxisX"] = fp.RotationAxisX
			traj["RotationAxisY"] = fp.RotationAxisY
			traj["RotationAxisZ"] = fp.RotationAxisZ
			traj["RotationPointX"] = fp.RotationPointX
			traj["RotationPointY"] = fp.RotationPointY
			traj["RotationPointZ"] = fp.RotationPointZ
			traj["TranslationX"] = fp.TranslationX
			traj["TranslationY"] = fp.TranslationY
			traj["TranslationZ"] = fp.TranslationZ
			traj["Timestamps"] = fp.Timestamps
			traj_valid = self.is_ValidTrajectory(traj)
			if traj_valid != fp.ValidTrajectory :
				fp.ValidTrajectory = traj_valid
				
		# update placement according to current time and trajectory and go 
		# to self.execute (by calling fp.recompute)
		if prop != "Placement" and \
		   hasattr(fp,"ValidTrajectory") and fp.ValidTrajectory:
			indices,weights = self.find_timestamp_indices_and_weights(fp)
			fp.Placement = FreeCAD.Placement(
							FreeCAD.Vector(
								weights[0]*fp.TranslationX[indices[0]] + 
								weights[1]*fp.TranslationX[indices[1]],
								weights[0]*fp.TranslationY[indices[0]] + 
								weights[1]*fp.TranslationY[indices[1]],
								weights[0]*fp.TranslationZ[indices[0]] + 
								weights[1]*fp.TranslationZ[indices[1]]),
							FreeCAD.Rotation(FreeCAD.Vector(
								weights[0]*fp.RotationAxisX[indices[0]] + 
								weights[1]*fp.RotationAxisX[indices[1]],
								weights[0]*fp.RotationAxisY[indices[0]] + 
								weights[1]*fp.RotationAxisY[indices[1]],
								weights[0]*fp.RotationAxisZ[indices[0]] + 
								weights[1]*fp.RotationAxisZ[indices[1]]),
								weights[0]*fp.RotationAngle[indices[0]] + 
								weights[1]*fp.RotationAngle[indices[1]]),
							FreeCAD.Vector(
								weights[0]*fp.RotationPointX[indices[0]] + 
								weights[1]*fp.RotationPointX[indices[1]],
								weights[0]*fp.RotationPointY[indices[0]] + 
								weights[1]*fp.RotationPointY[indices[1]],
								weights[0]*fp.RotationPointZ[indices[0]] + 
								weights[1]*fp.RotationPointZ[indices[1]]))
			fp.recompute()		
			
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
		# Check that there is an object to animate
		if not hasattr(fp,"AnimatedObjects") or len(fp.AnimatedObjects) == 0:
			FreeCAD.Console.PrintWarning(fp.Name + ".execute(): " +
										 "Select objects to animate.\n")
			return
		
		# Check that current trajectory has valid format
		if not fp.ValidTrajectory:			
			FreeCAD.Console.PrintWarning(fp.Name + ".execute(): Trajectory " +
										 "is not in a valid format.\n")
			return
		
		# display animated objects in a pose specified by the trajectory and 
		# current time 
		for o in fp.AnimatedObjects:
			o.Placement = fp.Placement
			o.recompute()

class ViewProviderLine:
   def __init__(self, obj):
      ''' Set this object to the proxy object of the actual view provider '''
      obj.Proxy = self

   def getDefaultDisplayMode(self):
      ''' Return the name of the default display mode. It must be defined in getDisplayModes. '''
      return "Flat Lines"

a=FreeCAD.ActiveDocument.addObject("Part::FeaturePython","Line")
Line(a)
ViewProviderLine(a.ViewObject)
App.ActiveDocument.recompute()