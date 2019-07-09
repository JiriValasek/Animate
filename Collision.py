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

"""@package Collision
"""

import FreeCAD

from os import path

## Path to a folder with the necessary icons.
PATH_TO_ICONS = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                          "Icons")


class CollisionProxy(object):
    """
docstr
    """

    def __init__(self, feature_python, shape=None, cause1=None, cause2=None):
        """
docstr
        """
        if shape is not None:
            feature_python.Shape = shape
        if cause1 is not None and cause2 is not None:
            feature_python.Label = cause1.Label + " x " + cause2.Label
        self.setProperties(feature_python, cause1=cause1, cause2=cause2)
        feature_python.Proxy = self

    def onDocumentRestored(self, feature_python):
        """
docstr
        """
        self.setProperties(feature_python)
        feature_python.ViewObject.Proxy.setProperties(
            feature_python.ViewObject)

    def setProperties(self, feature_python, cause1=None, cause2=None):
        """
docstr
        """
        if not hasattr(feature_python, "CausedBy"):
            feature_python.addProperty(
                "App::PropertyLinkList", "CausedBy", "Collision",
                "Objects that made this collision").CausedBy = [cause1, cause2]
        if not hasattr(feature_python, "Volume"):
            feature_python.addProperty(
                    "App::PropertyVolume", "Volume", "Collision",
                    "Overlapping volume of interfering objects."
                    ).Volume = feature_python.Shape.Volume

        feature_python.setEditorMode("Placement", 1)
        feature_python.setEditorMode("CausedBy", 1)
        feature_python.setEditorMode("Volume", 1)
        feature_python.setEditorMode("Label", 1)

        # Add ViewObject to __dict__ so that it can be accessed using
        # __getattribute__
        feature_python.__dict__["ViewObject"] = feature_python.ViewObject


class ViewProviderCollisionProxy(object):
    """
docstr
    """

    _icon = path.join(PATH_TO_ICONS, "Server.xpm")

    def __init__(self, vp, color=None):
        """
docstr
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
docstr
        """
        return True

    def setupContextMenu(self, vp, menu):
        """
docstr
        """
        menu.clear()

    def getIcon(self):
        """
Method used to get a path to an icon which will appear in the tree view.

Returns:
    A path to the icon stored in `_icon`.
        """
        return self._icon

    def setProperties(self, vp):
        """
docstr
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
#        vp.setEditorMode("Transparency", 2)
#        vp.setEditorMode("Visibility", 2)

        self._icon = path.join(PATH_TO_ICONS, "Collision.png")
