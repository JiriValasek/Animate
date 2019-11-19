# -*- coding: utf-8 -*-

# ***************************************************************************
# *                                                                         *
# *   Animate workbench - FreeCAD Workbench for lightweight animation       *
# *   Copyright (c) 2019 Jiří Valášek jirka362@gmail.com                    *
# *                                                                         *
# *   This file is part of the Animate workbench.                           *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   Animate workbench is distributed in the hope that it will be useful,  *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Lesser General Public License for more details.                   *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with Animate workbench; if not, write to the Free       *
# *   Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,        *
# *   MA  02111-1307 USA                                                    *
# *                                                                         *
# ***************************************************************************/

##@package RobWorld
#Classes related to the RobWorld component of the Animate Workbench.
#
#The classes in this module provide funcionality for
#a `DocumentObjectGroupPython` RobWorld instance and creates a command to be
#used in a workbench.
#

import FreeCAD
import FreeCADGui

from pivy import coin
from os import path

## Path to a folder with the necessary icons.
PATH_TO_ICONS = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                          "Icons")


## @brief Proxy class for a `DocumentObjectGroupPython` RobWorld instance.
#
#A RobWorldProxy instance adds properties to a `DocumentObjectGroupPython`
#RobWorld instance and responds to their changes.
#
#
#To connect this `Proxy` object to a `DocumentObjectGroupPython` RobWorld do:
#
#        a = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroupPython",
#                                             "RobWorld")
#        RobWorldProxy(a)
#

class RobWorldProxy:

    ## @brief Initialization method for RobWorldProxy.
    #
    #A class instance is created and made a `Proxy` for a generic
    #`DocumentObjectGroupPython` RobWorld object. During initialization number of
    #properties are specified and preset.
    #
    #
    # @param		fp	A `DocumentObjectGroupPython` RobWorld object to be extended.
    #

    def __init__(self, fp):
        # Add (and preset) properties
        self.setProperties(fp)
        fp.Proxy = self

    ## @brief Method called after `DocumentObjectGroupPython` RobWorld was changed.
    #
    #A RobWorld is checked for its validity. If the `Placement` property is
    #changed, then `ParentFramePlacement` property of a `RobWorld`'s children is set
    #to equal the new `Placement`.
    #
    #
    # @param		fp	A `DocumentObjectGroupPython` RobWorld object.
    # @param		prop	A str name of a changed property.
    #

    def onChanged(self, fp, prop):
        if prop == "Placement":
            # Propagate the Placement updates down the chain
            if hasattr(fp, "Group") and len(fp.Group) != 0:
                for child in fp.Group:
                    child.ParentFramePlacement = fp.Placement
                    child.purgeTouched()

    ## @brief Method called when recomputing a `DocumentObjectGroupPython`.
    #
    #Placement is computed from Yaw, Pitch and Roll angle rotations about
    #Z, Y and X axes originating in (0, 0, 0).
    #
    #
    # @param		fp	A `DocumentObjectGroupPython` RobWorld object.
    #

    def execute(self, fp):
        rotation = FreeCAD.Rotation(fp.AngleYaw, fp.AnglePitch, fp.AngleRoll)
        rotation_center = FreeCAD.Vector(0, 0, 0)
        position = FreeCAD.Vector(fp.PositionX, fp.PositionY, fp.PositionZ)
        fp.Placement = FreeCAD.Placement(position, rotation, rotation_center)

    ## @brief Method called when document is restored to make sure everything is as it was.
    #
    # 	Reinitialization	it creates properties and sets them to
    #default, if they were not restored automatically. Properties of
    #connected `ViewObject` are also recreated and reset if necessary.
    #
    #
    # @param		fp	A restored `DocumentObjectGroupPython` RobWorld object.
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
    # @param		fp	A restored or barebone `DocumentObjectGroupPython` RobWorld object.
    #

    def setProperties(self, fp):
        # Add (and preset) properties
        # Animation properties
        if not hasattr(fp, "AllowServer"):
            fp.addProperty("App::PropertyBool", "AllowServer", "General",
                           "Should this object allow a Server object to "
                           + "change it.").AllowServer = True

        # Frame Placement
        if not hasattr(fp, "PositionX"):
            fp.addProperty("App::PropertyFloat", "PositionX", "FramePlacement",
                           "X position of the world frame.").PositionX = 0
        if not hasattr(fp, "PositionY"):
            fp.addProperty("App::PropertyFloat", "PositionY", "FramePlacement",
                           "Y position of the world frame.").PositionY = 0
        if not hasattr(fp, "PositionZ"):
            fp.addProperty("App::PropertyFloat", "PositionZ", "FramePlacement",
                           "Z position of the world frame.").PositionZ = 0
        if not hasattr(fp, "AngleYaw"):
            fp.addProperty("App::PropertyFloat", "AngleYaw", "FramePlacement",
                           "Yaw angle (rotation about Z axis) of the world"
                           + " frame in degrees.").AngleYaw = 0
        if not hasattr(fp, "AnglePitch"):
            fp.addProperty("App::PropertyFloat", "AnglePitch",
                           "FramePlacement", "Pitch angle (rotation about Y"
                           + " axis) of the world frame in degrees."
                           ).AnglePitch = 0
        if not hasattr(fp, "AngleRoll"):
            fp.addProperty("App::PropertyFloat", "AngleRoll", "FramePlacement",
                           "Roll angle (rotation about X axis) of the world"
                           + " frame in degrees.").AngleRoll = 0

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

        # Hide some properties
        fp.setEditorMode("Placement", 2)

        import AnimateDocumentObserver
        AnimateDocumentObserver.addObserver()


## @brief Proxy class for `Gui.ViewProviderDocumentObject` RobWorld.ViewObject.
#
#A ViewProviderRobWorldProxy instance provides a RobWorld's icon, and displays
#frame.
#
#
#
#To connect this `Proxy` object to a `Gui.ViewProviderDocumentObject`
#RobWorld.ViewObject do:
#
# @code
#        a = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroupPython",
#                                             "RobWorld")
#        ViewProviderRobWorldProxy(a.ViewObject)
#

class ViewProviderRobWorldProxy:

    ## @property		fp
    # A RobWorld object.

    ## @property		panel
    # A RobWorldPanel if one is active or None.

    ## @property		tf_object2world
    # A SoTransform transformation from object to world frame.

    ## @property		font
    # A SoFontStyle font for axes labels.

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

    panel = None
    fp = None

    # standard methods---------------------------------------------------------
    ## @brief Initialization method for ViewProviderRobWorldProxy.
    #
    #A class instance is created and made a `Proxy` for a generic
    #`Gui.ViewProviderDocumentObject` RobWorld.ViewObject. During initialization
    #number of properties are specified and preset.
    #
    #
    # @param		vp	A barebone `Gui.ViewProviderDocumentObject` RobWorld.ViewObject.
    #

    def __init__(self, vp):
        self.setProperties(vp)
        vp.Proxy = self

    ## @brief Method called by FreeCAD after initialization to attach Coin3D constructs.
    #
    #A coordinate frame made of RGB arrows corresponding to X, Y and Z axes. This
    #frame shows current pose in a RobWorld. This method adds RobWorld as
    #the `fp` attribute.
    #
    #
    # @param		vp	A RobWorld.ViewObject after initialization.
    #

    def attach(self, vp):
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
        self.visualisations.whichChild.setValue(coin.SO_SWITCH_ALL)
        vp.RootNode.addChild(self.visualisations)

        vp.Object.Proxy.setProperties(vp.Object)
        self.setProperties(vp)
        self.fp = vp.Object

    ## @brief Method called after `DocumentObjectGroupPython` RobWorld was changed.
    #
    #This method is used to update Coin3D constructs, if associated properties
    #changed e.g. if the `FrameArrowheadRadius` changes, all Coin3D cones
    #representing frame arrowheads will change their radius accordingly.
    #
    #
    # @param		fp	A `DocumentObjectGroupPython` RobWorld object.
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
                hasattr(fp, "ShowFrameArrowheads"):
            if fp.ShowFrameArrowheads and hasattr(fp, "FrameArrowheadLength"):
                self.label_translations[0].translation.setValue(
                    0, fp.FrameArrowheadLength/2 + fp.DistanceToAxis, 0)
            elif hasattr(fp, "ShaftLength"):
                self.label_translations[0].translation.setValue(
                    0, fp.ShaftLength + fp.DistanceToAxis, 0)

    ## @brief Method called after RobWorld.ViewObject was changed.
    #
    #If visibility changed, an appropriate Coin3D construct hides the frame showing
    #current pose.
    #
    #
    # @param		vp	A RobWorld.ViewObject.
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
    #When a property of a RobWorld is touched the RobWorld and the FreeCAD
    #ActiveDocument are notified. The FreeCAD ActiveDocument then emits a signal
    #to inform all its observers e.g. the FreeCADGui ActiveDocument. The FreeCADGui
    #document then emits a new signal to inform e.g. the tree view. The tree view
    #then invokes `claimChildren()`.
    #

    def claimChildren(self):
        if hasattr(self, "fp") and self.fp:
            return self.fp.Group
        return []

    ## @brief Method called by FreeCAD to ask if an object `obj` can be dropped into a Group.
    #
    #Only FreeCAD objects of a RobRotation and RobTranslation type are allowed to
    #drop inside a RobWorld group.
    #
    #
    # @param		obj	A FreeCAD object hovering above a RobWorld item in the Tree View.
    #

    def canDropObject(self, obj):
        if hasattr(obj, "Proxy") and \
           (obj.Proxy.__class__.__name__ == "RobRotationProxy" or
           obj.Proxy.__class__.__name__ == "RobTranslationProxy"):
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
        return path.join(PATH_TO_ICONS, "RobWorld.png")

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
    # @param		vp	A `Gui.ViewProviderDocumentObject` RobWorld.ViewObject.
    #

    def setProperties(self, vp):
        # hide unnecessary view properties
        vp.setEditorMode("DisplayMode", 2)

    ## @brief Method called by FreeCAD when RobWorld is double-clicked in the Tree View.
    #
    #The default behavior is blocked, because it does not make sense in given
    #context.
    #
    #
    # @param		vp	A `Gui.ViewProviderDocumentObject` RobWorld.ViewObject.
    #
    # @return
    # @return		True	confirmation that this method was implemented.
    #

    def doubleClicked(self, vp):
        return True

    ## @brief Method called by the FreeCAD to customize a context menu for a RobWorld.
    #
    #The *Transform* and *Set colors...* items are removed from the context menu
    #shown upon right click on `DocumentObjectGroupPython` RobWorld in the Tree
    #View.
    #
    #
    # @param		vp	A right-clicked `Gui.ViewProviderDocumentObject` RobWorld.ViewObject.
    # @param		menu	A Qt's QMenu to be edited.
    #

    def setupContextMenu(self, vp, menu):
        menu.clear()

    ## @brief Method which makes Coin3D labels to be displayed in the FreeCAD View.
    #
    #Frame labels for axes X, Y and Z are made.
    #The labels have the same color as the axes.
    #
    # @return
    #    A SoSwitch with colored text label to be shown in the FreeCAD View.
    #

    def makeLabels(self):
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

    ## @brief Method which makes a Coin3D frame to show a current pose in a RobWorld.
    #
    #A frame is made from 3 red, green and blue arrows representing X, Y and Z.
    #Arrows are each constructed from a shaft and an arrowhead. Their dimensions
    #and other attributes are unassigned as they are extracted from appropriate
    #`RobWorld` properties.
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


## @brief Class specifying Animate workbench's RobWorld button/command.
#
#This class provides resources for a toolbar button and a menu button.
#It controls their behaivor(Active/Inactive) and responds to callbacks after
#either of them was clicked(Activated).
#

class RobWorldCommand(object):

    ## @brief Method used by FreeCAD to retrieve resources to use for this command.
    #
    # @return
    #    A dict with items `PixMap`, `MenuText` and `ToolTip` which contain
    #    a path to a command icon, a text to be shown in a menu and
    #    a tooltip message.
    #

    def GetResources(self):
        return {'Pixmap': path.join(PATH_TO_ICONS, "RobWorldCmd.png"),
                'MenuText': "RobWorld",
                'ToolTip': "Create RobWorld instance."}

    ## @brief Method used as a callback when the toolbar button or the menu item is clicked.
    #
    #This method creates a RobWorld instance in currently active document.
    #Afterwards it adds a RobWorldProxy as a `Proxy` to this instance as well as
    #ViewProviderRobWorldProxy to its `ViewObject.Proxy`, if FreeCAD runs in the
    #Graphic mode.
    #

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        a = doc.addObject("App::DocumentObjectGroupPython", "RobWorld")
        RobWorldProxy(a)
        if FreeCAD.GuiUp:
            ViewProviderRobWorldProxy(a.ViewObject)
        doc.recompute()
        return

    ## @brief Method to specify when the toolbar button and the menu item are enabled.
    #
    #The toolbar button `RobWorld` and menu item `RobWorld` are set to be active
    #only when there is an active document in which a RobWorld instance can
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
    FreeCADGui.addCommand('RobWorldCommand', RobWorldCommand())
