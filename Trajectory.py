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

from PySide2.QtWidgets import QDialogButtonBox
from PySide2.QtWidgets import QMessageBox
from PySide2.QtCore import QObject
from bisect import bisect
from pivy import coin
from os import path

## Path to a folder with the necessary icons.
_PATH_ICONS = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                        "Icons")

## Path to a folder with the necessary user interface files.
_PATH_UI = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                     "UIs")


class ControlPanel(QObject):
    """
Attributes:
    trajectories
    previous_times
    form
    """

    def __init__(self, trajectories, forms):
        super(ControlPanel, self).__init__()
        self.trajectories = trajectories

        # Disable editing of Trajectory properties and store previous
        # times from trajectories
        self.previous_times = []
        for trajectory in trajectories:
            self.previous_times.append(trajectory.Time)
            for prop in trajectory.PropertiesList:
                trajectory.setEditorMode(prop, 1)
            # Leave some properties hidden
            trajectory.setEditorMode("Placement", 2)
            trajectory.setEditorMode("ValidTrajectory", 2)

        # Add QDialogs to be displayed in freeCAD
        self.form = forms

        # Add callbacks to sliders on all forms and muve sliders to a position
        # corresponding with time values
        for i in range(len(forms)):
            forms[i].sld_time.valueChanged.connect(
                lambda value, form=forms[i],
                trajectory=trajectories[i]:
                    self.sliderChanged(value, form, trajectory))
            val = (100 * (trajectories[i].Time
                          - trajectories[i].Timestamps[0])) / \
                  (trajectory.Timestamps[-1]
                   - trajectory.Timestamps[0])
            forms[i].sld_time.setValue(val)

    def sliderChanged(self, value, form, trajectory):
        # Compute a time from the slider position and timestamp range
        t = value * (trajectory.Timestamps[-1]
                     - trajectory.Timestamps[0]) / 100 \
            + trajectory.Timestamps[0]

        # Update the time in a trajectory and
        # recompute the document to show changes
        trajectory.Time = t
        form.lbl_time.setText("Time: " + ("%5.3f" % t))
        FreeCAD.ActiveDocument.recompute()
        FreeCADGui.updateGui()

    def close(self):
        # Allow editing of Trajecotry properties again
        for trajectory in self.trajectories:
            for prop in trajectory.PropertiesList:
                trajectory.setEditorMode(prop, 0)
            trajectory.ViewObject.Proxy.panel = None

            # Keep some properties read-only state if they were in it before
            trajectory.setEditorMode("ObjectPlacement", 1)
            trajectory.setEditorMode("ParentFramePlacement", 1)

            # Keep some properties hidden state if they were hidden before
            trajectory.setEditorMode("Placement", 2)
            trajectory.setEditorMode("ValidTrajectory", 2)
        FreeCADGui.Control.closeDialog()

    def reject(self):
        # Return Trajectory times to previous values
        for i in range(len(self.trajectories)):
            self.trajectories[i].Time = self.previous_times[i]

        # Close the panel and recompute the document to show changes
        self.close()
        FreeCAD.ActiveDocument.recompute()
        FreeCADGui.updateGui()

    def accept(self):
        # Close the panel
        self.close()

    def getStandardButtons(self, *args):
        """ To have just one button - close """
        return QDialogButtonBox.Ok | QDialogButtonBox.Cancel

    def isAllowedAlterSelection(self):
        return True

    def isAllowedAlterView(self):
        return True

    def isAllowedAlterDocument(self):
        return True


class TrajectoryProxy:
    """
    TrajectoryProxy is a Proxy object made to be connected to
    `Part::FeaturePython` Trajectory object.

Attributes:
    pose

    To connect them use:

    >>> a=FreeCAD.ActiveDocument.addObject("App::FeaturePython",
                                           "Trajectory")
    >>> TrajectoryProxy(a)
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
        # Add (and preset) properties
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
        # Check that a trajectory has valid format
        if self.is_trajectory_property(prop):
#            traj = {}
#            traj["RotationAngle"] = fp.RotationAngle
#            traj["RotationAxisX"] = fp.RotationAxisX
#            traj["RotationAxisY"] = fp.RotationAxisY
#            traj["RotationAxisZ"] = fp.RotationAxisZ
#            traj["RotationPointX"] = fp.RotationPointX
#            traj["RotationPointY"] = fp.RotationPointY
#            traj["RotationPointZ"] = fp.RotationPointZ
#            traj["TranslationX"] = fp.TranslationX
#            traj["TranslationY"] = fp.TranslationY
#            traj["TranslationZ"] = fp.TranslationZ
#            traj["Timestamps"] = fp.Timestamps
            traj_valid = self.is_ValidTrajectory(
                    fp.Timestamps, fp.TranslationX, fp.TranslationY,
                    fp.TranslationZ, fp.RotationPointX, fp.RotationPointY,
                    fp.RotationPointZ, fp.RotationAxisX, fp.RotationAxisY,
                    fp.RotationAxisZ, fp.RotationAngle)
#            traj_valid = self.is_ValidTrajectory(trajectory=traj)
            if traj_valid != fp.ValidTrajectory:
                fp.ValidTrajectory = traj_valid

        elif prop == "Placement":
            # Propagate the Placement updates down the chain
            if hasattr(fp, "Group") and len(fp.Group) != 0:
                for child in fp.Group:
                    child.ParentFramePlacement = fp.Placement
                    child.purgeTouched()

            # Display animated objects in a pose specified by the trajectory
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
        # Check that current trajectory has valid format
        if not fp.ValidTrajectory:
            FreeCAD.Console.PrintWarning(fp.Name + ".execute(): Trajectory " +
                                         "is not in a valid format.\n")
            return

        # Update placement according to current time and trajectory
        indices, weights = self.find_timestamp_indices_and_weights(fp)

        self.pose["position"] = (weights[0]*fp.TranslationX[indices[0]] +
                                 weights[1]*fp.TranslationX[indices[1]],
                                 weights[0]*fp.TranslationY[indices[0]] +
                                 weights[1]*fp.TranslationY[indices[1]],
                                 weights[0]*fp.TranslationZ[indices[0]] +
                                 weights[1]*fp.TranslationZ[indices[1]])
        self.pose["rot_axis"] = (weights[0]*fp.RotationAxisX[indices[0]]
                                 + weights[1]*fp.RotationAxisX[indices[1]],
                                 weights[0]*fp.RotationAxisY[indices[0]]
                                 + weights[1]*fp.RotationAxisY[indices[1]],
                                 weights[0]*fp.RotationAxisZ[indices[0]]
                                 + weights[1]*fp.RotationAxisZ[indices[1]])
        self.pose["rot_point"] = (weights[0]*fp.RotationPointX[indices[0]]
                                  + weights[1]*fp.RotationPointX[indices[1]],
                                  weights[0]*fp.RotationPointY[indices[0]]
                                  + weights[1]*fp.RotationPointY[indices[1]],
                                  weights[0]*fp.RotationPointZ[indices[0]]
                                  + weights[1]*fp.RotationPointZ[indices[1]])
        self.pose["rot_angle"] = (weights[0]*fp.RotationAngle[indices[0]]
                                  + weights[1]*fp.RotationAngle[indices[1]])

        fp.ObjectPlacement = FreeCAD.Placement(
            FreeCAD.Vector(self.pose["position"][0],
                           self.pose["position"][1],
                           self.pose["position"][2]),
            FreeCAD.Rotation(FreeCAD.Vector(self.pose["rot_axis"][0],
                                            self.pose["rot_axis"][1],
                                            self.pose["rot_axis"][2]),
                             self.pose["rot_angle"]),
            FreeCAD.Vector(self.pose["rot_point"][0],
                           self.pose["rot_point"][1],
                           self.pose["rot_point"][2],))
        fp.Placement = fp.ParentFramePlacement.multiply(
                       fp.ObjectPlacement)

    def onDocumentRestored(self, fp):
        fp.ViewObject.Proxy.setProperties(fp.ViewObject)
        self.setProperties(fp)

    # supporting methods-------------------------------------------------------
    def setProperties(self, fp):

        self.pose = {"position":  (0, 0, 0),
                     "rot_axis":  (0, 0, 0),
                     "rot_point": (0, 0, 0),
                     "rot_angle": None}

        # Add (and preset) properties
        # Animation properties
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

        # Trajectory properties
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
                           "Frame axis arrow's arrowhead length."
                           ).FrameArrowheadLength = (10, 1.0, 1e6, 1)
        else:
            fp.FrameArrowheadLength = (fp.FrameArrowheadLength, 1.0, 1e6, 1)
        if not hasattr(fp, "FrameArrowheadRadius"):
            fp.addProperty("App::PropertyFloatConstraint",
                           "FrameArrowheadRadius", "Frame",
                           "Frame axis arrow's arrowhead bottom radius."
                           ).FrameArrowheadRadius = (5, 0.5, 1e6, 0.5)
        else:
            fp.FrameArrowheadRadius = (fp.FrameArrowheadRadius, 0.5, 1e6, 0.5)
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
        if not hasattr(fp, "ShowFrameLabels"):
            fp.addProperty("App::PropertyBool", "ShowFrameLabels",
                           "Frame", "Show label for frame axes."
                           ).ShowFrameLabels = True

        # Rotation axis properties
        if not hasattr(fp, "ShowRotationAxis"):
            fp.addProperty("App::PropertyBool", "ShowRotationAxis",
                           "RotationAxis",
                           "Show currently used rotation axis."
                           ).ShowRotationAxis = True
        if not hasattr(fp, "AxisLength"):
            fp.addProperty("App::PropertyFloatConstraint", "AxisLength",
                           "RotationAxis", "The rotation axis length."
                           ).AxisLength = (20, 1.0, 1e6, 1)
        else:
            fp.AxisLength = (fp.AxisLength, 1.0, 1e6, 1)
        if not hasattr(fp, "AxisWidth"):
            fp.addProperty("App::PropertyFloatConstraint", "AxisWidth",
                           "RotationAxis", "The rotation axis width."
                           ).AxisWidth = (4, 1.0, 64, 1)
        else:
            fp.AxisWidth = (fp.AxisWidth, 1.0, 64, 1)
        if not hasattr(fp, "AxisColor"):
            fp.addProperty("App::PropertyColor", "AxisColor",
                           "RotationAxis", "The rotation axis width."
                           ).AxisColor = (1.000, 0.667, 0.000)
        if not hasattr(fp, "AxisTransparency"):
            fp.addProperty("App::PropertyPercent", "AxisTransparency",
                           "RotationAxis",
                           "Transparency of the rotation axis in percents."
                           ).AxisTransparency = 0
        if not hasattr(fp, "ShowAxisArrowhead"):
            fp.addProperty("App::PropertyBool", "ShowAxisArrowhead",
                           "RotationAxis", "Show arrowhead for axis arrow."
                           ).ShowAxisArrowhead = True
        if not hasattr(fp, "AxisArrowheadLength"):
            fp.addProperty("App::PropertyFloatConstraint",
                           "AxisArrowheadLength", "RotationAxis",
                           "Frame axis arrow's arrowhead length."
                           ).AxisArrowheadLength = (10, 1.0, 1e6, 1)
        else:
            fp.AxisArrowheadLength = (fp.AxisArrowheadLength, 1.0, 1e6, 1)
        if not hasattr(fp, "AxisArrowheadRadius"):
            fp.addProperty("App::PropertyFloatConstraint",
                           "AxisArrowheadRadius", "RotationAxis",
                           "Frame axis arrow's arrowhead bottom radius."
                           ).AxisArrowheadRadius = (5, 0.5, 1e6, 0.5)
        else:
            fp.AxisArrowheadRadius = (fp.AxisArrowheadRadius, 0.5, 1e6, 0.5)
        if not hasattr(fp, "ShowAxisLabel"):
            fp.addProperty("App::PropertyBool", "ShowAxisLabel",
                           "RotationAxis", "Show label for rotation axis."
                           ).ShowAxisLabel = True

        # Label properties
        if not hasattr(fp, "FontSize"):
            fp.addProperty("App::PropertyIntegerConstraint", "FontSize",
                           "Labels", "Label font size."
                           ).FontSize = (10, 1, 100, 1)
        else:
            fp.FontSize = (fp.FontSize, 1, 100, 1)
        if not hasattr(fp, "DistanceToAxis"):
            fp.addProperty("App::PropertyFloatConstraint", "DistanceToAxis",
                           "Labels", "Distance from label to its axis."
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

        # Hide some properties
        fp.setEditorMode("Placement", 2)
        fp.setEditorMode("ValidTrajectory", 2)

        import AnimateDocumentObserver
        AnimateDocumentObserver.addObserver()

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
        # Check that trajectory has a correct format and load it
        if self.is_ValidTrajectory(trajectory=traj):
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

    def is_ValidTrajectory(self, timestamps=[], translation_x=[],
                           translation_y=[], translation_z=[],
                           rotation_point_x=[], rotation_point_y=[],
                           rotation_point_z=[], rotation_axis_x=[],
                           rotation_axis_y=[], rotation_axis_z=[],
                           rotation_angle=[], trajectory=None):
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
        # Check all keys are included and record lengths of their lists
        if trajectory is not None and isinstance(trajectory, dict):
            for key in ["Timestamps", "TranslationX", "TranslationY",
                        "TranslationZ", "RotationPointX", "RotationPointY",
                        "RotationPointZ", "RotationAxisX", "RotationAxisY",
                        "RotationAxisZ", "RotationAngle"]:
                if key not in trajectory.keys():
                    FreeCAD.Console.PrintWarning("Trajectory misses key " +
                                                 key + ".\n")
                    return False
            timestamps = trajectory["Timestamps"]
            translation_x = trajectory["TranslationX"]
            translation_y = trajectory["TranslationY"]
            translation_z = trajectory["TranslationZ"]
            rotation_point_x = trajectory["RotationPointX"]
            rotation_point_y = trajectory["RotationPointY"]
            rotation_point_z = trajectory["RotationPointZ"]
            rotation_axis_x = trajectory["RotationAxisX"]
            rotation_axis_y = trajectory["RotationAxisY"]
            rotation_axis_z = trajectory["RotationAxisZ"]
            rotation_angle = trajectory["RotationAngle"]

        # Check that all lists have the same length
        if len(timestamps) == 0 or \
                (len(timestamps) != 0 and
                 (len(timestamps) != len(timestamps) or
                  len(timestamps) != len(translation_x) or
                  len(timestamps) != len(translation_y) or
                  len(timestamps) != len(translation_z) or
                  len(timestamps) != len(rotation_point_x) or
                  len(timestamps) != len(rotation_point_y) or
                  len(timestamps) != len(rotation_point_z) or
                  len(timestamps) != len(rotation_axis_x) or
                  len(timestamps) != len(rotation_axis_y) or
                  len(timestamps) != len(rotation_axis_z) or
                  len(timestamps) != len(rotation_angle))):
            FreeCAD.Console.PrintWarning("Trajectory has lists with "
                                         + "inconsistent or zero "
                                         + "lengths.\n")
            return False

        # Check timestamps correspond to list of increasing values
        if any([timestamps[i] >= timestamps[i+1]
                for i in range(len(timestamps)-1)]):
            FreeCAD.Console.PrintWarning("Trajectory 'Timestamps' is not "
                                         + "list of increasing values.\n")
            return False

        if any([sum([rotation_axis_x[i]**2,
                     rotation_axis_y[i]**2,
                     rotation_axis_z[i]**2]) != 1
                for i in range(len(rotation_axis_x))]):
            FreeCAD.Console.PrintWarning("Trajectory 'Rotation Axis' "
                                         + "elements don't have norm 1.\n")
            return False

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


class ViewProviderTrajectoryProxy:
    """
    ViewProviderTrajectoryProxy is a Proxy object made to be connected to
    `Part::FeaturePython` Trajectory object's ViewObject.

    To connect them use:

    >>> a=FreeCAD.ActiveDocument.addObject("App::FeaturePython",
                                           "Trajectory")
    >>> ViewProviderTrajectoryProxy(a.ViewObject)
    """

    panel = None
    feature_python = None

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

        # prepare transformation to keep pose corresponding to placement
        self.tf_object2world = coin.SoTransform()

        labels = self.makeLabels()
        self.font = coin.SoFontStyle()

        axis = self.makeRotationAxis(labels[3])
        axis.insertChild(self.tf_object2world, 0)
        axis.insertChild(self.font, 1)
        self.rot_axis = coin.SoSwitch()
        self.rot_axis.addChild(axis)

        frame = self.makeFrame(labels[:3])
        frame.insertChild(self.tf_object2world, 0)
        frame.insertChild(self.font, 1)
        self.frame = coin.SoSwitch()
        self.frame.addChild(frame)

        self.visualisations = coin.SoSwitch()
        self.visualisations.addChild(self.rot_axis)
        self.visualisations.addChild(self.frame)
        vp.RootNode.addChild(self.visualisations)

        vp.Object.Proxy.setProperties(vp.Object)
        self.setProperties(vp)
        self.feature_python = vp.Object

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
        # Placement changes
        if prop == "Placement" and hasattr(fp, "Placement"):
            trans = fp.Placement.Base
            rot = fp.Placement.Rotation
            self.tf_object2world.translation.setValue((trans.x, trans.y,
                                                       trans.z))
            self.tf_object2world.rotation.setValue(rot.Q)
            if len(fp.Proxy.pose["rot_point"]) == 3 and \
                    len(fp.Proxy.pose["rot_axis"]) == 3:
                self.tf_y2axis.rotation.setValue(
                    coin.SbRotation(coin.SbVec3f(0, 1, 0),
                                    coin.SbVec3f(fp.Proxy.pose["rot_axis"][0],
                                                 fp.Proxy.pose["rot_axis"][1],
                                                 fp.Proxy.pose["rot_axis"][2])
                                    ))
                self.tf_y2axis.translation.setValue(
                        (fp.Proxy.pose["rot_point"][0],
                         fp.Proxy.pose["rot_point"][1],
                         fp.Proxy.pose["rot_point"][2]))

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

        # Axis changes
        elif prop == "ShowRotationAxis" and hasattr(fp, "ShowRotationAxis"):
            if fp.ShowRotationAxis:
                self.rot_axis.whichChild.setValue(coin.SO_SWITCH_ALL)
            else:
                self.rot_axis.whichChild.setValue(coin.SO_SWITCH_NONE)

        elif prop == "AxisTransparency" and \
                (hasattr(fp, "AxisColor") and hasattr(fp, "AxisTransparency")):
            self.rot_axis_color.orderedRGBA.setValue(
                (round(0xff*fp.AxisColor[0]) << 24)
                + (round(0xff*fp.AxisColor[1]) << 16)
                + (round(0xff*fp.AxisColor[2]) << 8)
                + 0xff*(100 - fp.AxisTransparency)//100)

        elif prop == "AxisColor" and \
                (hasattr(fp, "AxisColor") and hasattr(fp, "AxisTransparency")):
            self.rot_axis_color.orderedRGBA.setValue(
                (round(0xff*fp.AxisColor[0]) << 24)
                + (round(0xff*fp.AxisColor[1]) << 16)
                + (round(0xff*fp.AxisColor[2]) << 8)
                + 0xff*(100 - fp.AxisTransparency)//100)
            self.axis_label_color.orderedRGBA.setValue(
                (self.rot_axis_color.orderedRGBA.getValues()[0] & 0xFFFFFF00)
                + 0xFF)

        elif prop == "AxisWidth" and hasattr(fp, "AxisWidth"):
            self.rot_axis_drawstyle.lineWidth.setValue(fp.AxisWidth)

        elif prop == "AxisLength" and hasattr(fp, "AxisLength"):
            self.rot_axis_shaft.vertexProperty.getValue().vertex.\
                set1Value(1, 0, fp.AxisLength, 0)
            if hasattr(fp, "AxisArrowheadLength"):
                self.rot_axis_arrowhead_translation.translation.setValue(
                    0, fp.AxisLength + fp.AxisArrowheadLength/2, 0)
            if not fp.ShowAxisArrowhead and hasattr(fp, "DistanceToAxis"):
                self.label_translations[1].translation.setValue(
                    0, fp.AxisLength + fp.DistanceToAxis, 0)

        elif prop == "AxisArrowheadLength" and \
                hasattr(fp, "AxisArrowheadLength"):
            self.rot_axis_arrowhead_cone.height.setValue(
                fp.AxisArrowheadLength)
            if hasattr(fp, "AxisLength"):
                self.rot_axis_arrowhead_translation.translation.setValue(
                    0, fp.AxisLength + fp.AxisArrowheadLength/2, 0)
            if fp.ShowAxisArrowhead and hasattr(fp, "DistanceToAxis"):
                self.label_translations[1].translation.setValue(
                    0, fp.AxisArrowheadLength/2 + fp.DistanceToAxis, 0)

        elif prop == "AxisArrowheadRadius" and \
                hasattr(fp, "AxisArrowheadRadius"):
            self.rot_axis_arrowhead_cone.bottomRadius.setValue(
                fp.AxisArrowheadRadius)

        elif prop == "ShowAxisArrowhead" and hasattr(fp, "ShowAxisArrowhead"):
            if fp.ShowAxisArrowhead:
                self.rot_axis_arrowhead.whichChild.setValue(
                    coin.SO_SWITCH_ALL)
                if hasattr(fp, "AxisArrowheadLength") and \
                        hasattr(fp, "DistanceToAxis"):
                    self.label_translations[1].translation.setValue(
                        0, fp.AxisArrowheadLength/2 + fp.DistanceToAxis, 0)
            else:
                self.rot_axis_arrowhead.whichChild.setValue(
                    coin.SO_SWITCH_NONE)
                if hasattr(fp, "AxisLength") and hasattr(fp, "DistanceToAxis"):
                    self.label_translations[1].translation.setValue(
                        0, fp.AxisLength + fp.DistanceToAxis, 0)

        elif prop == "ShowAxisLabel" and hasattr(fp, "ShowAxisLabel"):
            if fp.ShowAxisLabel:
                self.labels[-1].whichChild.setValue(coin.SO_SWITCH_ALL)
            else:
                self.labels[-1].whichChild.setValue(coin.SO_SWITCH_NONE)

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
            if vp.Visibility:
                self.visualisations.whichChild.setValue(coin.SO_SWITCH_ALL)
            else:
                self.visualisations.whichChild.setValue(coin.SO_SWITCH_NONE)

    def claimChildren(self):
        if hasattr(self, "feature_python") and self.feature_python:
            return self.feature_python.Group
        return []

    def canDropObject(self, obj):
        if hasattr(obj, "Proxy") and \
           isinstance(obj.Proxy, self.feature_python.Proxy.__class__):
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

    def doubleClicked(self, vp):
        """
Double clicked.
        """
        # Switch to the Task View if a Trajectory panel is already opened
        if self.panel:
            FreeCADGui.Control.showTaskView()

        # Try to open new Trajectory panel
        else:
            # Check there is a valid trajectory
            if not vp.Object.ValidTrajectory:
                QMessageBox.warning(
                    None,
                    'Error while opening trajectory panel',
                    "Valid trajectory is necessary to open "
                    + "a trajectory panel.")

            # Load the QDialog from a file and name it after this object
            new_form = [FreeCADGui.PySideUic.loadUi(path.join(_PATH_UI,
                                                    "AnimationTrajectory.ui"))]
            new_form[0].setWindowTitle(vp.Object.Label)

            # Create a control panel and try to show it
            self.panel = ControlPanel([vp.Object], new_form)
            try:
                FreeCADGui.Control.showDialog(self.panel)
            except RuntimeError as e:
                # Reset the panel
                self.panel = None

                # Find all Trajectory feature python objects with
                # a reference to a Trajectory panel
                trajectories = []
                for obj in FreeCAD.ActiveDocument.Objects:
                    if hasattr(obj, "Proxy") and \
                            obj.Proxy.__class__.__name__ == "TrajectoryProxy":
                        if obj.ViewObject.Proxy.panel is not None:
                            trajectories.append(obj)

                if len(trajectories) > 0:
                    # Close opened Trajecotry panel
                    trajectories[0].ViewObject.Proxy.panel.reject()

                    # Load the QDialog form for each Trajectory which
                    # had a reference to the panel
                    forms = []
                    for trajectory in trajectories:
                        form = FreeCADGui.PySideUic.loadUi(
                                path.join(_PATH_UI, "AnimationTrajectory.ui"))
                        form.setWindowTitle(trajectory.Label)
                        forms.append(form)

                    # Load one more QDialog for this Trajectory
                    forms.append(new_form[0])

                    # Add this Trajectory to the list of trajectories
                    trajectories.append(vp.Object)

                    # Add a reference to the new panel to view providers
                    # of all trajectories
                    self.panel = ControlPanel(trajectories, forms)
                    for trajectory in trajectories:
                        trajectory.ViewObject.Proxy.panel = self.panel
                    FreeCADGui.Control.showDialog(self.panel)
                    return True

                # Diffeerent Task panel is opened, inform the user
                else:
                    QMessageBox.warning(
                        None,
                        'Error while opening trajectory panel',
                        "A different panel is already active.\n"
                        + "Close it before opening this one.")
                FreeCADGui.Control.showTaskView()
        return True

    def setupContextMenu(self, vp, menu):
        """
Method editing a context menu for right click on `FeaturePython` Server.

The *Transform* and *Set colors...* items are removed from the context menu
shown upon right click on `FeaturePython` Server in the Tree View.
The option to *Disconnect Server*, or *Connect Server* is added instead.

Args:
    vp: A right-clicked `Gui.ViewProviderDocumentObject` Server.ViewObject.
    menu: A Qt's QMenu to be edited.
        """
        menu.clear()
        action = menu.addAction("Select Time")
        action.triggered.connect(lambda f=self.doubleClicked,
                                 arg=vp: f(arg))

    def makeLabels(self):
        label_strings = ["X", "Y", "Z", "O"]
        colors = [0xFF0000FF, 0x00FF00FF, 0x0000FFFF]
        self.label_texts = []
        self.label_translations = []
        # frame translation
        self.label_translations.append(coin.SoTranslation())
        # axis translation
        self.label_translations.append(coin.SoTranslation())
        self.labels = []
        for i in range(4):
            label_group = coin.SoSeparator()
            if i < 3:
                label_group.addChild(self.label_translations[0])
                frame_axis_color = coin.SoPackedColor()
                frame_axis_color.orderedRGBA.setValue(colors[i])
                label_group.addChild(frame_axis_color)
            else:
                label_group.addChild(self.label_translations[1])
                self.axis_label_color = coin.SoPackedColor()
                label_group.addChild(self.axis_label_color)
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

    def makeRotationAxis(self, axis_label):
        # make a generic shaft from 0 in Y direction
        shaft_vertices = coin.SoVertexProperty()
        shaft_vertices.vertex.setNum(2)
        shaft_vertices.vertex.set1Value(0, 0, 0, 0)
        self.rot_axis_shaft = coin.SoLineSet()
        self.rot_axis_shaft.vertexProperty.setValue(shaft_vertices)
        self.rot_axis_shaft.numVertices.setNum(1)
        self.rot_axis_shaft.numVertices.setValue(2)

        # make a generic conic arrowhead oriented in Y axis direction and
        # move it at the end of the shaft
        self.rot_axis_arrowhead_translation = coin.SoTranslation()
        self.rot_axis_arrowhead_cone = coin.SoCone()
        self.rot_axis_arrowhead = coin.SoSwitch()
        self.rot_axis_arrowhead.addChild(self.rot_axis_arrowhead_translation)
        self.rot_axis_arrowhead.addChild(self.rot_axis_arrowhead_cone)

        # make rotations to rotate prepared shaft and arrowhead for Y axis
        # direction also to X and Z
        self.tf_y2axis = coin.SoTransform()

        # prepare colors for X,Y,Z which will correspond to R,G,B as customary
        self.rot_axis_color = coin.SoPackedColor()

        # prepare draw style to control shaft width
        self.rot_axis_drawstyle = coin.SoDrawStyle()

        # make complete frame and it to shaded display mode
        separated_axis = coin.SoSeparator()
        separated_axis.addChild(self.tf_y2axis)
        separated_axis.addChild(self.rot_axis_drawstyle)
        separated_axis.addChild(self.rot_axis_color)
        separated_axis.addChild(self.rot_axis_shaft)
        separated_axis.addChild(self.rot_axis_arrowhead)
        separated_axis.addChild(axis_label)

        return separated_axis


class TrajectoryCommand(object):
    """Create Object command"""

    def GetResources(self):
        return {'Pixmap': path.join(_PATH_ICONS, "TrajectoryCmd.xpm"),
                'MenuText': "Trajectory",
                'ToolTip': "Create Trajectory instance."}

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        a = doc.addObject("App::DocumentObjectGroupPython", "Trajectory")
        TrajectoryProxy(a)
        if FreeCAD.GuiUp:
            ViewProviderTrajectoryProxy(a.ViewObject)
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
