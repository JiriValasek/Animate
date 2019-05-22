# -*- coding: utf-8 -*-
"""
Created on Fri May 17 22:25:12 2019

@author: jirka
"""
import FreeCAD
from bisect import bisect
from pivy import coin

class AnimationTrajectory:
	""" 
	AnimationTrajectory is a Proxy object made to be connected to 
	`Part::FeaturePython` AnimationTrajectory object. 
	Use makeAnimationTrajectory() to do that together with connecting a 
	ViewProvider Proxy (recommended) or do:
	
	>>> a=FreeCAD.ActiveDocument.addObject("App::FeaturePython",
									       "AnimationTrajectory")
	>>> AnimationTrajectory(a)
	"""
	
	def __init__(self, fp):
		"""
		__init__(self, fp)
		
		Initialization method for AnimationTrajectory. A class instance is
		created and made a `Proxy` for a generic `Part::FeaturePython` object. 
		During initialization number of properties are specified and preset 
		if necessary.
		
		Parameters
		----------
		fp : Part::FeaturePython AnimationTrajectory object
			`fp` is a generic barebone instance made to extended. 
		"""
		# add (and preset) properties
		fp.addProperty("App::PropertyLinkList","AnimatedObjects","General",
						"Objects that will be animated.")
		fp.addProperty("App::PropertyBool","Interpolate","General",
						"Interpolate trajectory between timestamps."
						).Interpolate = True
		fp.addProperty("App::PropertyBool","ReceiveUpdates","General",
						"Should this object receive updates from a server."
						).ReceiveUpdates = True
		fp.addProperty("App::PropertyFloat","Time","General",
						"Animation time in seconds.").Time = 0
		
		fp.addProperty("App::PropertyFloatList","Timestamps","Trajectory",
						"Timestamps at which we define\n" +
						"translation and rotation.")
		fp.addProperty("App::PropertyFloatList","TranslationX","Trajectory",
						"Object translation along global X direction.")
		fp.addProperty("App::PropertyFloatList","TranslationY","Trajectory",
						"Object translation along global Y direction.")
		fp.addProperty("App::PropertyFloatList","TranslationZ","Trajectory",
						"Object translation along global Z direction.")
		
		fp.addProperty("App::PropertyFloatList","RotationPointX",
						"Trajectory",
						"Object rotation point X coordinate.")
		fp.addProperty("App::PropertyFloatList","RotationPointY",
						"Trajectory",
						"Object rotation point Y coordinate.")
		fp.addProperty("App::PropertyFloatList","RotationPointZ",
						"Trajectory",
						"Object rotation point Z coordinate.")
		
		fp.addProperty("App::PropertyFloatList","RotationAxisX",
						"Trajectory", "Object rotation axis component X.")
		fp.addProperty("App::PropertyFloatList","RotationAxisY",
						"Trajectory", "Object rotation axis component Y.")
		fp.addProperty("App::PropertyFloatList","RotationAxisZ",
						"Trajectory", "Object rotation axis component Z.")
		fp.addProperty("App::PropertyFloatList","RotationAngle","Trajectory",
						"Rotation angle in degrees.")
		
		fp.addProperty("App::PropertyBool","ValidTrajectory","General",
						"This property records if trajectory was changed."
						).ValidTrajectory = False
						
		fp.addProperty("App::PropertyPlacement","Placement","Base",
						"Current palacement for animated objects")
		# make some properties read-only
		fp.setEditorMode("Placement", 1)
		
		# hide some properties
		fp.setEditorMode("ValidTrajectory", 2)
		fp.Proxy = self
		

	def onChanged(self, fp, prop):
		"""
		onChanged(self, fp, prop)
		
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
		execute(self, fp)
		
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
			
			
	# supporting methods-------------------------------------------------------
	def change_trajectory(self, fp, traj):
		"""
		change_trajectory(self, fp, traj)
		
		Changes trajectory for animated object.
		
		Parameters
		----------
		fp : Part::FeaturePython AnimationTrajectory object
			`fp` is an object to which trajectory should be changed.
		traj : dict
			`traj` must be a dictionary with keys "RotationAngle", 
			"RotationAxisX", "RotationAxisY", "RotationAxisZ", 
			"RotationPointX", "RotationPointY", "RotationPointZ", 
			"TranslationX", "TranslationY", "TranslationZ" and "Timestamps".
			All these keys must be paired with lists of a same length.
		"""
		# check that trajectory has a correct format
		if self.is_ValidTrajectory(traj):
			fp.RotationAngle = traj["RotationAngle"]
			fp.RotationAxisX = traj["RotationAxisX"]
			fp.RotationAxisY = traj["RotationAxisY"]
			fp.RotationAxisZ = traj["RotationAxisZ"]
			fp.RotationPointX = traj["RotationPointX"]
			fp.RotationPointY = traj["RotationPointY"]
			fp.RotationPointZ = traj["RotationPointZ"]
			fp.TranslationX = traj["TranslationX"]
			fp.TranslationY = traj["TranslationY"]
			fp.TranslationZ = traj["TranslationZ"]
			fp.Timestamps = traj["Timestamps"]
		else:	
			FreeCAD.Console.PrintError("Invalid trajectory!")


	def is_trajectory_property(self, prop):
		"""
		is_trajectory_property(self, prop)
		
		Checks if a `prop` property is a `Trajectory` group property.
		
		Parameters
		----------
		prop : String
			Property string such as `Placement`(not a `Trajectory` group
			property) or `RotationPointX`(is a `Trajectory` proup property).
			
		Returns
		-------
		bool
			`True` if `prop` belong between `Trajectory` properties and `False`
			otherwise.
		"""		
		return prop in ["Timestamps","TranslationX","TranslationY",
						"TranslationZ","RotationPointX","RotationPointY",
						"RotationPointZ","RotationAxisX","RotationAxisY",
						"RotationAxisZ","RotationAngle"]


	def is_ValidTrajectory(self, x):
		"""
		is_ValidTrajectory(self, x)
		
		Checks if a `x` dictionary is a valid trajectory.
		
		Parameters
		----------
		x : Dictionary
			Valid dictionary must be a dictionary with keys "RotationAngle", 
			"RotationAxisX", "RotationAxisY", "RotationAxisZ", 
			"RotationPointX", "RotationPointY", "RotationPointZ", 
			"TranslationX", "TranslationY", "TranslationZ" and "Timestamps".
			All these keys must be paired with lists of a same length.
			
		Returns
		-------
		bool
			`True` if `x` has everything valid trajectory should and `False`
			otherwise.
		"""
		# check all keys are included and record lengths of their lists
		list_lengths = []
		for key in ["Timestamps","TranslationX","TranslationY",
					"TranslationZ","RotationPointX","RotationPointY",
					"RotationPointZ","RotationAxisX","RotationAxisY",
					"RotationAxisZ","RotationAngle"]:
			if key in x.keys():
				list_lengths.append(len(x[key]))
			else:
				FreeCAD.Console.PrintWarning("Trajectory misses key" + 
											 key + ".\n")
				return False
			
		# check that lists for all keys have the same length
		if any([l != list_lengths[0] for l in list_lengths]):
			FreeCAD.Console.PrintWarning("Trajectory has lists " +
										 "with inconsistent lengths.\n")
			return False
		
		# check timestamps correspond to list of increasing values
		if any([x["Timestamps"][i] >=  x["Timestamps"][i+1] 
				for i in range(len(x["Timestamps"])-1)]):
			FreeCAD.Console.PrintWarning("Trajectory 'Timestamps' is not " + 
										 "list of increasing values.\n")
			return False
		else:
			return True
	
	def find_timestamp_indices_and_weights(self, fp):
		""" 
		find_timestamp_indices_and_weights(self, fp)
		
		Finds indices and weights for current `Time` in `Timestamp` list 
		so that current pose can be computed. Both `Time` and `Timestamp` are 
		properties in `fp`.
		
		Parameters
		----------
		fp : Part::FeaturePython AnimationTrajectory object
			`fp` is an object in which we need to find `Timestamp` list 
			indices corresponding (just before and after) to current `Time`.
			
		Returns
		-------
		indices : Integer List
			Indices which are necessary to compute a pose from the trajectory. 
			Example: If time is 1.2s and timestamps are equidistantly spaced 
			after 0.5s, then the first and second index will correspond to 1s 
			and 1.5s respectively.
		weights : Float List
			Weights to be used while computing pose from two successive poses 
			whether it's by interpolation or not. 
		"""
		# retrieve  indices corresponding to current time 
		# time before an animation
		if fp.Time <= fp.Timestamps[0]:
			indices = [0,0]
			weights = [1,0]
		
		# time after an animation
		elif fp.Time >= fp.Timestamps[-1]:
			indices = [-1,-1]
			weights = [1,0]
		
		# time during an animation
		else: 
			indices = [bisect(fp.Timestamps,fp.Time)]
			indices.insert(0,indices[0]-1)
			weights = [fp.Timestamps[indices[1]]-fp.Time,
					   fp.Time-fp.Timestamps[indices[0]]]	
			if not fp.Interpolate:
				if  weights[0] > weights[1]:
					weights = [1,0]
				else:
					weights = [0,1]
			else:
				weights = [weights[0]/sum(weights), weights[1]/sum(weights)]
				
		return indices, weights
		
		


class ViewProviderAnimationTrajectory:
	""" 
	ViewProviderAnimationTrajectory is a Proxy object made to be connected to 
	`Part::FeaturePython` AnimationTrajectory object's ViewObject. 
	Use makeAnimationTrajectory() to do that together with connecting a 
	AnimationTrajectory Proxy (recommended) or do:
	
	>>> a=FreeCAD.ActiveDocument.addObject("App::FeaturePython",
									       "AnimationTrajectory")
	>>> ViewProviderAnimationTrajectory(a.ViewObject)
	"""
	
	# standard methods---------------------------------------------------------   
	def __init__(self, vp):
		"""
		__init__(self, vp)
		
		Initialization method for AnimationTrajectory view provider. 
		A class instance is created and made a `Proxy` for a generic
		`Gui::ViewProviderDocumentObject` object. During initialization 
		number of properties are specified and preset if necessary.
		
		Parameters
		----------
		vp : ViewProviderDocumentObject
			View provider object `vp` should be a `ViewObject` belonging
			to `Part::FeaturePython` AnimationTrajectory object.
		"""
		vp.addProperty("App::PropertyBool","ShowFrame","Base",
					   "Show a frame for current pose.").ShowFrame = True
		vp.addProperty("App::PropertyPercent","FrameTransparency","Base",
					   "Transparency of the frame in percents."
					   ).FrameTransparency = 0
		vp.addProperty("App::PropertyBool","ShowArrowheads","Frame Look",
					   "Show arrowheads for frame axis arrow's."
					   ).ShowArrowheads = True
		vp.addProperty("App::PropertyFloatConstraint","ArrowheadLength",
					   "Frame Look", "Frame axis arrow's arrowhead length."
					   ).ArrowheadLength = (10,1.0,1e6,1.0)
		vp.addProperty("App::PropertyFloatConstraint","ArrowheadRadius",
					   "Frame Look", 
					   "Frame axis arrow's arrowhead bottom radius."
					   ).ArrowheadRadius = (5,0.5,1e6,0.5)
		vp.addProperty("App::PropertyFloatConstraint","ShaftLength",
					   "Frame Look", "Frame axis arrow's shaft length."
					   ).ShaftLength = (20,1.0,1e6,1)
		vp.addProperty("App::PropertyFloatConstraint","ShaftWidth",
					   "Frame Look", "Frame axis arrow's shaft width."
					   ).ShaftWidth = (4,1.0,64,1)

		# hide unnecessary view properties
		vp.setEditorMode("DisplayMode", 2)
		vp.setEditorMode("Visibility", 2)
		vp.Proxy = self
		

	def attach(self, vp):
		""" 
		attach(self, vp)
		
		Sets up the Inventor scene sub-graph of the view provider and then 
		calls onChanged for parameters from view table which are necessary
		for proper graphics (i.e. colors, lengths etc.)
		
		Parameters
		----------
		vp : ViewProviderDocumentObject
			View provider object to which this is a `Proxy`.
		"""		
		#TODO add text2D at the end of arrows/shafts, in the middle or to
		# a position which can be set from view menu ?	
		
		# make a generic shaft from 0 in Y direction
		shaft_vertices = coin.SoVertexProperty()
		shaft_vertices.vertex.setNum(2)
		shaft_vertices.vertex.set1Value(0,0,0,0)		
		self.shaft =  coin.SoLineSet()
		self.shaft.vertexProperty.setValue(shaft_vertices)
		self.shaft.numVertices.setNum(1)
		self.shaft.numVertices.setValue(2)
		
		# make a generic conic arrowhead oriented in Y axis direction and
		# move it at the end of the shaft
		trans_y = coin.SoTranslation()
		trans_y.setName("ArrowheadTranslation")
		arrowhead_cone = coin.SoCone()
		arrowhead_cone.setName("ArrowheadCone")
		self.arrowhead = coin.SoSwitch()
		self.arrowhead.addChild(trans_y)
		self.arrowhead.addChild(arrowhead_cone)
		
		# make rotations to rotate prepared shaft and arrowhead for Y axis
		# direction also to X and Z
		rot_y2x = coin.SoRotation()
		rot_y2x.rotation.setValue(coin.SbRotation(coin.SbVec3f(0,1,0),
												  coin.SbVec3f(1,0,0)))		
		rot_y2z = coin.SoRotation()
		rot_y2z.rotation.setValue(coin.SbRotation(coin.SbVec3f(0,1,0),
												  coin.SbVec3f(0,0,1)))
		
		# prepare colors for X,Y,Z which will correspond to R,G,B as customary
		self.color_x = coin.SoPackedColor()
		self.color_y = coin.SoPackedColor()
		self.color_z = coin.SoPackedColor()
				
		# make complete colored and rotated arrows
		x_arrow = coin.SoSeparator()
		x_arrow.addChild(rot_y2x)
		x_arrow.addChild(self.color_x)
		x_arrow.addChild(self.shaft)
		x_arrow.addChild(self.arrowhead)
		y_arrow = coin.SoSeparator()
		y_arrow.addChild(self.color_y)
		y_arrow.addChild(self.shaft)
		y_arrow.addChild(self.arrowhead)
		z_arrow = coin.SoSeparator()
		z_arrow.addChild(rot_y2z)
		z_arrow.addChild(self.color_z)
		z_arrow.addChild(self.shaft)
		z_arrow.addChild(self.arrowhead)
		
		# prepare transformation to keep pose corresponding to placement
		self.transform_object2world = coin.SoTransform()
		
		# prepare draw style to control shaft width
		self.drawstyle = coin.SoDrawStyle()
		
		# make complete frame and it to shaded display mode
		self.shaded = coin.SoGroup()
		self.shaded.addChild(self.transform_object2world)
		self.shaded.addChild(self.drawstyle)
		self.shaded.addChild(x_arrow)
		self.shaded.addChild(y_arrow)
		self.shaded.addChild(z_arrow)
		vp.addDisplayMode(self.shaded,"Shaded")
				
		# set up all parameters for the scene sub-graph
		self.onChanged(vp,"ShowFrame")
		self.onChanged(vp,"FrameTransparency")
		self.onChanged(vp,"ShaftLength")
		self.onChanged(vp,"ShaftWidth")
		self.onChanged(vp,"ArrowheadLength")
		self.onChanged(vp,"ArrowheadRadius")
		self.onChanged(vp,"ShowArrowheads")
		
	def onChanged(self, vp, prop):
		""" 
		onChanged(self, vp, prop)
		
		Event handler for a property change in View table. The change is
		relayed to be reflected in Inventor scene sub-graph.
		
		Parameters
		----------
		vp : ViewProviderDocumentObject
			View provider object to which this is a `Proxy`.
		prop : String
			`prop` is a name of a changed property.
		"""
		# relay changes from view table propertie to coin's SoNodes fields
		if prop == "ShowFrame":
			if vp.ShowFrame:
				vp.show()
			else:
				vp.hide()
		elif prop == "FrameTransparency":
			self.color_x.orderedRGBA.\
				setValue(0xff0000ff - (0xff*vp.FrameTransparency)//100)
			self.color_y.orderedRGBA.\
				setValue(0x00ff00ff - (0xff*vp.FrameTransparency)//100)
			self.color_z.orderedRGBA.\
				setValue(0x0000ffff - (0xff*vp.FrameTransparency)//100)
		elif prop == "ShaftLength" and hasattr(vp, "ArrowheadLength"):
			self.shaft.vertexProperty.getValue().vertex.\
				set1Value(1,0,vp.ShaftLength,0)
			self.arrowhead.getByName("ArrowheadTranslation").translation.\
				setValue(0,vp.ShaftLength + vp.ArrowheadLength/2,0)
		elif prop == "ShaftWidth":
			self.drawstyle.lineWidth.setValue(vp.ShaftWidth)
		elif prop == "ArrowheadLength" and hasattr(vp, "ShaftLength"):
			self.arrowhead.getByName("ArrowheadCone").height.\
				setValue(vp.ArrowheadLength)
			self.arrowhead.getByName("ArrowheadTranslation").translation.\
				setValue(0,vp.ShaftLength + vp.ArrowheadLength/2,0)
		elif prop == "ArrowheadRadius":
			self.arrowhead.getByName("ArrowheadCone").bottomRadius.\
				setValue(vp.ArrowheadRadius)
		elif prop == "ShowArrowheads":
			if vp.ShowArrowheads:
				self.arrowhead.whichChild.setValue(coin.SO_SWITCH_ALL)
			else:
				self.arrowhead.whichChild.setValue(coin.SO_SWITCH_NONE)
		
	def updateData(self, fp, prop):
		""" 
		updateData(self, fp, prop)
		
		Event handler for a property change in Data table. The change is
		relayed to be reflected in Inventor scene sub-graph.
		
		Parameters
		----------
		fp : Part::FeaturePython AnimationTrajectory object
			`fp` is an object which property has changed.
		prop : String
			`prop` is a name of a changed property.
		"""
		# keep the frame pose to correspond with placement property
		if prop == "Placement":
			self.transform_object2world.rotation.setValue(
					fp.Placement.Rotation.Q)
			self.transform_object2world.translation.setValue(
					fp.Placement.Base)

	def getDisplayModes(self,obj):
		"""
		getDisplayModes(self,obj)
		
		Return a list of display modes.
		"""
		modes=[]
		modes.append("Shaded")
		return modes

	def getDefaultDisplayMode(self):
		"""
		getDefaultDisplayMode(self)
		
		Return the name of the default display mode. 
		It must be defined in getDisplayModes. 
		"""
		return "Shaded"

	def setDisplayMode(self, mode):
		"""
		setDisplayMode(self, mode)
		
		Map the display mode defined in attach with those defined 
		in getDisplayModes. Since they have the same names nothing needs to
		be done. This method is optional.
		"""
		return mode
				

	def getIcon(self):
		""" 
		getIcon(self)
		
		Get the icon in XMP format which will appear in the tree view.
		"""
		return  \
		"""
		/* XPM */ 
		static const unsigned char * ViewProviderAnimationTrajectory_xpm[] = {
		"16 16 15 1",
		" 	c None",
		"!	c black",
		"#	c #6C6C6C",
		"$	c #C0C0C0",
		"%	c white",
		"&	c #5D0000",
		"'	c #3E0000",
		"(	c #090909",
		")	c #7C0000",
		"*	c #9B0000",
		"+	c #BA0000",
		",	c #D90000",
		"-	c #0000FF",
		".	c #FF2424",
		"0	c #F00000",
		"!!!!!!!!#$$$$$$$",
		"!%%%%%%%%&&&''($",
		"!%%%%%))))%%%%%#",
		"!%%%**)%%%%%%%%!",
		"!%%**%%%%%%%%%%!",
		"!%%%**%%%%%%%%%!",
		"!%%%%**++%%%%%%!",
		"!%%%%%%%++++,%%#",
		"!%%!!%%%%%%+,,,$",
		"#%!--!.%%%%%%%,,",
		"$!----!...00%0,,",
		"!------!...000,$",
		"!------!...00,%#",
		"$!----!...00%%%!",
		"#%!--!.%%%%%%%%!",
		"!#$!!$$#!!!!!!!!"};
		"""

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

		
def makeAnimationTrajectory():
	"""
	makeAnimationTrajectory()
	
	Makes a complete AnimationTrajectory object in currently active document.
	"""
	a=FreeCAD.ActiveDocument.addObject("App::FeaturePython",
									   "AnimationTrajectory")
	AnimationTrajectory(a)
	ViewProviderAnimationTrajectory(a.ViewObject)


makeAnimationTrajectory()
at = FreeCAD.ActiveDocument.AnimationTrajectory
traj = {}
traj["RotationAngle"] = [0,360,720]
traj["RotationAxisX"] = [1,0,0]
traj["RotationAxisY"] = [0,1,0]
traj["RotationAxisZ"] = [0,0,1]
traj["RotationPointX"] = [0,-5,-5]
traj["RotationPointY"] = [0,0,-5]
traj["RotationPointZ"] = [0,0,0]
traj["TranslationX"] = [0,10,20]
traj["TranslationY"] = [0,10,20]
traj["TranslationZ"] = [0,10,20]
traj["Timestamps"] = [0,10,20]
at.Proxy.change_trajectory(at,traj)