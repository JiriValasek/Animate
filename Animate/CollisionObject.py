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

"""@package CollisionObject
Classes related to the Collision component of the Animate Workbench.

The classes in this module provides funcionality for a `FeaturePython`
Collision instance made to highlight overlapping shapes by a CollisionDetector.
"""

import FreeCAD

from os import path

## Path to a folder with the necessary icons.
PATH_TO_ICONS = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                          "Icons")


class CollisionProxy(object):
    """
Proxy class for a `FeaturePython` Collision instance.


To connect this `Proxy` object to a `DocumentObjectGroupPython`
CollisionDetector do:

        a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython",
                                             "Collision")
        CollisionProxy(a, shape, cause1, cause2)
    """

    def __init__(self, fp, shape=None, cause1=None, cause2=None):
        """
Initialization method for CollisionProxy.

A class instance is created and made a `Proxy` for a generic `FeaturePython`
Collision object. During initialization number of properties are specified and
preset. An object shape is supplied and the object is labeled so its known
which objects caused this `collision`.

Args:
    fp: A barebone `FeaturePython` Server object to be extended.
    shape: A `Solid` object defining the shape of an intersection.
    cause1: An FreeCAD object observed intersecting with the `cause2`.
    cause2: An FreeCAD object observed intersecting with the `cause1`.
        """
        if shape is not None:
            fp.Shape = shape
        if cause1 is not None and cause2 is not None:
            fp.Label = cause1.Label + " x " + cause2.Label
        self.setProperties(fp, cause1=cause1, cause2=cause2)
        fp.Proxy = self

    def onDocumentRestored(self, fp):
        """
Method called when document is restored to make sure everything is as it was.

Reinitialization method - it creates properties and sets them to
default values, if they were not restored automatically. Properties of
connected `ViewObject` are also recreated and reset if necessary.

Args:
    fp: A restored `FeaturePython` CollisionObject object.
        """
        self.setProperties(fp)
        fp.ViewObject.Proxy.setProperties(
            fp.ViewObject)

    def setProperties(self, fp, cause1=None, cause2=None):
        """
Method to set properties during initialization or document restoration.

The properties are set if they are not already present. Later they are set read
only, because an user is not allowed to edit any instance of
the CollisionObject.

Args:
    fp : A restored or barebone `FeaturePython` CollisionObject object.
        """
        if not hasattr(fp, "CausedBy"):
            fp.addProperty(
                "App::PropertyLinkList", "CausedBy", "Collision",
                "Objects that made this collision").CausedBy = [cause1, cause2]
        if not hasattr(fp, "Volume"):
            fp.addProperty(
                    "App::PropertyVolume", "Volume", "Collision",
                    "Overlapping volume of interfering objects."
                    ).Volume = fp.Shape.Volume

        fp.setEditorMode("Placement", 1)
        fp.setEditorMode("CausedBy", 1)
        fp.setEditorMode("Volume", 1)
        fp.setEditorMode("Label", 1)

        # Add ViewObject to __dict__ so that it can be accessed using
        # __getattribute__
        fp.__dict__["ViewObject"] = fp.ViewObject


class ViewProviderCollisionProxy(object):
    """
Proxy class for a `Gui.ViewProviderDocumentObject` Collision.ViewObject.

A ViewProviderServerProxy instance changes a `FeaturePython` Collision's icon.
It prevents user from transforming a `Collision` object after double-clicking
it in the Tree View. It also removes options to  *Transform* and
*Set colors...* from a context menu.

To connect this `Proxy` object to a `Gui.ViewProviderDocumentObject`
Collision.ViewObject do:

        a = FreeCAD.ActiveDocument.addObject("Part::FeaturePython",
                                             "Collision")
        CollisionProxy(a, shape, cause1, cause2)
    """

    def __init__(self, vp, color=None):
        """
Initialization method for ViewProviderCollisionProxy.

A class instance is created and made a `Proxy` for a generic
`Gui.ViewProviderDocumentObject` Collision.ViewObject. This method changes
`LineColor`, `PointColor`, ShapeColor`, `LineWidth` and `PointSize` properties
of a Collision instance and hides unnecessary unused View properties.

Args:
    vp: A barebone `Gui.ViewProviderDocumentObject` Collision.ViewObject.
    color: A tuple of floats specifying Point, Line and Shape RGB color.
        """
        if color is None:
            color = (1.0, 0.0, 0.0)
        vp.LineColor = vp.PointColor = vp.ShapeColor = color
        vp.LineWidth = 10.0
        vp.PointSize = 10.0
        self.setProperties(vp)
        vp.Proxy = self

    def doubleClicked(self, vp):
        """
Method called when CollisionDetector is double-clicked in the Tree View.

It just prevents user from accessing transformation panel and transforming
a `Collision` object. It's enough to just implement it and return `True` for
this purpose.

Args:
    vp: A double-clicked Collision.ViewObject.

Returns:
    True to specify that it was implemented and executed.
        """
        return True

    def setupContextMenu(self, vp, menu):
        """
Method editing a context menu for right click on a Collision.

The *Transform* and *Set colors...* items are removed from the context menu
shown upon right click on the Collision in the Tree View. This is done to
prevent user from transforming the `Collision` object or changing its color.

Args:
    vp: A right-clicked Collision.ViewObject.
    menu: A Qt's QMenu to be edited.
        """
        menu.clear()

    def getIcon(self):
        """
Method used to get a path to an icon which will appear in the tree view.

Returns:
    A path to the icon.
        """
        return path.join(PATH_TO_ICONS, "Collision.png")

    def setProperties(self, vp):
        """
Method to hide unused properties.

All unused unnecessary `FeaturePython`s properties are hidden except for
`Transparency` and `Visibility`.

Args:
    vp: A `Gui.ViewProviderDocumentObject` Collision.ViewObject.
        """
        vp.setEditorMode("AngularDeflection", 2)
        vp.setEditorMode("BoundingBox", 2)
        vp.setEditorMode("Deviation", 2)
        vp.setEditorMode("DisplayMode", 2)
        vp.setEditorMode("DrawStyle", 2)
        vp.setEditorMode("Lighting", 2)
        vp.setEditorMode("LineColor", 2)
        vp.setEditorMode("LineWidth", 2)
        vp.setEditorMode("PointColor", 2)
        vp.setEditorMode("PointSize", 2)
        vp.setEditorMode("Selectable", 2)
        vp.setEditorMode("SelectionStyle", 2)
        vp.setEditorMode("ShapeColor", 2)
