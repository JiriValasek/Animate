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

"""@package RobRotation
Classes related to the RobRotation component of the Animate Workbench.

The classes in this module provide funcionality for
a `DocumentObjectGroupPython` RobRotation instance and creates a command to be
used in a workbench.
"""

import FreeCAD
import FreeCADGui

from RobotPanel import RobotPanel

from PySide2.QtWidgets import QMessageBox
from bisect import bisect
from pivy import coin
from os import path

## Path to a folder with the necessary icons.
PATH_TO_ICONS = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                          "Icons")

## Path to a folder with the necessary user interface files.
PATH_TO_UI = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                       "UIs")


class RobRotationProxy:
    """
Proxy class for a `DocumentObjectGroupPython` RobRotation instance.

A RobRotationProxy instance adds properties to a `DocumentObjectGroupPython`
RobRotation instance and responds to their changes. It provides
a `RobotPanel` to be able to see an object in a rotation range.

Attributes:
    pose: A dict describing a pose - position, rotation axis, point and angle.

To connect this `Proxy` object to a `DocumentObjectGroupPython` RobRotation do:

        a = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroupPython",
                                             "RobRotation")
        RobRotationProxy(a)
    """

    def __init__(self, fp):
        """
Initialization method for RobRotationProxy.

A class instance is created and made a `Proxy` for a generic
`DocumentObjectGroupPython` RobRotation object. During initialization number of
properties are specified and preset.

Args:
    fp: A `DocumentObjectGroupPython` RobRotation object to be extended.
        """
        # Add (and preset) properties
        self.setProperties(fp)
        fp.Proxy = self

    def onChanged(self, fp, prop):
        """
Method called after `DocumentObjectGroupPython` RobRotation was changed.

A RobRotation is checked for its validity. If the `Placement` property is
changed, then `ParentFramePlacement` property of a `RobRotation` children is
set to equal the new `Placement`. If the `ParentFramePlacement` is changed,
then the `Placement` property is changed.

Args:
    fp: A `DocumentObjectGroupPython` RobRotation object.
    prop: A str name of a changed property.
        """
        # ignore updates to ranges
        if self.updated:
            self.updated = False
            return

        # Control allowed theta range limits
        elif prop == "ThetaMinimum" and hasattr(fp, "ThetaMaximum"):
            self.updated = True
            fp.ThetaMaximum = (fp.ThetaMaximum, fp.ThetaMinimum,
                               float("inf"), 1)
        elif prop == "ThetaMaximum" and hasattr(fp, "ThetaMinimum"):
            self.updated = True
            fp.ThetaMinimum = (fp.ThetaMinimum, -float("inf"),
                               fp.ThetaMaximum, 1)

        # Check that a RobRotation has valid format
        elif self.is_rotation_property(prop):
            traj_valid = self.is_ValidRotation(
                    fp.Timestamps, fp.TranslationX, fp.TranslationY,
                    fp.TranslationZ, fp.RotationPointX, fp.RotationPointY,
                    fp.RotationPointZ, fp.RotationAxisX, fp.RotationAxisY,
                    fp.RotationAxisZ, fp.RotationAngle)
#            traj_valid = self.is_ValidRotation(RobRotation=traj)
            if traj_valid != fp.ValidRotation:
                fp.ValidRotation = traj_valid

        elif prop == "Placement":
            # Propagate the Placement updates down the chain
            if hasattr(fp, "Group") and len(fp.Group) != 0:
                for child in fp.Group:
                    child.ParentFramePlacement = fp.Placement
                    child.purgeTouched()

            # Display animated objects in a pose specified by the rotation
            # and current time
            if hasattr(fp, "AnimatedObjects") and len(fp.AnimatedObjects) != 0:
                for o in fp.AnimatedObjects:
                    o.Placement = fp.Placement
                    o.purgeTouched()

        elif prop == "ParentFramePlacement":
            # If parent frame changed, recompute placement
            fp.Placement = fp.ParentFramePlacement.multiply(
                       fp.ObjectPlacement)

    def execute(self, fp):
        """
Method called when recomputing a `DocumentObjectGroupPython`.

If a RobRotation is valid, then current `pose` in a parent coordinate frame is
computed, `ObjectPlacement` and `Placement` are updated accordingly.

Args:
    fp: A `DocumentObjectGroupPython` RobRotation object.
        """
        # Check that current RobRotation has valid format
        if not fp.ValidRotation:
            FreeCAD.Console.PrintWarning(fp.Name + ".execute(): RobRotation " +
                                         "is not in a valid format.\n")
            return

        # Update placement according to current time and RobRotation
        indices, weights = self.find_timestamp_indices_and_weights(fp)

        self.fp.Theta = (weights[0]*fp.RotationAngle[indices[0]]
                         + weights[1]*fp.RotationAngle[indices[1]])

        T_theta = FreeCAD.Placement(FreeCAD.Vector(0, 0, 0),
                                    FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1),
                                                     self.fp.Theta))
        T_d = FreeCAD.Placement(FreeCAD.Vector(0, 0, fp.d),
                                FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 0))
        T_a = FreeCAD.Placement(FreeCAD.Vector(fp.a, 0, 0),
                                FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 0))
        T_alpha = FreeCAD.Placement(FreeCAD.Vector(0, 0, 0),
                                    FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1),
                                                     fp.Aplha))

        fp.ObjectPlacement = T_alpha.multiply(T_a.multiply(
                T_d.multiply(T_theta)))

        fp.Placement = fp.ParentFramePlacement.multiply(
                       fp.ObjectPlacement)

    def onDocumentRestored(self, fp):
        """
Method called when document is restored to make sure everything is as it was.

Reinitialization method - it creates properties and sets them to
default, if they were not restored automatically. Properties of
connected `ViewObject` are also recreated and reset if necessary.

Args:
    fp: A restored `DocumentObjectGroupPython` RobRotation object.
        """
        fp.ViewObject.Proxy.setProperties(fp.ViewObject)
        self.setProperties(fp)

    # supporting methods-------------------------------------------------------
    def setProperties(self, fp):
        """
Method to set properties during initialization or document restoration.

The properties are set if they are not already present and an
`AnimateDocumentObserver` is recreated.

Args:
    fp: A restored or barebone `DocumentObjectGroupPython` RobRotation object.
        """
        # Add (and preset) properties
        # Animation properties
        if not hasattr(fp, "ValidRotation"):
            fp.addProperty("App::PropertyBool", "ValidRotation", "General",
                           "This property records if rotation was changed."
                           ).ValidRotation = False
        if not hasattr(fp, "AnimatedObjects"):
            fp.addProperty("App::PropertyLinkListGlobal", "AnimatedObjects",
                           "General", "Objects that will be animated.")
        if not hasattr(fp, "Interpolate"):
            fp.addProperty("App::PropertyBool", "Interpolate", "General",
                           "Interpolate RobRotation between timestamps."
                           ).Interpolate = True
        if not hasattr(fp, "AllowServer"):
            fp.addProperty("App::PropertyBool", "AllowServer", "General",
                           "Should this object allow a Server object to "
                           + "change it.").AllowServer = True
        if not hasattr(fp, "AllowControl"):
            fp.addProperty("App::PropertyBool", "AllowControl", "General",
                           "Should this object allow a Control object "
                           + " to change it."
                           ).AllowControl = True
        if not hasattr(fp, "Time"):
            fp.addProperty("App::PropertyFloat", "Time", "General",
                           "Animation time in seconds.").Time = 0
        if not hasattr(fp, "ParentFramePlacement"):
            fp.addProperty("App::PropertyPlacement", "ParentFramePlacement",
                           "General", "Current placement of a Parent Frame.")
        if not hasattr(fp, "ObjectPlacement"):
            fp.addProperty("App::PropertyPlacement", "ObjectPlacement",
                           "General",
                           "Current Object placement in a Parent Frame.")

        # DH parameters
        if not hasattr(fp, "d"):
            fp.addProperty("App::PropertyFloat", "d", "DHParameters",
                           "Displacement along Z axis.").d = 0
        if not hasattr(fp, "a"):
            fp.addProperty("App::PropertyFloat", "a", "DHParameters",
                           "Displacement along X axis.").a = 0
        if not hasattr(fp, "Alpha"):
            fp.addProperty("App::PropertyFloat", "Alpha", "DHParameters",
                           "Rotation angle about X axis in degrees.").Alpha = 0
        if not hasattr(fp, "Theta"):
            fp.addProperty("App::PropertyFloat", "Theta", "DHParameters",
                           "Rotation angle about X axis in degrees.").Theta = 0
        if not hasattr(fp, "ThetaMaximum"):
            fp.addProperty("App::PropertyFloatConstraint", "ThetaMaximum",
                           "DHParameters", "Upper limit of rotation angle"
                           + " about Z axis in degrees."
                           ).ThetaMaximum = (360, 0, float("inf"), 1)
        elif hasattr(fp, "ThetaMinimum"):
            fp.ThetaMaximum = (fp.ThetaMaximum, fp.ThetaMinimum,
                               float("inf"), 1)
        if not hasattr(fp, "ThetaMinimum"):
            fp.addProperty("App::PropertyFloatConstraint", "ThetaMinimum",
                           "DHParameters", "Lower limit of rotation angle"
                           + " about Z axis in degrees."
                           ).ThetaMinimum = (0, -float("inf"), 360, 1)
        elif hasattr(fp, "ThetaMaximum"):
            fp.ThetaMinimum = (fp.ThetaMinimum, -float("inf"),
                               fp.ThetaMaximum, 1)
        if not hasattr(fp, "ThetaOffset"):
            fp.addProperty("App::PropertyFloat", "ThetaOffset",
                           "DHParameters", "Offset of rotation angle"
                           + " about Z axis in degrees.").ThetaOffset = 0

        # Rotation properties
        if not hasattr(fp, "Timestamps"):
            fp.addProperty("App::PropertyFloatList", "Timestamps",
                           "Rotation", "Timestamps at which we define\n"
                           + "translation and rotation.")
        if not hasattr(fp, "ThetaSequence"):
            fp.addProperty("App::PropertyFloatList", "ThetaSequence",
                           "Rotation", "Rotation angles about Z axis in"
                           + " degrees.")

        # Frame properties
        if not hasattr(fp, "ShowFrame"):
            fp.addProperty("App::PropertyBool", "ShowFrame", "Frame",
                           "Show a frame for current pose."
                           ).ShowFrame = True
        if not hasattr(fp, "FrameTransparency"):
            fp.addProperty("App::PropertyPercent", "FrameTransparency",
                           "Frame", "Transparency of the frame in percents."
                           ).FrameTransparency = 0
        if not hasattr(fp, "ShowFrameArrowheads"):
            fp.addProperty("App::PropertyBool", "ShowFrameArrowheads", "Frame",
                           "Show arrowheads for frame axis arrow's."
                           ).ShowFrameArrowheads = True
        if not hasattr(fp, "FrameArrowheadLength"):
            fp.addProperty("App::PropertyFloatConstraint",
                           "FrameArrowheadLength", "Frame",
                           "Frame axis arrow's arrowhead length.\n"
                           + "Range is < 1.0 | 1e6 >."
                           ).FrameArrowheadLength = (10, 1.0, 1e6, 1)
        else:
            fp.FrameArrowheadLength = (fp.FrameArrowheadLength, 1.0, 1e6, 1)
        if not hasattr(fp, "FrameArrowheadRadius"):
            fp.addProperty("App::PropertyFloatConstraint",
                           "FrameArrowheadRadius", "Frame",
                           "Frame axis arrow's arrowhead bottom radius.\n"
                           + "Range is < 0.5 | 1e6 >."
                           ).FrameArrowheadRadius = (5, 0.5, 1e6, 0.5)
        else:
            fp.FrameArrowheadRadius = (fp.FrameArrowheadRadius, 0.5, 1e6, 0.5)
        if not hasattr(fp, "ShaftLength"):
            fp.addProperty("App::PropertyFloatConstraint", "ShaftLength",
                           "Frame", "Frame axis arrow's shaft length.\n"
                           + "Range is < 1.0 | 1e6 >."
                           ).ShaftLength = (20, 1.0, 1e6, 1)
        else:
            fp.ShaftLength = (fp.ShaftLength, 1.0, 1e6, 1)
        if not hasattr(fp, "ShaftWidth"):
            fp.addProperty("App::PropertyFloatConstraint", "ShaftWidth",
                           "Frame", "Frame axis arrow's shaft width.\n"
                           + "Range is < 1.0 | 64 >."
                           ).ShaftWidth = (4, 1.0, 64, 1)
        else:
            fp.ShaftWidth = (fp.ShaftWidth, 1.0, 64, 1)
        if not hasattr(fp, "ShowFrameLabels"):
            fp.addProperty("App::PropertyBool", "ShowFrameLabels",
                           "Frame", "Show label for frame axes."
                           ).ShowFrameLabels = True

        # Label properties
        if not hasattr(fp, "FontSize"):
            fp.addProperty("App::PropertyIntegerConstraint", "FontSize",
                           "Labels", "Label font size.\n"
                           + "Range is < 1 | 100 >."
                           ).FontSize = (10, 1, 100, 1)
        else:
            fp.FontSize = (fp.FontSize, 1, 100, 1)
        if not hasattr(fp, "DistanceToAxis"):
            fp.addProperty("App::PropertyFloatConstraint", "DistanceToAxis",
                           "Labels", "Distance from label to its axis.\n"
                           + "Range is < 0.5 | 1e6 >."
                           ).DistanceToAxis = (5, 0.5, 1e6, 0.5)
        else:
            fp.DistanceToAxis = (fp.DistanceToAxis, 0.5, 1e6, 0.5)
        if not hasattr(fp, "Subscription"):
            fp.addProperty("App::PropertyString", "Subscription", "Labels",
                           "Subscription added to an axis name."
                           ).Subscription = ""
        if not hasattr(fp, "Superscription"):
            fp.addProperty("App::PropertyString", "Superscription", "Labels",
                           "Superscription added to an axis name."
                           ).Superscription = ""
        if not hasattr(fp, "FontFamily"):
            fp.addProperty("App::PropertyEnumeration", "FontFamily",
                           "Labels", "Label font family."
                           ).FontFamily = ["SERIF", "SANS", "TYPEWRITER"]
        if not hasattr(fp, "FontStyle"):
            fp.addProperty("App::PropertyEnumeration", "FontStyle",
                           "Labels", "Label font style."
                           ).FontStyle = ["NONE", "BOLD", "ITALIC",
                                          "BOLD ITALIC"]

        # Placement properties
        if not hasattr(fp, "Placement"):
            fp.addProperty("App::PropertyPlacement", "Placement", "Base",
                           "Current placement for animated objects in "
                           + "world frame.")

        # Make some properties read-only
        fp.setEditorMode("ObjectPlacement", 1)
        fp.setEditorMode("ParentFramePlacement", 1)
        fp.setEditorMode("Theta", 1)

        # Hide some properties
        fp.setEditorMode("Placement", 2)
        fp.setEditorMode("ValidRotation", 2)

        import AnimateDocumentObserver
        AnimateDocumentObserver.addObserver()

    def change_joint_sequence(self, fp, joint_sequence):
        """
Method used to change a `RobRotation`'s joint variable sequence.

A `joint_sequence` dictionary containing a RobRotation is tested for validity
and then assigned to a `RobRotation` `DocumentObjectGroupPython`.

Args:
    fp: A `DocumentObjectGroupPython` RobRotation object.
    joint_sequence: A dictionary describing a RobRotation.
        """
        # Check that RobRotation has a correct format and load it
        if self.is_ValidRotation(rotation=joint_sequence):
            fp.Timestamps = joint_sequence["Timestamps"]
            fp.ThetaSequence = joint_sequence["ThetaSequence"]
        else:
            FreeCAD.Console.PrintError("Invalid joint sequence!")

    def is_rotation_property(self, prop):
        """
Method to check that a property describes a RobRotation.

It's checked whether `prop` is `Timestamps` or `ThetaSequence`.

Args:
    prop: A str name of a changed property.

Returns:
    True if prop describes a RobRotation and False otherwise.
        """
        return prop in ["Timestamps", "ThetaSequence"]

    def is_ValidRotation(self, timestamps=[], theta=[], rotation=None):
        """
Method to check if a RobRotation is valid.

This method needs either a `rotation` dictionary argument or all the other
lists of floats. A valid rotation needs to have all the necessary lists.
All the lists must have same length. A `timestamps` list must consist of
a sequence of strictly increasing floats. A rotation axis must have always
length equal to 1.

Args:
    timestamps: A list of floats marking timestamps.
    theta: A list of floats signifying rotation angles about Z axis.
    rotation: A dict containing all lists above.

Returns:
    True if rotation is valid and False otherwise.
        """
        # Check all keys are included and record lengths of their lists
        if rotation is not None and isinstance(rotation, dict):
            for key in ["Timestamps", "ThetaSequence"]:
                if key not in rotation.keys():
                    FreeCAD.Console.PrintWarning("Rotation misses key " +
                                                 key + ".\n")
                    return False
            timestamps = rotation["Timestamps"]
            theta_sequence = rotation["ThetaSequence"]

        # Check that all lists have the same length
        if len(timestamps) == 0 or \
                (len(timestamps) != 0 and
                 len(timestamps) != len(theta_sequence)):
            FreeCAD.Console.PrintWarning("Rotation has lists with "
                                         + "inconsistent or zero "
                                         + "lengths.\n")
            return False

        # Check timestamps correspond to list of increasing values
        if any([timestamps[i] >= timestamps[i+1]
                for i in range(len(timestamps)-1)]):
            FreeCAD.Console.PrintWarning("Rotation 'Timestamps' is not "
                                         + "list of increasing values.\n")
            return False

        if any([self.fp.ThetaMinimum <= th <= self.fp.ThetaMaximum
                for th in theta_sequence]):
            FreeCAD.Console.PrintWarning("Rotation 'ThetaSequence' elements"
                                         + " are out of theta range.\n")
            return False

        return True

    def find_timestamp_indices_and_weights(self, fp):
        """
Method to find weighted `timestamps` indices corresponding to a given `time`.

If a `time` is smaller than the first timestamp, the returned indices are [0,0]
with weights [1,0] as that's the closest value. Similarly, if the `time` is
greater than the last timestamp, the returned indices are [-1,-1] pointing to
the last element of a `timestamps` list with weights [1,0]. If the `time` value
is between the first and last timestamp, the indices belong to the closest
higher and lower time. At the same time, if interpolation is off, the weights
are 0 and 1, where one is given to the index closest to the `time`. Otherwise,
the weights, whose sum equals to 1, are computed to show inverse relative
distance i.e. an index with a greater weight is the closer.

Args:
    fp: A `DocumentObjectGroupPython` RobRotation object.

Returns:
    indices: A list of two integers between -1 and and length of `Timestamps`.
    weights: A list of two floats between 0 and 1 showing relative closeness.
        """
        # Retrieve indices corresponding to current time
        # If the time is before the first Timestamp use the first Timestamp
        if fp.Time <= fp.Timestamps[0]:
            indices = [0, 0]
            weights = [1, 0]

        # If the time is after the last Timpestamp use the last Timestamp
        elif fp.Time >= fp.Timestamps[-1]:
            indices = [-1, -1]
            weights = [1, 0]

        # If time is in the range of Timesteps
        else:
            # Find the index of the closest higher value
            indices = [bisect(fp.Timestamps, fp.Time)]
            # Add the previous index
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


class ViewProviderRobRotationProxy:
    """
Proxy class for `Gui.ViewProviderDocumentObject` RobRotation.ViewObject.

A ViewProviderRobRotationProxy instance provides a RobRotation's icon,
double-click response and context menu with a *Select Time* option.

Attributes:
    fp: A RobRotation object.
    panel: A RobotPanel if one is active or None.
    tf_object2world: A SoTransform transformation from object to world frame.
    font: A SoFontStyle font for axes labels.
    frame: A SoSeparator with a coordinate frame made from 3 RGB arrows.
    visualisations: A SoSwitch with all visualisations (frame & rotation axis).
    label_texts: A list of `SoText2`s labels denoting all axes and an origin.
    label_translations: A list of `SoTranslation`s moving labels.
    labels: A list of `SoSwitch`es containing colored translated labels.
    frame_shaft: A SoLineSet shaft for frame axes.
    frame_arrowhead_translation: A SoTranslation moving frame arrowheads.
    frame_arrowhead_cone: A SoCone arrowhead cone for frame axes.
    frame_arrowhead: A SoSwitch translated cone for frame axes.
    frame_color_x: A SoPackedColor red color for an X axis.
    frame_color_y: A SoPackedColor green color for an Y axis.
    frame_color_z: A SoPackedColor blue color for an Z axis.
    frame_drawstyle: A SoDrawStyle controlling frame axes shaft line width.

To connect this `Proxy` object to a `Gui.ViewProviderDocumentObject`
RobRotation.ViewObject do:

        a = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroupPython",
                                             "RobRotation")
        ViewProviderRobRotationProxy(a.ViewObject)
    """

    panel = None
    fp = None

    # standard methods---------------------------------------------------------
    def __init__(self, vp):
        """
Initialization method for ViewProviderRobRotationProxy.

A class instance is created and made a `Proxy` for a generic
`Gui.ViewProviderDocumentObject` RobRotation.ViewObject. During initialization
number of properties are specified and preset.

Args:
    vp: A barebone `Gui.ViewProviderDocumentObject` RobRotation.ViewObject.
        """
        self.setProperties(vp)
        vp.Proxy = self

    def attach(self, vp):
        """
Method called by FreeCAD after initialization to attach Coin3D constructs.

A coordinate frame made of RGB arrows corresponding to X, Y and Z axes. This
frame shows current pose in a RobRotation. This method adds RobRotation as
the `fp` attribute.

Args:
    vp: A RobRotation.ViewObject after initialization.
        """
        # prepare transformation to keep pose corresponding to placement
        self.tf_object2world = coin.SoTransform()

        labels = self.makeLabels()
        self.font = coin.SoFontStyle()

        frame = self.makeFrame(labels[:3])
        frame.insertChild(self.tf_object2world, 0)
        frame.insertChild(self.font, 1)
        self.frame = coin.SoSwitch()
        self.frame.addChild(frame)

        self.visualisations = coin.SoSwitch()
        self.visualisations.addChild(self.frame)
        vp.RootNode.addChild(self.visualisations)

        vp.Object.Proxy.setProperties(vp.Object)
        self.setProperties(vp)
        self.fp = vp.Object

    def updateData(self, fp, prop):
        """
Method called after `DocumentObjectGroupPython` RobRotation was changed.

This method is used to update Coin3D constructs, if associated properties
changed e.g. if the `FrameArrowheadRadius` changes, all Coin3D cones
representing frame arrowheads will change their radius accordingly.

Args:
    fp: A `DocumentObjectGroupPython` RobRotation object.
    prop: A str name of a changed property.
        """
        # Placement changes
        if prop == "Placement" and hasattr(fp, "Placement"):
            trans = fp.Placement.Base
            rot = fp.Placement.Rotation
            self.tf_object2world.translation.setValue((trans.x, trans.y,
                                                       trans.z))
            self.tf_object2world.rotation.setValue(rot.Q)

        # Frame changes
        elif prop == "ShowFrame" and hasattr(fp, "ShowFrame"):
            if fp.ShowFrame:
                self.frame.whichChild.setValue(coin.SO_SWITCH_ALL)
            else:
                self.frame.whichChild.setValue(coin.SO_SWITCH_NONE)

        elif prop == "FrameTransparency" and hasattr(fp, "FrameTransparency"):
            self.frame_color_x.orderedRGBA.\
                setValue(0xff0000ff - (0xff*fp.FrameTransparency)//100)
            self.frame_color_y.orderedRGBA.\
                setValue(0x00ff00ff - (0xff*fp.FrameTransparency)//100)
            self.frame_color_z.orderedRGBA.\
                setValue(0x0000ffff - (0xff*fp.FrameTransparency)//100)

        elif prop == "ShaftLength" and hasattr(fp, "ShaftLength"):
            self.frame_shaft.vertexProperty.getValue().vertex.\
                set1Value(1, 0, fp.ShaftLength, 0)
            if hasattr(fp, "FrameArrowheadLength"):
                self.frame_arrowhead_translation.translation.setValue(
                    0, fp.ShaftLength + fp.FrameArrowheadLength/2, 0)
            if not fp.ShowFrameArrowheads and hasattr(fp, "DistanceToAxis"):
                self.label_translations[0].translation.setValue(
                    0, fp.ShaftLength + fp.DistanceToAxis, 0)

        elif prop == "FrameArrowheadLength" and \
                hasattr(fp, "FrameArrowheadLength"):
            self.frame_arrowhead_cone.height.setValue(fp.FrameArrowheadLength)
            if hasattr(fp, "ShaftLength"):
                self.frame_arrowhead_translation.translation.setValue(
                    0, fp.ShaftLength + fp.FrameArrowheadLength/2, 0)
            if fp.ShowFrameArrowheads and hasattr(fp, "DistanceToAxis"):
                self.label_translations[0].translation.setValue(
                    0, fp.FrameArrowheadLength/2 + fp.DistanceToAxis, 0)

        elif prop == "ShaftWidth" and hasattr(fp, "ShaftWidth"):
            self.frame_drawstyle.lineWidth.setValue(fp.ShaftWidth)

        elif prop == "FrameArrowheadRadius" and \
                hasattr(fp, "FrameArrowheadRadius"):
            self.frame_arrowhead_cone.bottomRadius.setValue(
                fp.FrameArrowheadRadius)

        elif prop == "ShowFrameArrowheads" and \
                hasattr(fp, "ShowFrameArrowheads"):
            if fp.ShowFrameArrowheads:
                self.frame_arrowhead.whichChild.setValue(coin.SO_SWITCH_ALL)
                if hasattr(fp, "FrameArrowheadLength") and \
                        hasattr(fp, "DistanceToAxis"):
                    self.label_translations[0].translation.setValue(
                        0, fp.FrameArrowheadLength/2 + fp.DistanceToAxis, 0)
            else:
                self.frame_arrowhead.whichChild.setValue(coin.SO_SWITCH_NONE)
                if hasattr(fp, "ShaftLength") and \
                        hasattr(fp, "DistanceToAxis"):
                    self.label_translations[0].translation.setValue(
                        0, fp.ShaftLength + fp.DistanceToAxis, 0)

        elif prop == "ShowFrameLabels" and hasattr(fp, "ShowFrameLabels"):
            for label in self.labels[:3]:
                if fp.ShowFrameLabels:
                    label.whichChild.setValue(coin.SO_SWITCH_ALL)
                else:
                    label.whichChild.setValue(coin.SO_SWITCH_NONE)

        # Changes to the labels
        elif prop == "Subscription" and hasattr(fp, "Subscription"):
            for l in self.label_texts:
                l.string.setValues(2, 1, [fp.Subscription])

        elif prop == "Superscription" and hasattr(fp, "Superscription"):
            for l in self.label_texts:
                l.string.setValues(0, 1, [fp.Superscription])

        elif prop == "FontFamily" and hasattr(fp, "FontFamily"):
            if fp.FontFamily == "SERIF":
                self.font.family.setValue(self.font.SERIF)
            if fp.FontFamily == "SANS":
                self.font.family.setValue(self.font.SANS)
            if fp.FontFamily == "TYPEWRITER":
                self.font.family.setValue(self.font.TYPEWRITER)

        elif prop == "FontStyle" and hasattr(fp, "FontStyle"):
            if fp.FontStyle == "NONE":
                self.font.style.setValue(self.font.NONE)
            if fp.FontStyle == "BOLD":
                self.font.style.setValue(self.font.BOLD)
            if fp.FontStyle == "ITALIC":
                self.font.style.setValue(self.font.ITALIC)
            if fp.FontStyle == "BOLD ITALIC":
                self.font.style.setValue(self.font.BOLD | self.font.ITALIC)

        elif prop == "FontSize" and hasattr(fp, "FontSize"):
            self.font.size.setValue(fp.FontSize)

        elif prop == "DistanceToAxis" and hasattr(fp, "DistanceToAxis") and \
            hasattr(fp, "ShowFrameArrowheads") and \
                hasattr(fp, "ShowAxisArrowhead"):
            if fp.ShowFrameArrowheads and hasattr(fp, "FrameArrowheadLength"):
                self.label_translations[0].translation.setValue(
                    0, fp.FrameArrowheadLength/2 + fp.DistanceToAxis, 0)
            elif hasattr(fp, "ShaftLength"):
                self.label_translations[0].translation.setValue(
                    0, fp.ShaftLength + fp.DistanceToAxis, 0)
            if fp.ShowAxisArrowhead and hasattr(fp, "AxisArrowheadLength"):
                self.label_translations[1].translation.setValue(
                    0, fp.AxisArrowheadLength/2 + fp.DistanceToAxis, 0)
            elif hasattr(fp, "AxisLength"):
                self.label_translations[1].translation.setValue(
                    0, fp.AxisLength + fp.DistanceToAxis, 0)

    def onChanged(self, vp, prop):
        """
Method called after RobRotation.ViewObject was changed.

If visibility changed, an appropriate Coin3D construct hides the frame showing
current pose.

Args:
    vp: A RobRotation.ViewObject.
    prop: A str name of a changed property.
        """
        if prop == "Visibility":
            if vp.Visibility:
                self.visualisations.whichChild.setValue(coin.SO_SWITCH_ALL)
            else:
                self.visualisations.whichChild.setValue(coin.SO_SWITCH_NONE)

    def claimChildren(self):
        """
Method called by FreeCAD to retrieve assigned children.

When a property of a RobRotation is touched the RobRotation and the FreeCAD
ActiveDocument are notified. The FreeCAD ActiveDocument then emits a signal
to inform all its observers e.g. the FreeCADGui ActiveDocument. The FreeCADGui
document then emits a new signal to inform e.g. the tree view. The tree view
then invokes `claimChildren()`.
        """
        if hasattr(self, "fp") and self.fp:
            return self.fp.Group
        return []

    def canDropObject(self, obj):
        """
Method called by FreeCAD to ask if an object `obj` can be dropped into a Group.

Only FreeCAD objects of a RobRotation type are allowed to drop inside
a RobRotation group.

Args:
    obj: A FreeCAD object hovering above a RobRotation item in the Tree View.
        """
        if hasattr(obj, "Proxy") and \
                  (obj.Proxy.__class__.__name__ == "RobRotationProxy" or
                   obj.Proxy.__class__.__name__ == "RobTranslationProxy"):
            return True
        return False

    def getIcon(self):
        """
Method called by FreeCAD to supply an icon for the Tree View.

A full path to an icon is supplied for the FreeCADGui.

Returns:
    A str path to an icon.
        """
        return path.join(PATH_TO_ICONS, "RobRotation.png")

    def __getstate__(self):
        """
Necessary method to avoid errors when trying to save unserializable objects.

This method is used by JSON to serialize unserializable objects during
autosave. Without this an Error would rise when JSON would try to do
that itself.

We need this for unserializable `fp` attribute, but we don't
serialize it, because it's enough to reset it when object is restored.

Returns:
    None, because we don't serialize anything.
        """
        return None

    def __setstate__(self, state):
        """
Necessary method to avoid errors when trying to restore unserializable objects.

This method is used during a document restoration. We need this for
unserializable `fp` attribute, but we do not restore it, because it's enough
to reset it.
        """
        pass

    def setProperties(self, vp):
        """
Method to hide unused properties.

Property Display Mode is set to be invisible as they are unused.

Args:
    vp: A `Gui.ViewProviderDocumentObject` RobRotation.ViewObject.
        """
        # hide unnecessary view properties
        vp.setEditorMode("DisplayMode", 2)

    def doubleClicked(self, vp):
        """
Method called by FreeCAD when RobRotation is double-clicked in the Tree View.

If no dialog is opened in the Task View, a new `RobotPanel` is opened.
If another `RobotPanel` is opened, it is closed and all its QDialogs are
added to a new `RobotPanel`. If a `RobotPanel` is already opened,
the Model tab on the Combo View is swapped for the Tasks tab so that the panel
becomes visible. If another dialog is opened a warning is shown.

Args:
    vp: A `Gui.ViewProviderDocumentObject` RobRotation.ViewObject.
        """
        # Switch to the Task View if a RobRotation panel is already opened
        if self.panel:
            FreeCADGui.Control.showTaskView()

        # Try to open new RobotPanel
        else:
            # Load the QDialog from a file and name it after this object
            new_form = [FreeCADGui.PySideUic.loadUi(path.join(PATH_TO_UI,
                                                    "AnimationJoint.ui"))]
            new_form[0].setWindowTitle(vp.Object.Label)

            # Create a control panel and try to show it
            self.panel = RobotPanel([vp.Object], new_form)
            try:
                FreeCADGui.Control.showDialog(self.panel)
            except RuntimeError as e:
                # Reset the panel
                self.panel = None

                # Find all RobRotation/RobTranslation feature python objects
                # with a reference to a RobotPanel
                robot_joints = []
                for obj in FreeCAD.ActiveDocument.Objects:
                    if hasattr(obj, "Proxy") and \
                            (obj.Proxy.__class__.__name__
                             == "RobRotationProxy"
                             or obj.Proxy.__class__.__name__
                             == "RobTranslationProxy"):
                        if obj.ViewObject.Proxy.panel is not None:
                            robot_joints.append(obj)

                if len(robot_joints) > 0:
                    # Close opened Trajecotry panel
                    robot_joints[0].ViewObject.Proxy.panel.reject()

                    # Load the QDialog form for each RobRotation/RobTranslation
                    # which had a reference to the panel
                    forms = []
                    for joint in robot_joints:
                        form = FreeCADGui.PySideUic.loadUi(
                                path.join(PATH_TO_UI, "AnimationJoint.ui"))
                        form.setWindowTitle(joint.Label)
                        forms.append(form)

                    # Load one more QDialog for this RobRotation
                    forms.append(new_form[0])

                    # Add this RobRotation to the list of robot_joints
                    robot_joints.append(vp.Object)

                    # Add a reference to the new panel to view providers
                    # of all robot_joints
                    self.panel = RobotPanel(robot_joints, forms)
                    for joint in robot_joints:
                        joint.ViewObject.Proxy.panel = self.panel
                    FreeCADGui.Control.showDialog(self.panel)
                    return True

                # Diffeerent Task panel is opened, inform the user
                else:
                    QMessageBox.warning(
                        None,
                        'Error while opening RobotPanel',
                        "A different panel is already active.\n"
                        + "Close it before opening this one.")
                FreeCADGui.Control.showTaskView()
        return True

    def setupContextMenu(self, vp, menu):
        """
Method called by the FreeCAD to customize a context menu for a RobRotation.

The *Transform* and *Set colors...* items are removed from the context menu
shown upon right click on `DocumentObjectGroupPython` RobRotation in the Tree
View. The option to *Select Time* is added instead.

Args:
    vp: A rightclicked `Gui.ViewProviderDocumentObject` RobRotation.ViewObject.
    menu: A Qt's QMenu to be edited.
        """
        menu.clear()
        action = menu.addAction("Select Time")
        action.triggered.connect(lambda f=self.doubleClicked,
                                 arg=vp: f(arg))

    def makeLabels(self):
        """
Method which makes Coin3D labels to be displayed in the FreeCAD View.

Frame labels for axes X, Y and Z and a label for rotation axis are made.
The labels have the same color as the axes.

Returns:
    A SoSwitch with colored text label to be shown in the FreeCAD View.
        """
        label_strings = ["X", "Y", "Z"]
        colors = [0xFF0000FF, 0x00FF00FF, 0x0000FFFF]
        self.label_texts = []
        self.label_translations = []
        # frame translation
        self.label_translations.append(coin.SoTranslation())
        # axis translation
        self.label_translations.append(coin.SoTranslation())
        self.labels = []
        for i in range(3):
            label_group = coin.SoSeparator()
            label_group.addChild(self.label_translations[0])
            frame_axis_color = coin.SoPackedColor()
            frame_axis_color.orderedRGBA.setValue(colors[i])
            label_group.addChild(frame_axis_color)
            self.label_texts.append(coin.SoText2())
            self.label_texts[i].string.setValues(
                0, 3, ["", label_strings[i], ""])
            self.label_texts[i].justification.setValue(
                self.label_texts[i].CENTER)
            self.label_texts[i].spacing.setValue(0.45)
            label_group.addChild(self.label_texts[i])
            self.labels.append(coin.SoSwitch())
            self.labels[i].addChild(label_group)
        return self.labels

    def makeFrame(self, frame_labels):
        """
Method which makes a Coin3D frame to show a current pose in a RobRotation.

A frame is made from 3 red, green and blue arrows representing X, Y and Z.
Arrows are each constructed from a shaft and an arrowhead. Their dimensions
and other attributes are unassigned as they are extracted from appropriate
`RobRotation` properties.

Returns:
    A SoSeparator with the frame shown in the FreeCAD View.
        """
        # make a generic shaft from 0 in Y direction
        shaft_vertices = coin.SoVertexProperty()
        shaft_vertices.vertex.setNum(2)
        shaft_vertices.vertex.set1Value(0, 0, 0, 0)
        self.frame_shaft = coin.SoLineSet()
        self.frame_shaft.vertexProperty.setValue(shaft_vertices)
        self.frame_shaft.numVertices.setNum(1)
        self.frame_shaft.numVertices.setValue(2)

        # make a generic conic arrowhead oriented in Y axis direction and
        # move it at the end of the shaft
        self.frame_arrowhead_translation = coin.SoTranslation()
        self.frame_arrowhead_cone = coin.SoCone()
        self.frame_arrowhead = coin.SoSwitch()
        self.frame_arrowhead.addChild(self.frame_arrowhead_translation)
        self.frame_arrowhead.addChild(self.frame_arrowhead_cone)

        # make rotations to rotate prepared shaft and arrowhead for Y axis
        # direction also to X and Z
        rot_y2x = coin.SoRotation()
        rot_y2x.rotation.setValue(coin.SbRotation(coin.SbVec3f(0, 1, 0),
                                                  coin.SbVec3f(1, 0, 0)))
        rot_y2z = coin.SoRotation()
        rot_y2z.rotation.setValue(coin.SbRotation(coin.SbVec3f(0, 1, 0),
                                                  coin.SbVec3f(0, 0, 1)))

        # prepare colors for X,Y,Z which will correspond to R,G,B as customary
        self.frame_color_x = coin.SoPackedColor()
        self.frame_color_y = coin.SoPackedColor()
        self.frame_color_z = coin.SoPackedColor()

        # make complete colored and rotated arrows
        x_arrow = coin.SoSeparator()
        x_arrow.addChild(rot_y2x)
        x_arrow.addChild(self.frame_color_x)
        x_arrow.addChild(self.frame_shaft)
        x_arrow.addChild(self.frame_arrowhead)
        x_arrow.addChild(frame_labels[0])
        y_arrow = coin.SoSeparator()
        y_arrow.addChild(self.frame_color_y)
        y_arrow.addChild(self.frame_shaft)
        y_arrow.addChild(self.frame_arrowhead)
        y_arrow.addChild(frame_labels[1])
        z_arrow = coin.SoSeparator()
        z_arrow.addChild(rot_y2z)
        z_arrow.addChild(self.frame_color_z)
        z_arrow.addChild(self.frame_shaft)
        z_arrow.addChild(self.frame_arrowhead)
        z_arrow.addChild(frame_labels[2])

        # prepare draw style to control shaft width
        self.frame_drawstyle = coin.SoDrawStyle()

        # make complete frame and it to shaded display mode
        separated_frame = coin.SoSeparator()
        separated_frame.addChild(self.frame_drawstyle)
        separated_frame.addChild(x_arrow)
        separated_frame.addChild(y_arrow)
        separated_frame.addChild(z_arrow)

        return separated_frame


class RobRotationCommand(object):
    """
Class specifying Animate workbench's RobRotation button/command.

This class provides resources for a toolbar button and a menu button.
It controls their behaivor(Active/Inactive) and responds to callbacks after
either of them was clicked(Activated).
    """

    def GetResources(self):
        """
Method used by FreeCAD to retrieve resources to use for this command.

Returns:
    A dict with items `PixMap`, `MenuText` and `ToolTip` which contain
    a path to a command icon, a text to be shown in a menu and
    a tooltip message.
        """
        return {'Pixmap': path.join(PATH_TO_ICONS, "RobRotationCmd.png"),
                'MenuText': "RobRotation",
                'ToolTip': "Create RobRotation instance."}

    def Activated(self):
        """
Method used as a callback when the toolbar button or the menu item is clicked.

This method creates a RobRotation instance in currently active document.
Afterwards it adds a RobRotationProxy as a `Proxy` to this instance as well as
ViewProviderRobRotationProxy to its `ViewObject.Proxy`, if FreeCAD runs in the
Graphic mode.
        """
        doc = FreeCAD.ActiveDocument
        a = doc.addObject("App::DocumentObjectGroupPython", "RobRotation")
        RobRotationProxy(a)
        if FreeCAD.GuiUp:
            ViewProviderRobRotationProxy(a.ViewObject)
        doc.recompute()
        return

    def IsActive(self):
        """
Method to specify when the toolbar button and the menu item are enabled.

The toolbar button `RobRotation` and menu item `RobRotation` are set to be
active only when there is an active document in which a RobRotation instance
can be created.

Returns:
    True if buttons shall be enabled and False otherwise.
        """
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            return True


if FreeCAD.GuiUp:
    # Add command to FreeCAD Gui when importing this module in InitGui
    FreeCADGui.addCommand('RobRotationCommand', RobRotationCommand())
