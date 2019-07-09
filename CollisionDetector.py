
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

"""@package CollisionDetector
Description
"""

import FreeCAD
import FreeCADGui
import json

from Collision import CollisionProxy, ViewProviderCollisionProxy
from PySide2.QtWidgets import QMessageBox
from PySide2.QtCore import QTimer, QObject
from DraftGui import todo
from os import path

## Path to a folder with the necessary icons.
_PATH_ICONS = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                        "Icons")

class CollisionDetectorProxy(object):
    """
docstr

Attributes
    in_collision
    collided
    original_styles
    timer
    """
    command_queue = []

    def __init__(self, feature_python):
        """
docstr
        """
        self.setProperties(feature_python)
        feature_python.Proxy = self

    def onDocumentRestored(self, feature_python):
        """
docstr
        """
        feature_python.ViewObject.Proxy.setProperties(
                feature_python.ViewObject)
        self.setProperties(feature_python)

    def onBeforeChange(self, feature_python, prop):
        """
docstr
        """
        # Remember ObservedObjects before change to test which size
        # change took place
        if prop == "ObservedObjects":
            self.observed_objects_before = feature_python.ObservedObjects

    def onChanged(self, feature_python, prop):
        """
docstr
        """
        # Check if an object was deleted from the ObservedObjects
        # and reset it to the original style
        if prop == "ObservedObjects":
            removed_objects = set(self.observed_objects_before)\
                - set(feature_python.ObservedObjects)
            for obj in removed_objects:
                if obj.Name in self.original_styles.keys():
                    style = self.original_styles.pop(obj.Name)
                    obj.ViewObject.Transparency = style["Transparency"]
                    obj.ViewObject.ShapeColor = tuple(style["ShapeColor"])
                    obj.ViewObject.LineColor = tuple(style["LineColor"])
                    obj.ViewObject.LineWidth = style["LineWidth"]
            added_objects = set(feature_python.ObservedObjects) \
                - set(self.observed_objects_before)
            for obj in added_objects:
                self.original_styles[obj.Name] = {
                    "Transparency": obj.ViewObject.Transparency,
                    "ShapeColor": obj.ViewObject.ShapeColor,
                    "LineColor": obj.ViewObject.LineColor,
                    "LineWidth": obj.ViewObject.LineWidth}

    def execute(self, feature_python):
        """
docstr
        """
        self.checkCollisions()

    def setProperties(self, feature_python):
        """
docstr
        """
        # Add (and preset) properties
        if not hasattr(feature_python, "ObservedObjects"):
            feature_python.addProperty(
                "App::PropertyLinkList", "ObservedObjects", "General",
                "Objects that will be checked for intersections.")
        if not hasattr(feature_python, "RememberCollisons"):
            feature_python.addProperty(
                "App::PropertyBool", "RememberCollisons", "General",
                "Remember which objects collided and show them."
                ).RememberCollisons = True
        # Intersection style
        if not hasattr(feature_python, "IntersectionColor"):
            feature_python.addProperty(
                "App::PropertyColor", "IntersectionColor", "IntersectionStyle",
                "Color for highlighting intersections."
                ).IntersectionColor = (1.0, 0.0, 0.0)

        # Style of objects in collision
        if not hasattr(feature_python, "InCollisionTransparency"):
            feature_python.addProperty(
                "App::PropertyPercent", "InCollisionTransparency",
                "In-CollisionStyle",
                "Transparency set to objects in collision."
                ).InCollisionTransparency = 50
        if not hasattr(feature_python, "InCollisionShapeColor"):
            feature_python.addProperty(
                "App::PropertyColor", "InCollisionShapeColor",
                "In-CollisionStyle",
                "Shape color for highlighting objects in collision."
                ).InCollisionShapeColor = (1.0, 0.667, 0.333)
        if not hasattr(feature_python, "InCollisionLineColor"):
            feature_python.addProperty(
                "App::PropertyColor", "InCollisionLineColor",
                "In-CollisionStyle",
                "Line color for highlighting objects in collision."
                ).InCollisionLineColor = (1.0, 0.667, 0.0)
        if not hasattr(feature_python, "InCollisionLineWidth"):
            feature_python.addProperty(
                "App::PropertyFloatConstraint", "InCollisionLineWidth",
                "In-CollisionStyle",
                "Line width for highlighting objects in collision."
                ).InCollisionLineWidth = (2, 1, 64, 1)
        else:
            feature_python.InCollisionLineWidth = \
                (feature_python.InCollisionLineWidth, 2, 64, 1)

        # Style of collided objects
        if not hasattr(feature_python, "CollidedTransparency"):
            feature_python.addProperty(
                "App::PropertyPercent", "CollidedTransparency",
                "CollidedStyle", "Transparency set to collided objects."
                ).CollidedTransparency = 50
        if not hasattr(feature_python, "CollidedShapeColor"):
            feature_python.addProperty(
                "App::PropertyColor", "CollidedShapeColor", "CollidedStyle",
                "Color for highlighting objects which collided."
                ).CollidedShapeColor = (0.667, 0.333, 1.0)
        if not hasattr(feature_python, "CollidedLineColor"):
            feature_python.addProperty(
                "App::PropertyColor", "CollidedLineColor",
                "CollidedStyle",
                "Line color for highlighting objects in collision."
                ).CollidedLineColor = (0.667, 0.0, 1.0)
        if not hasattr(feature_python, "CollidedLineWidth"):
            feature_python.addProperty(
                "App::PropertyFloatConstraint",
                "CollidedLineWidth", "CollidedStyle",
                "Line width for highlighting objects in collision."
                ).CollidedLineWidth = (2, 1, 64, 1)
        else:
            feature_python.CollidedLineWidth = \
                (feature_python.CollidedLineWidth, 2, 64, 1)

        if not hasattr(self, "in_collision") or \
                (hasattr(self, "in_collision") and self.in_collision is None):
            self.in_collision = set()
        if not hasattr(self, "collided") or \
                (hasattr(self, "collided") and self.collided is None):
            self.collided = set()
        if not hasattr(self, "original_styles") or \
                (hasattr(self, "original_styles") and
                 self.original_styles is None):
            self.original_styles = dict()

        self.feature_python = feature_python
        self.checking = False
        self.reseting = False
        self.last_collision = None
        self.last_collision_viewobject = None

        feature_python.setEditorMode("Group", 1)

        import AnimateDocumentObserver
        AnimateDocumentObserver.addObserver()

    def checkCollisions(self):
        if self.checking:
            print("Already Checking!")
            return
        else:
            self.checking = True

        # Find new collisons
        in_collision = set()
        ok = set()

        if len(self.feature_python.ObservedObjects) == 0:
            FreeCAD.Console.PrintWarning(
                "CollisionDetector observes no objects.\n")
            self.executeLater(
                None, self.feature_python.removeObjectsFromDocument, None)
            self.checking = False
            return
        elif len(self.feature_python.ObservedObjects) == 1:
            FreeCAD.Console.PrintWarning(
                "CollisionDetector observes only 1 object.\n")
            self.executeLater(
                None, self.feature_python.removeObjectsFromDocument, None)
            ok.add(self.feature_python.ObservedObjects[0])
            self.visualize(ok, in_collision)
            self.checking = False
            return

        for obj in self.feature_python.ObservedObjects:
            if not hasattr(obj, "Shape"):
                QMessageBox.warning(
                    None,
                    'Error while opening checking collisions',
                    "Object " + obj.Label + " does not have a shape assigned."
                    + "\nIt is not possible to chech its collisions.\n"
                    + "Remove it from the observed objects.")
                self.checking = False
                return

        self.executeLater(
            None, self.feature_python.removeObjectsFromDocument, None)

        for i in range(len(self.feature_python.ObservedObjects) - 1):
            for j in range(i+1, len(self.feature_python.ObservedObjects)):
                if self.intersection(self.feature_python.ObservedObjects[i],
                                     self.feature_python.ObservedObjects[j]):
                    in_collision.add(self.feature_python.ObservedObjects[i])
                    in_collision.add(self.feature_python.ObservedObjects[j])
                else:
                    ok.add(self.feature_python.ObservedObjects[i])
                    ok.add(self.feature_python.ObservedObjects[j])

        # make ok and in_collision disjoint
        ok.difference_update(in_collision)
        self.visualize(ok, in_collision)
        self.checking = False

    def intersection(self, obj1, obj2):
        """
docstr
        """
        if not obj1.Shape.BoundBox.intersected(obj2.Shape.BoundBox):
            return False

        if obj1.Shape.distToShape(obj2.Shape)[0] > 0:
            return False

        intersection = obj1.Shape.common(obj2.Shape)
        if intersection.Volume == 0:
            return False

        self.executeLater(None,
                          self.makeCollisionObject,
                          (intersection, obj1, obj2,
                           self.feature_python.IntersectionColor))
        return True

    def makeCollisionObject(self, shape, cause1, cause2, color):
        """
docstr
        """
        collision = self.feature_python.newObject(
                "Part::FeaturePython", "Collision")
        CollisionProxy(collision, shape, cause1, cause2)
        ViewProviderCollisionProxy(collision.ViewObject, color)
        collision.purgeTouched()

    def visualize(self, ok, in_collision):
        # Compute which object are no longer in collision
        collided = self.in_collision.intersection(ok)
        # Add them to a set of object which have collided
        self.collided = self.collided.union(collided)
        # Remove objects which no longer collide from a set for such objects
        self.in_collision.difference_update(collided)
        # Add new object which are in-collision to the set
        self.in_collision = self.in_collision.union(in_collision)

        if self.feature_python.RememberCollisons:
            for obj in collided:
                obj.ViewObject.Transparency = \
                    self.feature_python.CollidedTransparency
                obj.ViewObject.ShapeColor = \
                    self.feature_python.CollidedShapeColor
                obj.ViewObject.LineColor = \
                    self.feature_python.CollidedLineColor
                obj.ViewObject.LineWidth = \
                    self.feature_python.CollidedLineWidth
        else:
            for obj in collided:
                style = self.original_styles[obj.Name]
                obj.ViewObject.Transparency = style["Transparency"]
                obj.ViewObject.ShapeColor = style["ShapeColor"]
                obj.ViewObject.LineColor = style["LineColor"]
                obj.ViewObject.LineWidth = style["LineWidth"]

        for obj in in_collision:
            obj.ViewObject.Transparency = \
                self.feature_python.InCollisionTransparency
            obj.ViewObject.ShapeColor = \
                self.feature_python.InCollisionShapeColor
            obj.ViewObject.LineColor = \
                self.feature_python.InCollisionLineColor
            obj.ViewObject.LineWidth = \
                self.feature_python.InCollisionLineWidth

    def reset(self):
        if self.checking:
            FreeCAD.Console.PrintWarning("Can't reset, Checking!")
            return
        else:
            self.reseting = True
            self.executeLater(
                None, self.feature_python.removeObjectsFromDocument, None)
            for obj_name, style in self.original_styles.items():
                obj = FreeCAD.ActiveDocument.getObject(obj_name)
                obj.ViewObject.Transparency = style["Transparency"]
                obj.ViewObject.ShapeColor = tuple(style["ShapeColor"])
                obj.ViewObject.LineColor = tuple(style["LineColor"])
                obj.ViewObject.LineWidth = style["LineWidth"]
            self.in_collision = set()
            self.collided = set()
            self.reseting = False

    def executeLater(self, var, command, args):
        if isinstance(args, tuple):
            self.command_queue.append((var, command, args))
        elif args is None:
            self.command_queue.append((var, command, ()))
        else:
            self.command_queue.append((var, command, (args,)))
        QTimer.singleShot(0, self.executeCommandQueue)

    def executeCommandQueue(self):
        try:
            for var, cmd, args in self.command_queue:
                try:
                    if var is not None:
                        cmd(*args)
                    else:
                        var = cmd(*args)
                except Exception as e:
                    FreeCAD.Console.PrintWarning(
                        "CollisionDetector: Executing a command in the "
                        + "command_queue.\n")
                    FreeCAD.Console.PrintWarning(str(e) + "\n")
        except ReferenceError as e:
            FreeCAD.Console.PrintLog(
                "CollisionDetector: Deleted object in the command_queue.\n")
        self.command_queue = []

    def __getstate__(self):
        """
docstr
        """
        state = {"original_styles": self.original_styles,
                 "collided": [obj.Name for obj in self.collided],
                 "in_collision": [obj.Name for obj in self.in_collision]}
        data = json.JSONEncoder().encode(state)
        return data

    def __setstate__(self, data):
        """
docstr
        """
        state = json.JSONDecoder().decode(data)
        self.original_styles = state["original_styles"]
        self.collided = {FreeCAD.ActiveDocument.getObject(name)
                         for name in state["collided"]}
        self.in_collision = {FreeCAD.ActiveDocument.getObject(name)
                             for name in state["in_collision"]}


class ViewProviderCollisionDetectorProxy(object):
    """
docstr
    """

    panel = None
    feature_python = None

    def __init__(self, view_provider):
        """
docstr
        """
        self.setProperties(view_provider)
        view_provider.Proxy = self

    def attach(self, view_provider):
        """
docstr
        """
        # Add feature python as it's necessary to claimChildren
        self.feature_python = view_provider.Object

    def onDelete(self, view_provider, subelements):
        """
docstr
        """
        view_provider.Object.Proxy.reset()
        return True

    def getIcon(self):
        """
        Get the icon in XMP format which will appear in the trv_sequences view.
        """
        return path.join(_PATH_ICONS, "CollisionDetector.png")

    def setProperties(self, view_provider):
        """
docstr
        """
        # Hide unnecessary view properties
        view_provider.setEditorMode("DisplayMode", 2)
        view_provider.setEditorMode("Visibility", 2)

    def doubleClicked(self, view_provider):
        """
Double clicked.
        """
        # pass do something
        view_provider.Object.Proxy.checkCollisions()
        return True

    def setupContextMenu(self, view_provider, menu):
        """
docstr
        """
        menu.clear()
        action = menu.addAction("Check collisions")
        action.triggered.connect(
            view_provider.Object.Proxy.checkCollisions)
        action = menu.addAction("Reset collision display")
        action.triggered.connect(view_provider.Object.Proxy.reset)

    def __getstate__(self):
        """
docstr
        """
        return None

    def __setstate__(self, state):
        """
docstr
        """
        return None

    def claimChildren(self):
        """
docstr
        """
        if hasattr(self, "feature_python"):
            if self.feature_python:
                return self.feature_python.Group
        return []

    def canDropObject(self, obj):
        """
docstr
        """
        # Don't accept any objects
        return False


class CollisionDetectorCommand(object):
    """Create Object command"""

    def GetResources(self):
        return {'Pixmap': path.join(_PATH_ICONS, "CollisionDetectorCmd.png"),
                'MenuText': "CollisionDetector",
                'ToolTip': "Create CollisionDetector instance."}

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        a = doc.addObject("App::DocumentObjectGroupPython", "CollisionDetector")
        CollisionDetectorProxy(a)
        if FreeCAD.GuiUp:
            ViewProviderCollisionDetectorProxy(a.ViewObject)
        doc.recompute()
        return

    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            return True

    def getHelp(self):
        return ["This is help for  Control\n",
                "and it needs to be written."]


if FreeCAD.GuiUp:
    FreeCADGui.addCommand('CollisionDetectorCommand',
                          CollisionDetectorCommand())
