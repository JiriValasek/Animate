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
Created on Tue Jun 25 19:53:58 2019

@author: jirka
"""

import FreeCAD


from PySide2.QtWidgets import QMessageBox

ANIMATE_OBJECT_GROUP_CLASSES = ["TrajectoryProxy", "ControlProxy"]
ANIMATE_CLASSES = ["TrajectoryProxy", "ControlProxy", "ServerProxy"]
ALLOWED_IN_CONTROL = ["TrajectoryProxy", "ServerProxy"]


class AnimateDocumentObserver(object):

    __instance = None
    group_before = None
    serverProxies = {}

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super(AnimateDocumentObserver,
                                   cls).__new__(cls, *args, **kwargs)
        return cls.__instance

    def slotBeforeChangeObject(self, obj, prop):
        if prop == "Group":
            self.group_before = obj.Group
            FreeCAD.ActiveDocument.openTransaction()

    def slotChangedObject(self, obj, prop):
        if prop == "Group" and len(obj.Group) > len(self.group_before):
            new_obj = obj.Group[-1]
            if self.isAnimateGroup(obj):
                if self.foreignObjectInAnimateGroup(new_obj, obj):
                    QMessageBox.warning(
                            None, 'Forbidden action detected',
                            "Group objects from Animate workbench can group\n"
                            + "only selected objects from Animate workbench.\n"
                            + "Check the user guide for more info.")
                    FreeCAD.ActiveDocument.undo()
                else:
                    FreeCAD.ActiveDocument.commitTransaction()
            else:
                if self.animateObjectInForeignGroup(new_obj, obj):
                    QMessageBox.warning(
                            None, 'Forbidden action detected',
                            "Objects from Animate workbench can be grouped\n"
                            + "only by selected objects from Animate "
                            + "workbench.\nCheck the user guide "
                            + "for more info.")
                    FreeCAD.ActiveDocument.undo()
                else:
                    FreeCAD.ActiveDocument.commitTransaction()

    def isAnimateGroup(self, obj):
        if not hasattr(obj, "Proxy"):
            return False
        elif obj.Proxy.__class__.__name__ not in ANIMATE_OBJECT_GROUP_CLASSES:
            return False
        else:
            return True

    def isAnimateObject(self, obj):
        if not hasattr(obj, "Proxy"):
            return False
        elif obj.Proxy.__class__.__name__ not in ANIMATE_CLASSES:
            return False
        else:
            return True

    def foreignObjectInAnimateGroup(self, obj, group):
        if group.Proxy.__class__.__name__ == "TrajectoryProxy" and \
                hasattr(obj, "Proxy") and \
                obj.Proxy.__class__.__name__ == "TrajectoryProxy":
            return False
        elif group.Proxy.__class__.__name__ == "ControlProxy" and \
                hasattr(obj, "Proxy") and \
                obj.Proxy.__class__.__name__ in ALLOWED_IN_CONTROL:
            return False
        return True

    def animateObjectInForeignGroup(self, obj, group):
        return not self.isAnimateGroup(group) and self.isAnimateObject(obj)

    def slotDeletedDocument(self, doc):
        """
Qt slot method called if a document is about to be closed.

This method is used to notify ServerProxy `sp` that document will be closed.

Args:
    doc: A FreeCAD's `App.Document` document about to be closed.
        """
        if doc.Name in self.serverProxies:
            for server_proxy in self.serverProxies[doc.Name]:
                server_proxy.onDocumentClosed()

    def addServerToNotify(self, server_proxy, document_name):
        if document_name in self.serverProxies:
            if server_proxy not in self.serverProxies[document_name]:
                self.serverProxies[document_name].append(server_proxy)
        else:
            self.serverProxies[document_name] = [server_proxy]


def addObserver():
    if not hasattr(FreeCAD, "animate_observer"):
        FreeCAD.animate_observer = AnimateDocumentObserver()
        FreeCAD.addDocumentObserver(FreeCAD.animate_observer)
