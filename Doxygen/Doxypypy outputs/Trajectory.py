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

##@package Trajectory
#Classes related to the Trajectory component of the Animate Workbench.
#
#The classes in this module provide funcionality for
#a `DocumentObjectGroupPython` Trajectory instance and creates a command to be
#used in a workbench.
#

import FreeCAD
import FreeCADGui

from PySide2.QtWidgets import QDialogButtonBox
from PySide2.QtWidgets import QMessageBox
from PySide2.QtCore import QObject
from bisect import bisect
from pivy import coin
from os import path

## Path to a folder with the necessary icons.
PATH_TO_ICONS = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                        "Icons")

## Path to a folder with the necessary user interface files.
PATH_TO_UI = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                     "UIs")

## @brief Class providing funcionality to a Trajectory panel inside the TaskView.
#
#This class enables user to see a manipulator in different configurations.
#It provides a dialogs to be shown in the TaskView. These dialogs have sliders
#which allow user to go through a trajectory.
#
#
#

class TrajectoryPanel(QObject):

    ## @property		trajectories
    # A list of `DocumentObjectGroupPython` Trajectory instances.

    ## @property		previous_times
    # A list of trajectory times before opening a panel.

    ## @property		form
    # A list of QDialog instances to show in the TaskView.

    ## @brief Initialization method for TrajectoryPanel.
    #
    #A class instance is created. A list of proxies for associated `Trajectory`
    #instances are loaded as well as corresponding QDialog forms.
    #Previously visible properties are set to be read-only as not to change when a
    #`TrajectoryPanel` is open. Finally all sliders on dialogs are moved to
    #a position corresponding to a `Trajectory` time.
    #
    #
    # @param		trajectories	A list of `DocumentObjectGroupPython` Trajectory instances.
    # @param		forms	A list of QDialog instances to show in the TaskView.
    #

    def __init__(self, trajectories, forms):
        super(TrajectoryPanel, self).__init__()
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

    ## @brief Feedback method called when any slider position is changed.
    #
    #A trajectory time is extrapolated from the slider position. The time is shown
    #on the dialog and set to a trajectory. Finally, the FreeCAD document and
    #the FreeCADGui document are updated.
    #
    #
    # @param		value	A slider position.
    # @param		form	A Dialog panel on which slider was moved.
    # @param		trajectory	A Trajectory associated with the `form`.
    #

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

    ## @brief Method used to close `TrajectoryPanel`.
    #
    #Trajectory properties are return to be editable/read-only/invisible as they
    #were before. After that `TrajectoryPanel` is closed.
    #

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

    ## @brief Feedback method called when 'Cancel' button was pressed to close the panel.
    #
    #Trajectory Times are set to the original values. `TrajectoryPanel` is closed.
    #FreeCAD and FreeCADGui documents are updated.
    #

    def reject(self):
        # Return Trajectory times to previous values
        for i in range(len(self.trajectories)):
            self.trajectories[i].Time = self.previous_times[i]

        # Close the panel and recompute the document to show changes
        self.close()
        FreeCAD.ActiveDocument.recompute()
        FreeCADGui.updateGui()

    ## @brief Feedback method called when 'OK' button was pressed to close the panel.
    #
    #Trajectory Times are saved. `TrajectoryPanel` is closed. FreeCAD and FreeCADGui
    #documents are updated.
    #

    def accept(self):
        # Close the panel
        self.close()

    ## @brief Method to set just one button (close) to close the dialog.
    #
    #
    #    *args: A tuple of unused arguments from Qt.
    #

    def getStandardButtons(self, *args):
        return QDialogButtonBox.Ok | QDialogButtonBox.Cancel

    ## @brief Method to tell FreeCAD if dialog is allowed to alter a selection.
    #
    # @return
    # @return		False	this dialog does not change a selection.
    #

    def isAllowedAlterSelection(self):
        return False

    ## @brief Method to tell FreeCAD if dialog is allowed to alter a view.
    #
    # @return
    # @return		True	this dialog does change a view.
    #

    def isAllowedAlterView(self):
        return True

    ## @brief Method to tell FreeCAD if dialog is allowed to alter a document.
    #
    # @return
    # @return		True	this dialog does change a document.
    #

    def isAllowedAlterDocument(self):
        return True


## @brief Proxy class for a `DocumentObjectGroupPython` Trajectory instance.
#
#A TrajectoryProxy instance adds properties to a `DocumentObjectGroupPython`
#Trajectory instance and responds to their changes. It provides
#a `TrajectoryPanel` to be able to see an object progress through a trajectory.
#
#
#
#To connect this `Proxy` object to a `DocumentObjectGroupPython` Trajectory do:
#
# @code
#        a = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroupPython",
#                                             "Trajectory")
#        TrajectoryProxy(a)
#

class TrajectoryProxy:

    ## @property		pose
    # A dict describing a pose - position, rotation axis, point and angle.

    ## @brief Initialization method for TrajectoryProxy.
    #
    #A class instance is created and made a `Proxy` for a generic
    #`DocumentObjectGroupPython` Trajectory object. During initialization number of
    #properties are specified and preset.
    #
    #
    # @param		fp	A `DocumentObjectGroupPython` Trajectory object to be extended.
    #

    def __init__(self, fp):
        # Add (and preset) properties
        self.setProperties(fp)
        fp.Proxy = self

    ## @brief Method called after `DocumentObjectGroupPython` Trajectory was changed.
    #
    #A trajectory is checked for its validity. If the `Placement` property is
    #changed, then `ParentFramePlacement` property of a `Trajectory` children is set
    #to equal the new `Placement`. If the `ParentFramePlacement` is changed, then
    #the `Placement` property is changed.
    #
    #
    # @param		fp	A `DocumentObjectGroupPython` Trajectory object.
    # @param		prop	A str name of a changed property.
    #

    def onChanged(self, fp, prop):
        # Check that a trajectory has valid format
        if self.is_trajectory_property(prop):
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

    ## @brief Method called when recomputing a `DocumentObjectGroupPython`.
    #
    #If a trajectory is valid, then current `pose` in a parent coordinate frame is
    #computed, `ObjectPlacement` and `Placement` are updated accordingly.
    #
    #
    # @param		fp	A `DocumentObjectGroupPython` Trajectory object.
    #

    def execute(self, fp):
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

    ## @brief Method called when document is restored to make sure everything is as it was.
    #
    # 	Reinitialization	it creates properties and sets them to
    #default, if they were not restored automatically. Properties of
    #connected `ViewObject` are also recreated and reset if necessary.
    #
    #
    # @param		fp	A restored `DocumentObjectGroupPython` Trajectory object.
    #

    def onDocumentRestored(self, fp):
        fp.ViewObject.Proxy.setProperties(fp.ViewObject)
        self.setProperties(fp)

    # supporting methods-------------------------------------------------------
    ## @brief Method to set properties during initialization or document restoration.
    #
    #The properties are set if they are not already present and an
    #`AnimateDocumentObserver` is recreated.
    #
    #
    # @param		fp	A restored or barebone `DocumentObjectGroupPython` Trajectory object.
    #

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
            fp.addProperty("App::PropertyLinkListGlobal", "AnimatedObjects",
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

    ## @brief Metod used to change a `Trajectory`'s trajectory.
    #
    #A `traj` dictionary containing a trajectory is tested for validity and then
    #assigned to a `Trajectory` `DocumentObjectGroupPython`.
    #
    #
    # @param		fp	A `DocumentObjectGroupPython` Trajectory object.
    # @param		traj	A dictionary describing a trajectory.
    #

    def change_trajectory(self, fp, traj):
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

    ## @brief Method to check that a property describes a trajectory.
    #
    #It's checked whether `prop` is `Timestamps`, `TranslationX`, `TranslationY`,
    #`TranslationZ`, `RotationPointX`, `RotationPointY`, `RotationPointZ`,
    #`RotationAxisX`, `RotationAxisY`, `RotationAxisZ` or `RotationAngle`.
    #
    #
    # @param		prop	A str name of a changed property.
    #
    # @return
    #    True if prop describes a trajectory and False otherwise.
    #

    def is_trajectory_property(self, prop):
        return prop in ["Timestamps", "TranslationX", "TranslationY",
                        "TranslationZ", "RotationPointX", "RotationPointY",
                        "RotationPointZ", "RotationAxisX", "RotationAxisY",
                        "RotationAxisZ", "RotationAngle"]

    ## @brief Method to check if a trajectory is valid.
    #
    #This method needs either a `trajectory` dictionary argument or all the other
    #lists of floats. A valid trajectory needs to have all the necessary lists.
    #All the lists must have same length. A `timestamps` list must consist of
    #a sequence of strictly increasing floats. A rotation axis must have always
    #length equal to 1.
    #
    #
    # @param		timestamps	A list of floats marking timestamps.
    # @param		translation_x	A list of floats signifying translations in X direction.
    # @param		translation_y	A list of floats signifying translations in Y direction.
    # @param		translation_z	A list of floats signifying translations in Z direction.
    # @param		rotation_point_x	A list of floats signifying rotation point X coordinates.
    # @param		rotation_point_y	A list of floats signifying rotation point Y coordinates.
    # @param		rotation_point_z	A list of floats signifying rotation point Z coordinates.
    # @param		rotation_axis_x	A list of floats signifying rotation axis X elements.
    # @param		rotation_axis_y	A list of floats signifying rotation axis Y elements.
    # @param		rotation_axis_z	A list of floats signifying rotation axis Z elements.
    # @param		rotation_angle	A list of floats signifying rotation angles.
    # @param		trajectory	A dict containing all lists above.
    #
    # @return
    #    True if trajectory is valid and False otherwise.
    #

    def is_ValidTrajectory(self, timestamps=[], translation_x=[],
                           translation_y=[], translation_z=[],
                           rotation_point_x=[], rotation_point_y=[],
                           rotation_point_z=[], rotation_axis_x=[],
                           rotation_axis_y=[], rotation_axis_z=[],
                           rotation_angle=[], trajectory=None):
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

    ## @brief Method to find weighted `timestamps` indices corresponding to a given `time`.
    #
    #If a `time` is smaller than the first timestamp, the returned indices are [0,0]
    #with weights [1,0] as that's the closest value. Simlarly, if the `time` is
    #greater than the last timestamp, the returned indices are [-1,-1] pointing to
    #the last element of a `timestamps` list with weights [1,0]. If the `time` value
    #is between the first and last timestamp, the indices belong to the closest
    #higher and lower time. At the same time, if interpolation is off, the weights
    #are 0 and 1, where one is given to the index closest to the `time`. Otherwise,
    #the weights, whose sum equals to 1, are computed to show inverse relative
    #distance i.e. an index with a greater weight is the closer.
    #
    #
    # @param		fp	A `DocumentObjectGroupPython` Trajectory object.
    #
    # @return
    # @return		indices	A list of two integers between -1 and and length of `Timestamps`.
    # @return		weights	A list of two floats between 0 and 1 showing relative closeness.
    #

    def find_timestamp_indices_and_weights(self, fp):
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


## @brief Proxy class for `Gui.ViewProviderDocumentObject` Trajectory.ViewObject.
#
#A ViewProviderTrajectoryProxy instance provides a Trajectory's icon,
#double-click response and context menu with a *Select Time* option.
#
#
#
#To connect this `Proxy` object to a `Gui.ViewProviderDocumentObject`
#Trajectory.ViewObject do:
#
# @code
#        a = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroupPython",
#                                             "Trajectory")
#        ViewProviderTrajectoryProxy(a.ViewObject)
#

class ViewProviderTrajectoryProxy:

    ## @property		fp
    # A Trajectory object.

    ## @property		panel
    # A TrajectoryPanel if one is active or None.

    ## @property		tf_object2world
    # A SoTransform transformation from object to world frame.

    ## @property		font
    # A SoFontStyle font for axes labels.

    ## @property		rot_axis
    # A SoSwitch with a rotation axis in form of an arrow.

    ## @property		frame
    # A SoSeparator with a coordinate frame made from 3 RGB arrows.

    ## @property		visualisations
    # A SoSwitch with all visualisations (frame & rotation axis).

    ## @property		label_texts
    # A list of `SoText2`s labels denoting all axes and an origin.

    ## @property		label_translations
    # A list of `SoTranslation`s moving labels.

    ## @property		labels
    # A list of `SoSwitch`es containing colored translated labels.

    ## @property		axis_label_color
    # A SoPackedColor coloring a rotational axis(RA) label.

    ## @property		frame_shaft
    # A SoLineSet shaft for frame axes.

    ## @property		frame_arrowhead_translation
    # A SoTranslation moving frame arrowheads.

    ## @property		frame_arrowhead_cone
    # A SoCone arrowhead cone for frame axes.

    ## @property		frame_arrowhead
    # A SoSwitch translated cone for frame axes.

    ## @property		frame_color_x
    # A SoPackedColor red color for an X axis.

    ## @property		frame_color_y
    # A SoPackedColor green color for an Y axis.

    ## @property		frame_color_z
    # A SoPackedColor blue color for an Z axis.

    ## @property		frame_drawstyle
    # A SoDrawStyle controlling frame axes shaft line width.

    ## @property		rot_axis_shaft
    # A SoLineSet shaft for a rotation axis.

    ## @property		rot_axis_arrowhead_translation
    # A SoTranslation moving a RA arrowhead.

    ## @property		rot_axis_arrowhead_cone
    # A SoCone arrowhead cone for a rotation axis.

    ## @property		rot_axis_arrowhead
    # A SoSwitch translated cone for a rotation axis.

    ## @property		tf_y2axis
    # A SoTransform transformation from Y axis to a rotation axis.

    ## @property		rot_axis_color
    # A SoPackedColor coloring a rotational axis.

    ## @property		rot_axis_drawstyle
    # A SoDrawStyle controlling RA shaft line width.

    panel = None
    fp = None

    # standard methods---------------------------------------------------------
    ## @brief Initialization method for ViewProviderTrajectoryProxy.
    #
    #A class instance is created and made a `Proxy` for a generic
    #`Gui.ViewProviderDocumentObject` Trajectory.ViewObject. During initialization
    #number of properties are specified and preset.
    #
    #
    # @param		vp	A barebone `Gui.ViewProviderDocumentObject` Trajectory.ViewObject.
    #

    def __init__(self, vp):
        self.setProperties(vp)
        vp.Proxy = self

    ## @brief Method called by FreeCAD after initialization to attach Coin3D constructs.
    #
    #A coordinate frame made of RGB arrows corresponding to X, Y and Z axes. This
    #frame shows current pose in a trajectory. This method adds Trajectory as
    #the `fp` attribute.
    #
    #
    # @param		vp	A Trajectory.ViewObject after initialization.
    #

    def attach(self, vp):
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
        self.fp = vp.Object

    ## @brief Method called after `DocumentObjectGroupPython` Trajectory was changed.
    #
    #This method is used to update Coin3D constructs, if associated properties
    #changed e.g. if the `FrameArrowheadRadius` changes, all Coin3D cones
    #representing frame arrowheads will change their radius accordingly.
    #
    #
    # @param		fp	A `DocumentObjectGroupPython` Trajectory object.
    # @param		prop	A str name of a changed property.
    #

    def updateData(self, fp, prop):
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

    ## @brief Method called after Trajectory.ViewObject was changed.
    #
    #If visibility changed, an appropriate Coin3D construct hides the frame showing
    #current pose.
    #
    #
    # @param		vp	A Trajectory.ViewObject.
    # @param		prop	A str name of a changed property.
    #

    def onChanged(self, vp, prop):
        if prop == "Visibility":
            if vp.Visibility:
                self.visualisations.whichChild.setValue(coin.SO_SWITCH_ALL)
            else:
                self.visualisations.whichChild.setValue(coin.SO_SWITCH_NONE)

    ## @brief Method called by FreeCAD to retrieve assigned children.
    #
    #When a property of a Trajectory is touched the Trajectory and the FreeCAD
    #ActiveDocument are notified. The FreeCAD ActiveDocument then emits a signal
    #to inform all its observers e.g. the FreeCADGui ActiveDocument. The FreeCADGui
    #document then emits a new signal to inform e.g. the tree view. The tree view
    #then invokes `claimChildren()`.
    #

    def claimChildren(self):
        if hasattr(self, "fp") and self.fp:
            return self.fp.Group
        return []

    ## @brief Method called by FreeCAD to ask if an object `obj` can be droped into a Group.
    #
    #Only FreeCAD objects of a Trajectory type are allowed to drop inside
    #a Trajectory group.
    #
    #
    # @param		obj	A FreeCAD object hovering above a Trajectory item in the Tree View.
    #

    def canDropObject(self, obj):
        if hasattr(obj, "Proxy") and \
           isinstance(obj.Proxy, self.fp.Proxy.__class__):
            return True
        return False

    ## @brief Method called by FreeCAD to supply an icon for the Tree View.
    #
    #A full path to an icon is supplied for the FreeCADGui.
    #
    # @return
    #    A str path to an icon.
    #

    def getIcon(self):
        return path.join(PATH_TO_ICONS, "Trajectory.xpm")

    ## @brief Necessary method to avoid errors when trying to save unserializable objects.
    #
    #This method is used by JSON to serialize unserializable objects during
    #autosave. Without this an Error would rise when JSON would try to do
    #that itself.
    #
    #We need this for unserializable `fp` attribute, but we don't
    #serialize it, because it's enough to reset it when object is restored.
    #
    # @return
    #    None, because we don't serialize anything.
    #

    def __getstate__(self):
        return None

    ## @brief Necessary method to avoid errors when trying to restore unserializable objects.
    #
    #This method is used during a document restoration. We need this for
    #unserializable `fp` attribute, but we do not restore it, because it's enough
    #to reset it.
    #

    def __setstate__(self, state):
        pass

    ## @brief Method to hide unused properties.
    #
    #Property Display Mode is set to be invisible as they are unused.
    #
    #
    # @param		vp	A `Gui.ViewProviderDocumentObject` Trajectory.ViewObject.
    #

    def setProperties(self, vp):
        # hide unnecessary view properties
        vp.setEditorMode("DisplayMode", 2)

    ## @brief Method called by FreeCAD when Trajectory is double-clicked in the Tree View.
    #
    #If no dialog is opened in the Task View, a new `TrajectoryPanel` is opened.
    #If another `TrajectoryPanel` is opened, it is closed and all its QDialogs
    #are added to a new `TrajectoryPanel`. If a `TrajectoryPanel` is already opened,
    #the Model tab on the Combo View is swaped for the Tasks tab so that the panel
    #becomes visible. If another dialog is opened a warning is shown.
    #
    #
    # @param		vp	A `Gui.ViewProviderDocumentObject` Trajectory.ViewObject.
    #

    def doubleClicked(self, vp):
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
            new_form = [FreeCADGui.PySideUic.loadUi(path.join(PATH_TO_UI,
                                                    "AnimationTrajectory.ui"))]
            new_form[0].setWindowTitle(vp.Object.Label)

            # Create a control panel and try to show it
            self.panel = TrajectoryPanel([vp.Object], new_form)
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
                                path.join(PATH_TO_UI,
                                          "AnimationTrajectory.ui"))
                        form.setWindowTitle(trajectory.Label)
                        forms.append(form)

                    # Load one more QDialog for this Trajectory
                    forms.append(new_form[0])

                    # Add this Trajectory to the list of trajectories
                    trajectories.append(vp.Object)

                    # Add a reference to the new panel to view providers
                    # of all trajectories
                    self.panel = TrajectoryPanel(trajectories, forms)
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

    ## @brief Method called by the FreeCAD to customize a context menu for a Trajectory.
    #
    #The *Transform* and *Set colors...* items are removed from the context menu
    #shown upon right click on `DocumentObjectGroupPython` Trajectory in the Tree
    #View. The option to *Select Time* is added instead.
    #
    #
    # @param		vp	A right-clicked `Gui.ViewProviderDocumentObject` Trajectory.ViewObject.
    # @param		menu	A Qt's QMenu to be edited.
    #

    def setupContextMenu(self, vp, menu):
        menu.clear()
        action = menu.addAction("Select Time")
        action.triggered.connect(lambda f=self.doubleClicked,
                                 arg=vp: f(arg))

    ## @brief Method which makes Coin3D labels to be displayed in the FreeCAD View.
    #
    #Frame labels for axes X, Y and Z and a label for rotation axis are made.
    #The labels have the same color as the axes.
    #
    # @return
    #    A SoSwitch with colored text label to be shown in the FreeCAD View.
    #

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

    ## @brief Method which makes a Coin3D frame to show a current pose in a trajectory.
    #
    #A frame is made from 3 red, green and blue arrows representing X, Y and Z.
    #Arrows are each constructed from a shaft and an arrowhead. Their dimensions
    #and other attributes are unassigned as they are extracted from appropriate
    #`Trajectory` properties.
    #
    # @return
    #    A SoSeparator with the frame shown in the FreeCAD View.
    #

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

    ## @brief Method which makes a Coin3D rotation axis to show in the FreeCAD View
    #
    #A rotation axis is made from a shaft and an arrowhead. Its dimensions
    #and other attributes are unassigned as they are extracted from appropriate
    #`Trajectory` properties.
    #
    # @return
    #    A SoSeparator with the rotation axis to be shown in the FreeCAD View.
    #

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


## @brief Class specifing Animate workbench's Trajectory button/command.
#
#This class provides resources for a toolbar button and a menu button.
#It controls their behaivor(Active/Inactive) and responds to callbacks after
#either of them was clicked(Activated).
#

class TrajectoryCommand(object):

    ## @brief Method used by FreeCAD to retrieve resources to use for this command.
    #
    # @return
    #    A dict with items `PixMap`, `MenuText` and `ToolTip` which contain
    #    a path to a command icon, a text to be shown in a menu and
    #    a tooltip message.
    #

    def GetResources(self):
        return {'Pixmap': path.join(PATH_TO_ICONS, "TrajectoryCmd.xpm"),
                'MenuText': "Trajectory",
                'ToolTip': "Create Trajectory instance."}

    ## @brief Method used as a callback when the toolbar button or the menu item is clicked.
    #
    #This method creates a Trajectory instance in currently active document.
    #Afterwards it adds a TrajectoryProxy as a `Proxy` to this instance as well as
    #ViewProviderTrajectoryProxy to its `ViewObject.Proxy`, if FreeCAD runs in the
    #Graphic mode.
    #

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        a = doc.addObject("App::DocumentObjectGroupPython", "Trajectory")
        TrajectoryProxy(a)
        if FreeCAD.GuiUp:
            ViewProviderTrajectoryProxy(a.ViewObject)
        doc.recompute()
        return

    ## @brief Method to specify when the toolbar button and the menu item are enabled.
    #
    #The toolbar button `Trajectory` and menu item `Trajectory` are set to be active
    #only when there is an active document in which a Trajectory instance can
    # be created.
    #
    # @return
    #    True if buttons shall be enabled and False otherwise.
    #

    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            return True


if FreeCAD.GuiUp:
    # Add command to FreeCAD Gui when importing this module in InitGui
    FreeCADGui.addCommand('TrajectoryCommand', TrajectoryCommand())
