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

"""
Created on Fri May 17 22:25:12 2019

@author: jirka
"""
import FreeCAD
import FreeCADGui

from bisect import bisect
from pivy import coin
from os import path


_PATH_ICONS = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                        "Icons")


class Trajectory:
    """
    Trajectory is a Proxy object made to be connected to
    `Part::FeaturePython` Trajectory object.

    To connect them use:

    >>> a=FreeCAD.ActiveDocument.addObject("App::FeaturePython",
                                           "Trajectory")
    >>> Trajectory(a)
    """

    def __init__(self, fp):
        """
        __init__(self, fp)

        Initialization method for Trajectory. A class instance is
        created and made a `Proxy` for a generic `Part::FeaturePython` object.
        During initialization number of properties are specified and preset
        if necessary.

        Parameters
        ----------
        fp : Part::FeaturePython Trajectory object
            `fp` is a generic barebone instance made to extended.
        """
        # add (and preset) properties
        self.setProperties(fp)
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
        fp : Part::FeaturePython Trajectory object
            `fp` is an object which property has changed.
        prop : String
            `prop` is a name of a changed property.
        """
        # don't react to changing Placement
        if prop == "Placement":
            return

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
            if traj_valid != fp.ValidTrajectory:
                fp.ValidTrajectory = traj_valid

        # update placement according to current time and trajectory and go
        # to self.execute (by calling fp.recompute)
        if hasattr(fp, "ValidTrajectory") and fp.ValidTrajectory and \
           hasattr(fp, "ParentFramePlacement") and \
           (self.is_trajectory_property(prop) or
           prop in ["Time", "Interpolate"]):
            indices, weights = self.find_timestamp_indices_and_weights(fp)
            fp.ObjectPlacement = FreeCAD.Placement(
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
            fp.Placement = fp.ParentFramePlacement.multiply(
                           fp.ObjectPlacement)
            # propagate the updates down the chain
            for child in fp.Group:
                child.ParentFramePlacement = fp.Placement
            # display animated objects in a pose specified by the trajectory
            # and current time
            for o in fp.AnimatedObjects:
                o.Placement = fp.Placement
                o.recompute()

        elif prop == "AnimatedObjects":
            # display animated objects in a pose specified by the trajectory
            # and current time
            for o in fp.AnimatedObjects:
                o.Placement = fp.Placement
                o.recompute()

        elif prop == "ParentFramePlacement" and hasattr(fp, "ObjectPlacement"):
            fp.Placement = fp.ParentFramePlacement.multiply(
                           fp.ObjectPlacement)
            # propagate the updates down the chain
            for child in fp.Group:
                child.ParentFramePlacement = fp.Placement
        # display animated objects in a pose specified by the trajectory and
        # current time
            for o in fp.AnimatedObjects:
                o.Placement = fp.Placement
                o.recompute()

    def execute(self, fp):
        """
        execute(self, fp)

        Event handler called to recompute the object after a property
        was changed to new valid value (processed by onChange()).

        We change the placement of connected parts/assemblies to agree with
        computed current placement.

        Parameters
        ----------
        fp : Part::FeaturePython Trajectory object
            `fp` is an object which property has changed.
        """
        # Check that there is an object to animate
        if not hasattr(fp, "AnimatedObjects") or len(fp.AnimatedObjects) == 0:
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
#        for o in fp.AnimatedObjects:
#            o.Placement = fp.Placement
#            o.recompute()
#            o.purgeTouched()

    def onDocumentRestored(self, fp):
        fp.ViewObject.Proxy.setProperties(fp.ViewObject)
        self.setProperties(fp)

    # supporting methods-------------------------------------------------------
    def setProperties(self, fp):
        # add (and preset) properties
        if not hasattr(fp, "ValidTrajectory"):
            fp.addProperty("App::PropertyBool", "ValidTrajectory", "General",
                           "This property records if trajectory was changed."
                           ).ValidTrajectory = False

        if not hasattr(fp, "AnimatedObjects"):
            fp.addProperty("App::PropertyLinkList", "AnimatedObjects",
                           "General", "Objects that will be animated.")
        if not hasattr(fp, "Interpolate"):
            fp.addProperty("App::PropertyBool", "Interpolate", "General",
                           "Interpolate trajectory between timestamps."
                           ).Interpolate = True
        if not hasattr(fp, "ReceiveUpdates"):
            fp.addProperty("App::PropertyBool", "ReceiveUpdates", "General",
                           "Should this object receive updates from a server."
                           ).ReceiveUpdates = True
        if not hasattr(fp, "Time"):
            fp.addProperty("App::PropertyFloat", "Time", "General",
                           "Animation time in seconds.").Time = 0

        if not hasattr(fp, "Timestamps"):
            fp.addProperty("App::PropertyFloatList", "Timestamps",
                           "Trajectory", "Timestamps at which we define\n" +
                           "translation and rotation.")
        if not hasattr(fp, "TranslationX"):
            fp.addProperty("App::PropertyFloatList", "TranslationX",
                           "Trajectory",
                           "Object translation along global X direction.")
        if not hasattr(fp, "TranslationY"):
            fp.addProperty("App::PropertyFloatList", "TranslationY",
                           "Trajectory",
                           "Object translation along global Y direction.")
        if not hasattr(fp, "TranslationZ"):
            fp.addProperty("App::PropertyFloatList", "TranslationZ",
                           "Trajectory",
                           "Object translation along global Z direction.")

        if not hasattr(fp, "RotationPointX"):
            fp.addProperty("App::PropertyFloatList", "RotationPointX",
                           "Trajectory",
                           "Object rotation point X coordinate.")
        if not hasattr(fp, "RotationPointY"):
            fp.addProperty("App::PropertyFloatList", "RotationPointY",
                           "Trajectory",
                           "Object rotation point Y coordinate.")
        if not hasattr(fp, "RotationPointZ"):
            fp.addProperty("App::PropertyFloatList", "RotationPointZ",
                           "Trajectory",
                           "Object rotation point Z coordinate.")

        if not hasattr(fp, "RotationAxisX"):
            fp.addProperty("App::PropertyFloatList", "RotationAxisX",
                           "Trajectory", "Object rotation axis component X.")
        if not hasattr(fp, "RotationAxisY"):
            fp.addProperty("App::PropertyFloatList", "RotationAxisY",
                           "Trajectory", "Object rotation axis component Y.")
        if not hasattr(fp, "RotationAxisZ"):
            fp.addProperty("App::PropertyFloatList", "RotationAxisZ",
                           "Trajectory", "Object rotation axis component Z.")
        if not hasattr(fp, "RotationAngle"):
            fp.addProperty("App::PropertyFloatList", "RotationAngle",
                           "Trajectory",
                           "Rotation angle in degrees.")

        if not hasattr(fp, "ShowFrame"):
            fp.addProperty("App::PropertyBool", "ShowFrame", "Frame",
                           "Show a frame for current pose."
                           ).ShowFrame = True
        if not hasattr(fp, "FrameTransparency"):
            fp.addProperty("App::PropertyPercent", "FrameTransparency",
                           "Frame", "Transparency of the frame in percents."
                           ).FrameTransparency = 0
        if not hasattr(fp, "ShowArrowheads"):
            fp.addProperty("App::PropertyBool", "ShowArrowheads", "Frame",
                           "Show arrowheads for frame axis arrow's."
                           ).ShowArrowheads = True
        if not hasattr(fp, "ArrowheadLength"):
            fp.addProperty("App::PropertyFloatConstraint", "ArrowheadLength",
                           "Frame", "Frame axis arrow's arrowhead length."
                           ).ArrowheadLength = (10, 1.0, 1e6, 1)
        else:
            fp.ArrowheadLength = (fp.ArrowheadLength, 1.0, 1e6, 1)
        if not hasattr(fp, "ArrowheadRadius"):
            fp.addProperty("App::PropertyFloatConstraint", "ArrowheadRadius",
                           "Frame",
                           "Frame axis arrow's arrowhead bottom radius."
                           ).ArrowheadRadius = (5, 0.5, 1e6, 0.5)
        else:
            fp.ArrowheadRadius = (fp.ArrowheadRadius, 0.5, 1e6, 0.5)
        if not hasattr(fp, "ShaftLength"):
            fp.addProperty("App::PropertyFloatConstraint", "ShaftLength",
                           "Frame", "Frame axis arrow's shaft length."
                           ).ShaftLength = (20, 1.0, 1e6, 1)
        else:
            fp.ShaftLength = (fp.ShaftLength, 1.0, 1e6, 1)
        if not hasattr(fp, "ShaftWidth"):
            fp.addProperty("App::PropertyFloatConstraint", "ShaftWidth",
                           "Frame", "Frame axis arrow's shaft width."
                           ).ShaftWidth = (4, 1.0, 64, 1)
        else:
            fp.ShaftWidth = (fp.ShaftWidth, 1.0, 64, 1)

        if not hasattr(fp, "Placement"):
            fp.addProperty("App::PropertyPlacement", "Placement", "Base",
                           "Current placement for animated objects in "
                           + "world frame.")

        if not hasattr(fp, "ParentFramePlacement"):
            fp.addProperty("App::PropertyPlacement", "ParentFramePlacement",
                           "General", "Current placement of a Parent Frame.")

        if not hasattr(fp, "ObjectPlacement"):
            fp.addProperty("App::PropertyPlacement", "ObjectPlacement",
                           "General",
                           "Current Object placement in a Parent Frame.")

        # make some properties read-only
        fp.setEditorMode("ObjectPlacement", 1)
        fp.setEditorMode("ParentFramePlacement", 1)

        # hide some properties
        fp.setEditorMode("Placement", 2)
        fp.setEditorMode("ValidTrajectory", 2)

    def change_trajectory(self, fp, traj):
        """
        change_trajectory(self, fp, traj)

        Changes trajectory for animated object.

        Parameters
        ----------
        fp : Part::FeaturePython Trajectory object
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
        return prop in ["Timestamps", "TranslationX", "TranslationY",
                        "TranslationZ", "RotationPointX", "RotationPointY",
                        "RotationPointZ", "RotationAxisX", "RotationAxisY",
                        "RotationAxisZ", "RotationAngle"]

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
        for key in ["Timestamps", "TranslationX", "TranslationY",
                    "TranslationZ", "RotationPointX", "RotationPointY",
                    "RotationPointZ", "RotationAxisX", "RotationAxisY",
                    "RotationAxisZ", "RotationAngle"]:
            if key in x.keys():
                list_lengths.append(len(x[key]))
            else:
                FreeCAD.Console.PrintWarning("Trajectory misses key" +
                                             key + ".\n")
                return False

        # check there no key has an empty list
        if 0 in list_lengths:
            FreeCAD.Console.PrintWarning("Trajectory has list/lists of " +
                                         "zero lengths.\n")
            return False

        # check that lists for all keys have the same length
        if any([len_ != list_lengths[0] for len_ in list_lengths]):
            FreeCAD.Console.PrintWarning("Trajectory has lists " +
                                         "with inconsistent lengths.\n")
            return False

        # check timestamps correspond to list of increasing values
        if any([x["Timestamps"][i] >= x["Timestamps"][i+1]
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
        fp : Part::FeaturePython Trajectory object
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
            indices = [0, 0]
            weights = [1, 0]

        # time after an animation
        elif fp.Time >= fp.Timestamps[-1]:
            indices = [-1, -1]
            weights = [1, 0]

        # time during an animation
        else:
            indices = [bisect(fp.Timestamps, fp.Time)]
            indices.insert(0, indices[0]-1)
            weights = [fp.Timestamps[indices[1]] - fp.Time,
                       fp.Time - fp.Timestamps[indices[0]]]
            if not fp.Interpolate:
                if weights[0] > weights[1]:
                    weights = [1, 0]
                else:
                    weights = [0, 1]
            else:
                weights = [weights[0]/sum(weights), weights[1]/sum(weights)]

        return indices, weights


class ViewProviderTrajectory:
    """
    ViewProviderTrajectory is a Proxy object made to be connected to
    `Part::FeaturePython` Trajectory object's ViewObject.

    To connect them use:

    >>> a=FreeCAD.ActiveDocument.addObject("App::FeaturePython",
                                           "Trajectory")
    >>> ViewProviderTrajectory(a.ViewObject)
    """

    # standard methods---------------------------------------------------------
    def __init__(self, vp):
        """
        __init__(self, vp)

        Initialization method for Trajectory view provider.
        A class instance is created and made a `Proxy` for a generic
        `Gui::ViewProviderDocumentObject` object. During initialization
        number of properties are specified and preset if necessary.

        Parameters
        ----------
        vp : ViewProviderDocumentObject
            View provider object `vp` should be a `ViewObject` belonging
            to `Part::FeaturePython` Trajectory object.
        """
        self.setProperties(vp)
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
        # TODO add text2D at the end of arrows/shafts, in the middle or to
        # a position which can be set from view menu ?

        # make a generic shaft from 0 in Y direction
        shaft_vertices = coin.SoVertexProperty()
        shaft_vertices.vertex.setNum(2)
        shaft_vertices.vertex.set1Value(0, 0, 0, 0)
        self.shaft = coin.SoLineSet()
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
        rot_y2x.rotation.setValue(coin.SbRotation(coin.SbVec3f(0, 1, 0),
                                                  coin.SbVec3f(1, 0, 0)))
        rot_y2z = coin.SoRotation()
        rot_y2z.rotation.setValue(coin.SbRotation(coin.SbVec3f(0, 1, 0),
                                                  coin.SbVec3f(0, 0, 1)))

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

        # prepare draw style to control shaft width
        self.drawstyle = coin.SoDrawStyle()

        # prepare transformation to keep pose corresponding to placement
        self.tf_object2world = coin.SoTransform()

        # make complete frame and it to shaded display mode
        self.frame = coin.SoSwitch()
        self.frame.addChild(self.tf_object2world)
        self.frame.addChild(self.drawstyle)
        self.frame.addChild(x_arrow)
        self.frame.addChild(y_arrow)
        self.frame.addChild(z_arrow)
        vp.RootNode.addChild(self.frame)

        vp.Object.Proxy.setProperties(vp.Object)
        self.setProperties(vp)
        self.Object = vp.Object

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
        if prop == "Visibility":
            # Make all children invisible
            FreeCAD.Console.PrintLog("Visibility altered\n")

    def updateData(self, fp, prop):
        """
        updateData(self, fp, prop)

        Event handler for a property change in Data table. The change is
        relayed to be reflected in Inventor scene sub-graph.

        Parameters
        ----------
        fp : Part::FeaturePython Trajectory object
            `fp` is an object which property has changed.
        prop : String
            `prop` is a name of a changed property.
        """
        if hasattr(fp, "ShowFrame"):
            if fp.ShowFrame:
                self.frame.whichChild.setValue(coin.SO_SWITCH_ALL)
            else:
                self.frame.whichChild.setValue(coin.SO_SWITCH_NONE)
        if hasattr(fp, "FrameTransparency"):
            self.color_x.orderedRGBA.\
                setValue(0xff0000ff - (0xff*fp.FrameTransparency)//100)
            self.color_y.orderedRGBA.\
                setValue(0x00ff00ff - (0xff*fp.FrameTransparency)//100)
            self.color_z.orderedRGBA.\
                setValue(0x0000ffff - (0xff*fp.FrameTransparency)//100)
        if hasattr(fp, "ShaftLength") and hasattr(fp, "ArrowheadLength"):
            self.shaft.vertexProperty.getValue().vertex.\
                set1Value(1, 0, fp.ShaftLength, 0)
            self.arrowhead.getByName("ArrowheadTranslation").translation.\
                setValue(0, fp.ShaftLength + fp.ArrowheadLength/2, 0)
            self.arrowhead.getByName("ArrowheadCone").height.\
                setValue(fp.ArrowheadLength)
        if hasattr(fp, "ShaftWidth"):
            self.drawstyle.lineWidth.setValue(fp.ShaftWidth)
        if hasattr(fp, "ArrowheadRadius"):
            self.arrowhead.getByName("ArrowheadCone").bottomRadius.\
                setValue(fp.ArrowheadRadius)
        if hasattr(fp, "ShowArrowheads"):
            if fp.ShowArrowheads:
                self.arrowhead.whichChild.setValue(coin.SO_SWITCH_ALL)
            else:
                self.arrowhead.whichChild.setValue(coin.SO_SWITCH_NONE)
        if hasattr(fp, "Placement"):
            trans = fp.Placement.Base
            rot = fp.Placement.Rotation
            self.tf_object2world.translation.setValue((trans.x, trans.y,
                                                       trans.z))
            self.tf_object2world.rotation.setValue(rot.Q)

    def canDropObject(self, obj):

        if hasattr(obj, "Proxy") and \
           isinstance(obj.Proxy, self.Object.Proxy.__class__):
            return True
        return False

    def getIcon(self):
        """
        getIcon(self)

        Get the icon in XMP format which will appear in the tree view.
        """
        return path.join(_PATH_ICONS, "Trajectory.xpm")

    def __getstate__(self):
        """
        __getstate__(self)

        When saving the document this object gets stored using Python's
        cPickle module. Since we have some un-pickable here -- the Coin
        stuff -- we must define this method to return a tuple of all pickable
        objects or None.
        """
        return None

    def __setstate__(self, state):
        """
        __setstate__(self,state)

        When restoring the pickled object from document we have the chance
        to set some internals here. Since no data were pickled nothing needs
        to be done here.
        """
        pass

    def setProperties(self, vp):
        # hide unnecessary view properties
        vp.setEditorMode("DisplayMode", 2)
        vp.setEditorMode("Visibility", 2)


class TrajectoryCommand(object):
    """Create Object command"""

    def GetResources(self):
        return {'Pixmap': path.join(_PATH_ICONS, "TrajectoryCmd.xpm"),
                'MenuText': "Trajectory",
                'ToolTip': "Create Trajectory instance."}

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        a = doc.addObject("App::DocumentObjectGroupPython", "Trajectory")
        Trajectory(a)
        if FreeCAD.GuiUp:
            ViewProviderTrajectory(a.ViewObject)
        doc.recompute()
        return

    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            return True

    def getHelp(self):
        return ["This is help for Trajectory\n",
                "and it needs to be written."]


if FreeCAD.GuiUp:
    FreeCADGui.addCommand('TrajectoryCommand', TrajectoryCommand())
