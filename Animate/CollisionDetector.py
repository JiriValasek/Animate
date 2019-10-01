
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
Classes related to the CollisionDetector component of the Animate Workbench.

The classes in this module provide funcionality for
a `DocumentObjectGroupPython` CollisionDetector instance and creates a command
to be used in a workbench.
"""

import FreeCAD
import FreeCADGui
import json

from CollisionObject import CollisionProxy, ViewProviderCollisionProxy
from PySide2.QtWidgets import QMessageBox
from PySide2.QtCore import QTimer
from os import path

## Path to a folder with the necessary icons.
PATH_TO_ICONS = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                          "Icons")


class CollisionDetectorProxy(object):
    """
Proxy class for a `DocumentObjectGroupPython` CollisionDetector instance.

A CollisionDetectorProxy instance adds properties to
a `DocumentObjectGroupPython` CollisionDetector instance and responds to theirs
changes. It detects collisions among `ObservedObjects`.

Attributes:
    command_queue: A list of commands interfering with Coin3D to execute later.
    observed_objects_before: An `ObservedObjects` property before change.
    in_collision: A set of objects which are in-collision together.
    collided: A set of objects which have collided since the last reset.
    original_styles: A dict of objects and their style original style.
    shape_info: A dict of objects, `Part object`s inside them and fused shapes.
    fp: A `DocumentObjectGroupPython` associated with the proxy.
    checking: A flag to signal collision checking is in progress.
    reseting: A flag to signal reseting objects to previous state.

To connect this `Proxy` object to a `DocumentObjectGroupPython`
CollisionDetector do:

        a = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroupPython",
                          "CollisionDetector")
        CollisionDetectorProxy(a)
    """
    command_queue = []

    def __init__(self, fp):
        """
Initialization method for CollsionDetectorProxy.

A class instance is created and made a `Proxy` for a generic
`DocumentObjectGroupPython` CollisionDetector object. During initialization
number of properties are specified and preset.

Args:
    fp: A barebone CollisionDetector object to be extended.
        """
        self.setProperties(fp)
        fp.Proxy = self

    def onDocumentRestored(self, fp):
        """
Method called when document is restored to make sure everything is as it was.

Reinitialization method - it creates properties and sets them to
default, if they were not restored automatically. Properties of
connected `ViewObject` are also recreated and reset if necessary.

Args:
    fp: A restored `DocumentObjectGroupPython` CollisionDetector object.
        """
        fp.ViewObject.Proxy.setProperties(fp.ViewObject)
        self.setProperties(fp)

    def onBeforeChange(self, fp, prop):
        """
Method called before `DocumentObjectGroupPython` CollisionDetector is changed.

A list of ObservedObjects is loaded to check which objects were added or
removed so that their style can be changed appropriately.

Args:
    fp: A `DocumentObjectGroupPython` CollisionDetector object.
    prop: A str of a property about to change.
        """
        if prop == "ObservedObjects":
            self.observed_objects_before = fp.ObservedObjects

    def onChanged(self, fp, prop):
        """
Method called after `DocumentObjectGroupPython` CollisionDetector was changed.

A list of ObservedObjects is loaded and checked for added or removed objects
so that their style can be changed appropriately.

Args:
    fp: A `DocumentObjectGroupPython` CollisionDetector object.
    prop: A str of a changed property.
        """
        # Check if an object was deleted/added from the ObservedObjects
        # and reset it to the original style/remember its style
        if prop == "ObservedObjects":
            removed_objects = set(self.observed_objects_before)\
                - set(fp.ObservedObjects)
            for obj in removed_objects:
                self.resetObject(obj)
            added_objects = set(fp.ObservedObjects) \
                - set(self.shape_info.keys())
            self.loadObjects(added_objects)
            # remember if all observed objects are valid
            fp.ValidObservedObjects = (set(self.shape_info.keys())
                                       == set(fp.ObservedObjects))

    def resetObject(self, object_):
        """
Method that resets style of an `object_` to what it was before.

The object can be a `Part::PartFeature`, a `group object` or a `Part object`.
Its Transparency, ShapeColor, LineColor and LineWidth are restored to previous
values.

Args:
    object_: An observed object.
        """
        # Check that object to be reset has shape info recorded.
        if object_ in self.shape_info.keys():
            # Go through all 'Part objects' inside
            for obj in self.shape_info.pop(object_)["objects"]:
                # Reset styles
                if obj.Name in self.original_styles.keys():
                    style = self.original_styles.pop(obj.Name)
                    obj.ViewObject.Transparency = style["Transparency"]
                    obj.ViewObject.ShapeColor = tuple(style["ShapeColor"])
                    obj.ViewObject.LineColor = tuple(style["LineColor"])
                    obj.ViewObject.LineWidth = style["LineWidth"]

    def loadObjects(self, objects, save_style=True):
        """
Adds shape info and loads object to restore them during reset.

Groups and GroupExtensions are explored and shapes inside are added to
the shape_info dictionary. Their styles are recorded.

Args:
    objects: A list or set of added objects.
        """
        # Go through objects
        for obj in objects:
            # Invalid object - No shape nor group
            if not hasattr(obj, "Shape") and not hasattr(obj, "Group"):
                QMessageBox.warning(
                    None,
                    'Error while checking collisions',
                    "Object " + obj.Label + " does not have a shape assigned."
                    + "\nNeither does it group objects which do.\n"
                    + "It is not possible to check its collisions.\n"
                    + "Remove it from the observed objects.")
            # Group object
            elif not hasattr(obj, "Shape") and hasattr(obj, "Group"):
                # Explore it
                groupobjects, groupshape = self.exploreGroup(obj)
                if groupshape is not None:
                    self.shape_info[obj] = {"objects": groupobjects,
                                            "shape": groupshape}
                    if save_style:
                        for obj in groupobjects:
                            self.original_styles[obj.Name] = {
                                "Transparency": obj.ViewObject.Transparency,
                                "ShapeColor": obj.ViewObject.ShapeColor,
                                "LineColor": obj.ViewObject.LineColor,
                                "LineWidth": obj.ViewObject.LineWidth}
                else:
                    QMessageBox.warning(
                        None,
                        'Error while checking collisions',
                        "Group " + obj.Label + " does not contain\n"
                        + "any objects with shapes assigned.\n"
                        + "It is not possible to check its collisions.\n"
                        + "Remove it from the observed objects.")
            # Regular object
            else:
                self.shape_info[obj] = {"objects": [obj],
                                        "shape": obj.Shape}
                if save_style:
                    self.original_styles[obj.Name] = {
                        "Transparency": obj.ViewObject.Transparency,
                        "ShapeColor": obj.ViewObject.ShapeColor,
                        "LineColor": obj.ViewObject.LineColor,
                        "LineWidth": obj.ViewObject.LineWidth}

    def execute(self, fp):
        """
Method called when recomputing a `DocumentObjectGroupPython` CollisionDetector.

Collisions are checked upon recompute.

Args:
    fp: A `DocumentObjectGroupPython` CollisionDetector object.
        """
        self.checkCollisions()

    def setProperties(self, fp):
        """
Method to set properties during initialization or document restoration.

The properties are set if they are not already present and an
`AnimateDocumentObserver` is recreated.

Args:
    fp: A restored or barebone CollisionDetector object.
        """
        if not hasattr(fp, "ValidObservedObjects"):
            fp.addProperty(
                "App::PropertyBool", "ValidObservedObjects", "General",
                "All objects are valid for collision detection"
                ).ValidObservedObjects = False
        # Add (and preset) properties
        if not hasattr(fp, "ObservedObjects"):
            fp.addProperty(
                "App::PropertyLinkListGlobal", "ObservedObjects", "General",
                "Objects that will be checked for intersections.")
        if not hasattr(fp, "RememberCollisions"):
            fp.addProperty(
                "App::PropertyBool", "RememberCollisions", "General",
                "Remember which objects collided and show them."
                ).RememberCollisions = True
        if not hasattr(fp, "CheckingLevel"):
            fp.addProperty("App::PropertyEnumeration", "CheckingLevel",
                           "General", "Levels of checking from coarse and\n"
                           + "fast (Bounding box) to slow but precise\n"
                           + "(Intersection volume). To see intersected area\n"
                           + "select 'Intersection volume visualizations'")
            fp.CheckingLevel = ["Bounding box",
                                "Shape distance",
                                "Intersection volume",
                                "Intersection volume visualizations"]
        # Intersection style
        if not hasattr(fp, "IntersectionColor"):
            fp.addProperty(
                "App::PropertyColor", "IntersectionColor", "IntersectionStyle",
                "Color for highlighting intersections."
                ).IntersectionColor = (1.0, 0.0, 0.0)

        # Style of objects in collision
        if not hasattr(fp, "InCollisionTransparency"):
            fp.addProperty(
                "App::PropertyPercent", "InCollisionTransparency",
                "In-CollisionStyle",
                "Transparency set to objects in collision."
                ).InCollisionTransparency = 50
        if not hasattr(fp, "InCollisionShapeColor"):
            fp.addProperty(
                "App::PropertyColor", "InCollisionShapeColor",
                "In-CollisionStyle",
                "Shape color for highlighting objects in collision."
                ).InCollisionShapeColor = (1.0, 0.667, 0.333)
        if not hasattr(fp, "InCollisionLineColor"):
            fp.addProperty(
                "App::PropertyColor", "InCollisionLineColor",
                "In-CollisionStyle",
                "Line color for highlighting objects in collision."
                ).InCollisionLineColor = (1.0, 0.667, 0.0)
        if not hasattr(fp, "InCollisionLineWidth"):
            fp.addProperty(
                "App::PropertyFloatConstraint", "InCollisionLineWidth",
                "In-CollisionStyle",
                "Line width for highlighting objects\n"
                + "in collision. Range is < 1 | 64 >."
                ).InCollisionLineWidth = (2, 1, 64, 1)
        else:
            fp.InCollisionLineWidth = (fp.InCollisionLineWidth, 2, 64, 1)

        # Style of collided objects
        if not hasattr(fp, "CollidedTransparency"):
            fp.addProperty(
                "App::PropertyPercent", "CollidedTransparency",
                "CollidedStyle", "Transparency set to collided objects."
                ).CollidedTransparency = 50
        if not hasattr(fp, "CollidedShapeColor"):
            fp.addProperty(
                "App::PropertyColor", "CollidedShapeColor", "CollidedStyle",
                "Color for highlighting objects which collided."
                ).CollidedShapeColor = (0.667, 0.333, 1.0)
        if not hasattr(fp, "CollidedLineColor"):
            fp.addProperty(
                "App::PropertyColor", "CollidedLineColor",
                "CollidedStyle",
                "Line color for highlighting objects in collision."
                ).CollidedLineColor = (0.667, 0.0, 1.0)
        if not hasattr(fp, "CollidedLineWidth"):
            fp.addProperty(
                "App::PropertyFloatConstraint",
                "CollidedLineWidth", "CollidedStyle",
                "Line width for highlighting objects"
                + "in collision. Range is < 1 | 64 >."
                ).CollidedLineWidth = (2, 1, 64, 1)
        else:
            fp.CollidedLineWidth = (fp.CollidedLineWidth, 2, 64, 1)

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
        if not hasattr(self, "shape_info") or \
                (hasattr(self, "shape_info") and
                 self.shape_info is None):
            self.shape_info = dict()
            self.loadObjects(fp.ObservedObjects, save_style=False)

        self.fp = fp
        self.checking = False
        self.reseting = False

        fp.setEditorMode("Group", 1)
        fp.setEditorMode("ValidObservedObjects", 2)
        fp.ValidObservedObjects = (set(self.shape_info.keys())
                                   == set(fp.ObservedObjects))

        import AnimateDocumentObserver
        AnimateDocumentObserver.addObserver()

    def checkCollisions(self):
        """
Method which checks for collisions among observed objects.

If observed objects are valid and checking is not already in progress,
the collision checking is started.
        """
        # Don't check if there are invalid objects
        if not self.fp.ValidObservedObjects:
            QMessageBox.warning(
                    None,
                    'Error while checking collisions',
                    "One or more objects to check for collisions "
                    + "don't have shapes attached, or are empty groups.")
            return

        # Don't check if reseting
        if self.reseting:
            FreeCAD.Console.PrintWarning("Can't check, Reseting!")
            return

        # Don't check if already checking
        if self.checking:
            FreeCAD.Console.PrintWarning("Already Checking!")
            return
        else:
            self.checking = True

        # Prepare sets for objects in-collision and not-in-collision(ok)
        in_collision = set()
        ok = set()

        # Remove previously detected collisions
        self.executeLater(None, self.fp.removeObjectsFromDocument, None)

        # No observed object present
        if len(self.fp.ObservedObjects) == 0:
            FreeCAD.Console.PrintWarning(
                "CollisionDetector observes no objects.\n")
            self.checking = False
            return

        # Only 1 observed object
        elif len(self.fp.ObservedObjects) == 1:
            FreeCAD.Console.PrintWarning(
                "CollisionDetector observes only 1 object.\n")
            ok.add(self.fp.ObservedObjects[0])
            self.visualize(ok, in_collision)
            self.checking = False
            return

        # Go through observed objects and update their placement
        for obj in self.fp.ObservedObjects:
            if len(self.shape_info[obj]["objects"]) >= 2:
                self.shape_info[obj]["shape"] = \
                    self.shape_info[obj]["objects"][0].Shape.fuse(
                        [o.Shape for o in self.shape_info[obj]["objects"][1:]])
                if hasattr(obj, "Placement"):
                    self.shape_info[obj]["shape"].Placement.Base = \
                        obj.Placement.Base
                    self.shape_info[obj]["shape"].Placement.Rotation = \
                        obj.Placement.Rotation

            elif hasattr(obj, "Placement"):
                self.shape_info[obj]["shape"] = obj.Shape

        # Go through observed objects and check for intersections
        for i in range(len(self.fp.ObservedObjects) - 1):
            for j in range(i+1, len(self.fp.ObservedObjects)):
                if self.intersection(self.fp.ObservedObjects[i],
                                     self.fp.ObservedObjects[j]):
                    in_collision.add(self.fp.ObservedObjects[i])
                    in_collision.add(self.fp.ObservedObjects[j])
                else:
                    ok.add(self.fp.ObservedObjects[i])
                    ok.add(self.fp.ObservedObjects[j])

        # make ok and in-collision disjoint
        ok.difference_update(in_collision)
        # visualize which objects are ok/in-collision/collided
        self.visualize(ok, in_collision)
        # set checking to false after all objects are truly removed and added
        self.executeLater(None, self.setChecking, False)

    def exploreGroup(self, group):
        """
Method to explore a `group` for all objects and shapes inside.

All object in the group are added to a `groupobjects` list and their shapes
are fused into a `groupshape`.

Args:
    group: A group object.

Returns:
    groupobjects: A list of objects in the `group`.
    groupshape: A shape fused from the shapes of `groupobjects` or None.
        """
        # Shapes of objects in the group
        shapes = []
        # Objects and groups to go through
        objects = group.Group
        i = 0
        while i < len(objects):
            # Object has a shape attached
            if hasattr(objects[i], "Shape"):
                shapes.append(objects[i].Shape)

            # Object has a group attached
            if hasattr(objects[i], "Group"):
                # Remove regular groups as their content is already between
                # objects
                if objects[i].__class__.__name__ == "DocumentObjectGroup":
                    objects.pop(i)

                # Go through content of other groups and add it
                else:
                    groupobjects, groupshape = self.exploreGroup(
                            objects.pop(i))
                    if groupshape is not None:
                        shapes.append(groupshape)
                        objects = objects[:i] + groupobjects + objects[i:]
                        i += len(groupobjects) - 1
            i += 1

        # There are shapes present in the group
        if len(shapes) != 0:
            # There are more than 2 shapes in the group
            if len(shapes) >= 2:
                shape = shapes[0].fuse(shapes[1:])
            else:
                shape = shapes[0]

            # Group has a placement property
            if hasattr(group, "Placement"):
                shape.Placement = group.Placement
            return objects, shape

        # No shapes in the group
        else:
            return objects, None

    def intersection(self, obj1, obj2):
        """
Method to check intersection between `obj1` and `obj2`.

Based on selected checking level this method checks for collisions and makes
an intersection object if required.

Args:
    obj1: An object to check for a mutual intersection.
    obj2: Another object to check for a mutual intersection.

Returns:
    groupobjects: A list of objects in the `group`.
    groupshape: A shape fused from the shapes of `groupobjects` or None.
        """
        # Check Bounding box is intersecting (the fastest and crudest)
        if not self.shape_info[obj1]["shape"].BoundBox.intersect(
                self.shape_info[obj2]["shape"].BoundBox):
            return False

        # Check the shortest distance between the shapes is 0
        if self.fp.CheckingLevel == "Shape distance" and \
                self.shape_info[obj1]["shape"].distToShape(
                self.shape_info[obj2]["shape"])[0] > 0:
            return False

        # If requested, check intersection volume, and show intersection
        if self.fp.CheckingLevel == "Intersection volume" or \
                self.fp.CheckingLevel == "Intersection volume visualizations":
            # Compute common volume to both objects
            intersection = self.shape_info[obj1]["shape"].common(
                    self.shape_info[obj2]["shape"])

            # Test common volume is not 0 i.e. objects are not just touching
            if intersection.Volume == 0:
                return False

            # Make an Collision object to show the intersection if asked for
            if self.fp.CheckingLevel == "Intersection volume visualizations":
                self.executeLater(None, self.makeCollisionObject,
                                  (intersection, obj1, obj2,
                                   self.fp.IntersectionColor))
        return True

    def makeCollisionObject(self, shape, cause1, cause2, color):
        """
Method to make a collision object and add it to the `CollisionDetector`.

Args:
    shape: A shape of a common volume between objects cause1 and cause2.
    cause1: An intersecting object.
    cause2: An intersecting object.
    color: A color assigned to the collision object.
        """
        # Add new object to the CollisionDetector
        collision = self.fp.newObject("Part::FeaturePython", "Collision")
        # Attach a Proxy ot it and it's ViewObject, then purge its touched flag
        CollisionProxy(collision, shape, cause1, cause2)
        ViewProviderCollisionProxy(collision.ViewObject, color)
        collision.purgeTouched()

    def visualize(self, ok, in_collision):
        """
Method to visualize which object are in-collision and which have collided.

Sets of collided and in-collision objects are kept up to date in this method.
Then these sets are highlighted using style properties (Transparency,
Shape Color, Line Color, Line Width).

Args:
    ok: A set of objects that are not in-collision.
    in_collision: A set of objects that are in-collision.
        """
        # Compute which objects are no longer in collision
        collided = self.in_collision.intersection(ok)
        # Add them to a set of objects which have collided
        self.collided = self.collided.union(collided)
        # Remove objects which no longer collide from a set for such objects
        self.in_collision.difference_update(collided)
        # Add new object which are in-collision to the set
        self.in_collision = self.in_collision.union(in_collision)

        # If collided objects shall be shown
        if self.fp.RememberCollisions:
            # show them
            for obj in collided:
                for o in self.shape_info[obj]["objects"]:
                    o.ViewObject.Transparency = self.fp.CollidedTransparency
                    o.ViewObject.ShapeColor = self.fp.CollidedShapeColor
                    o.ViewObject.LineColor = self.fp.CollidedLineColor
                    o.ViewObject.LineWidth = self.fp.CollidedLineWidth
        else:
            # otherwise reset them
            for obj in collided:
                for o in self.shape_info[obj]["objects"]:
                    style = self.original_styles[obj.Name]
                    o.ViewObject.Transparency = style["Transparency"]
                    o.ViewObject.ShapeColor = style["ShapeColor"]
                    o.ViewObject.LineColor = style["LineColor"]
                    o.ViewObject.LineWidth = style["LineWidth"]

        # Show objects in-collision
        for obj in in_collision:
            for o in self.shape_info[obj]["objects"]:
                o.ViewObject.Transparency = self.fp.InCollisionTransparency
                o.ViewObject.ShapeColor = self.fp.InCollisionShapeColor
                o.ViewObject.LineColor = self.fp.InCollisionLineColor
                o.ViewObject.LineWidth = self.fp.InCollisionLineWidth

    def reset(self):
        """
Method to reset CollisionDetector.

Deletes `CollisionObject`s and returns all `ObservedObjects` to their original
style.
        """
        if self.checking:
            FreeCAD.Console.PrintWarning("Can't reset, Checking!")
            return
        else:
            self.reseting = True
            self.executeLater(None, self.fp.removeObjectsFromDocument, None)
            for obj_name, style in self.original_styles.items():
                obj = FreeCAD.ActiveDocument.getObject(obj_name)
                obj.ViewObject.Transparency = style["Transparency"]
                obj.ViewObject.ShapeColor = tuple(style["ShapeColor"])
                obj.ViewObject.LineColor = tuple(style["LineColor"])
                obj.ViewObject.LineWidth = style["LineWidth"]
            self.in_collision = set()
            self.collided = set()
            # set reseting to false after all objects are truly removed
            self.executeLater(None, self.setReseting, False)

    def setChecking(self, value):
        """
Method necessary to be able to set `checking` attribute with delayed execution.

In order to be able to check when a Collision is deleted/moved by user instead
of a `CollisionDetector` instance owning it, it's necessary to set `checking`
attribute to `False` after all collisions are removed.

Args:
    value: A bool flagging that `CollisionDetector` is checking for Collisions.
        """
        self.checking = value

    def setReseting(self, value):
        """
Method necessary to be able to set `reseting` attribute with delayed execution.

In order to be able to check when a Collision is deleted/moved by user instead
of a `CollisionDetector` instance owning it, it's necessary to set `reseting`
attribute to `False` after all collisions are removed.

Args:
    value: A bool flagging that `CollisionDetector` is reseting Collisions.
        """
        self.reseting = value

    def executeLater(self, var, command, args):
        """
Method to postpone execution after coin is finished (and avoid crashing coin).

Removing objects is necessary to do using this method, otherwise coin will
crash. When using with variable or arguments, its crutial that they stay
available and unchanged until the command is executed.

Usage example:
        self.executeLater(None, self.fp.removeObjectsFromDocument, None)

Args:
    var: A variable to be assigned return value from a command or None.
    command: A command to be executed.
    args: A tuple or arguments to used in a command, an argument or None.
        """
        if isinstance(args, tuple):
            self.command_queue.append((var, command, args))
        elif args is None:
            self.command_queue.append((var, command, ()))
        else:
            self.command_queue.append((var, command, (args,)))
        QTimer.singleShot(0, self.executeCommandQueue)

    def executeCommandQueue(self):
        """
Method to execute queue of postponed commands so that coin does not crash.

Call this method using a singleshot timer. For the fastest execution set
time to 0.

Usage example:
        PySide2.QtCore.QTimer.singleShot(0, self.executeCommandQueue)

        """
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
Necessary method to save unserializable objects.

We use this to save `original_styles` dictionary, `collided` and `in_collision`
sets.

Returns:
    data: A JSON string representation of a Python data structure.
        """
        state = {"original_styles": self.original_styles,
                 "collided": [obj.Name for obj in self.collided],
                 "in_collision": [obj.Name for obj in self.in_collision]}
        data = json.JSONEncoder().encode(state)
        return data

    def __setstate__(self, data):
        """
Necessary method to restore unserializable objects when loading document.

We use this to restore `original_styles` dictionary, `collided` and
`in_collision` sets.

Args:
    data: A JSON string representation of a Python data structure.
        """
        state = json.JSONDecoder().decode(data)
        self.original_styles = state["original_styles"]
        self.collided = {FreeCAD.ActiveDocument.getObject(name)
                         for name in state["collided"]}
        self.in_collision = {FreeCAD.ActiveDocument.getObject(name)
                             for name in state["in_collision"]}


class ViewProviderCollisionDetectorProxy(object):
    """
Proxy class for `Gui.ViewProviderDocumentObject` CollisionDetector.ViewObject.

A ViewProviderCollisionDetectorProxy instance provides a CollisionDetector's
icon, double-click response and context menu with "Check collisions" and
"Reset collision display".

Attributes:
    fp: A CollisionDetector object.

To connect this `Proxy` object to a `Gui.ViewProviderDocumentObject`
CollisionDetector.ViewObject do:

        a = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroupPython",
                                             "CollisionDetector")
        ViewProviderCollisionDetectorProxy(a.ViewObject)
    """

    def __init__(self, vp):
        """
Initialization method for ViewProviderCollisionDetectorProxy.

A class instance is created and made a `Proxy` for a generic
`Gui.ViewProviderDocumentObject` CollisionDetector.ViewObject.
During initialization number of properties are specified and preset.

Args:
    vp: A barebone CollisionDetector.ViewObject.
        """
        vp.Proxy = self
        self.setProperties(vp)

    def onDelete(self, vp, subelements):
        """
Method called when CollisionDetector is about to be deleted.

This method is used to return observed objects to their original style.

Args:
    vp: A `Gui.ViewProviderDocumentObject` CollisionDEtector.ViewObject.
    subelements: An unused argument from C++ binding.

Returns:
    True to specify that it was implemented and executed.
        """
        vp.Object.Proxy.reset()
        return True

    def getIcon(self):
        """
Method used to get a path to an icon which will appear in the tree view.

Returns:
    A path to the icon.
        """
        return path.join(PATH_TO_ICONS, "CollisionDetector.png")

    def setProperties(self, vp):
        """
Method to hide properties and attach CollisionDetectorProxy.

This method is called during initialization or document restoration. All unused
unnecessary view properties are hidden.

Args:
    vp: A `Gui.ViewProviderDocumentObject` CollisionDetector.ViewObject.
        """
        # Hide unnecessary view properties
        vp.setEditorMode("DisplayMode", 2)
        vp.setEditorMode("Visibility", 2)

        # Add feature python as it's necessary to claimChildren
        self.fp = vp.Object

    def doubleClicked(self, vp):
        """
Method called when CollisionDetector is double-clicked in the Tree View.

It tries to check collisions.

Args:
    vp: A double-clicked CollisionDetector.ViewObject.

Returns:
    True to specify that it was implemented and executed.
        """
        # pass do something
        try:
            vp.Object.Proxy.checkCollisions()
        finally:
            return True

    def setupContextMenu(self, vp, menu):
        """
Method editing a context menu for right click on a CollisionDetector.

The *Transform* and *Set colors...* items are removed from the context menu
shown upon right click on CollisionDetector in the Tree View. The option to
*Check collisions*, or *Reset collision display* is added instead.

Args:
    vp: A right-clicked CollisionDetector.ViewObject.
    menu: A Qt's QMenu to be edited.
        """
        menu.clear()
        action = menu.addAction("Check collisions")
        action.triggered.connect(
            vp.Object.Proxy.checkCollisions)
        action = menu.addAction("Reset collision display")
        action.triggered.connect(vp.Object.Proxy.reset)

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
unserializable `fp` attribute, but we do not restore it,
because it's enough to reset it.

Returns:
    None, because we don't restore anything.
        """
        return None

    def claimChildren(self):
        """
Method necessary for maintaining a tree structure.

Returns:
    Group: A list of objects which are grouped by CollisionDetector.
        """
        if hasattr(self, "fp"):
            if self.fp:
                return self.fp.Group
        return []

    def canDropObject(self, obj):
        """
Method deciding which objects can be added to a CollisionDetector group.

Returns always False so that no foreign objects are added.

Args:
    obj: An object to be added inside the group.

Returns:
    False to signal any `obj` can't be added to a CollisionDetector group.
        """
        # Don't accept any objects
        return False


class CollisionDetectorCommand(object):
    """
Class specifing Animate workbench's CollisionDetector button/command.

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
        return {'Pixmap': path.join(PATH_TO_ICONS, "CollisionDetectorCmd.png"),
                'MenuText': "CollisionDetector",
                'ToolTip': "Create CollisionDetector instance."}

    def Activated(self):
        """
Method used as a callback when the toolbar button or the menu item is clicked.

This method creates a CollisionDetector instance in currently active
document. Afterwards it adds a CollisionDetectorProxy as a `Proxy` to this
instance as well as ViewProviderCollisionDetectorProxy to its
`ViewObject.Proxy`, if FreeCAD runs in the Graphic mode.
        """
        doc = FreeCAD.ActiveDocument
        a = doc.addObject("App::DocumentObjectGroupPython",
                          "CollisionDetector")
        CollisionDetectorProxy(a)
        if FreeCAD.GuiUp:
            ViewProviderCollisionDetectorProxy(a.ViewObject)
        doc.recompute()
        return

    def IsActive(self):
        """
Method to specify when the toolbar button and the menu item are enabled.

The toolbar button `CollisionDetector` and menu item `CollisionDetector` are
set to be active only when there is an active document in which
a CollisionDetector instance can be created.

Returns:
    True if buttons shall be enabled and False otherwise.
        """
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            return True


if FreeCAD.GuiUp:
    # Add command to FreeCAD Gui when importing this module in InitGui
    FreeCADGui.addCommand('CollisionDetectorCommand',
                          CollisionDetectorCommand())
