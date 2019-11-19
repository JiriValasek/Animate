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

##@package AnimateDocumentObserver
#AnimateDocumentObserver and a method how to safely add it to FreeCAD.
#
#
#

import FreeCAD

from PySide2.QtWidgets import QMessageBox

## All the DocumentObjectGroupPython classes in the Animate workbench
ANIMATE_OBJECT_GROUP_CLASSES = ["TrajectoryProxy", "ControlProxy",
                                "CollisionDetectorProxy", "RobWorldProxy",
                                "RobRotationProxy", "RobTranslationProxy"]

## All the FeaturePython and DocumentObjectGroupPython  classes in the animate
# toolbox
ANIMATE_CLASSES = ["TrajectoryProxy", "ControlProxy", "ServerProxy",
                   "CollisionDetectorProxy", "CollisionProxy", "RobWorldProxy",
                   "RobRotationProxy", "RobTranslationProxy"]

## Classes allowed in the Control group
ALLOWED_IN_CONTROL = ["TrajectoryProxy", "ServerProxy",
                      "CollisionDetectorProxy", "RobWorldProxy",
                      "RobRotationProxy", "RobTranslationProxy"]


## @brief Class that keeps `Animate` workbench objects in recommended structures.
#
#
#
#
#
#

class AnimateDocumentObserver(object):

    ## @property		__instance
    # A reference to a singleton.

    ## @property		server_proxies
    # A dict of document names and `ServerProxies` in them.

    ## @property		group_before
    # A list of objects inside a group object about to change.

    ## @var __instance
    # @hideinitializer
    # @private
    __instance = None
    server_proxies = {}

    ## @brief Method creating an `AnimateDocumentObserver` singleton instance.
    #
    # @return
    #    An `AnimateDocumentObserver` singleton instance.
    #

    def __new__(cls, *args, **kwargs):
        # Make AnimateDocumentObserver a singleton
        if cls.__instance is None:
            cls.__instance = super(AnimateDocumentObserver,
                                   cls).__new__(cls, *args, **kwargs)
        return cls.__instance

    ## @brief Qt slot method called when an object in a surveyed document is about to change.
    #
    #If the object which is going to change has a `Group` property, then
    #a transaction is begun and a current state of the `Group` property is recorded.
    #
    #
    # @param		obj	An object in the observed document about to change.
    # @param		prop	A str of a property about to change.
    #

    def slotBeforeChangeObject(self, obj, prop):
        # If any group is about to be changed, start a transaction
        if prop == "Group":
            FreeCAD.ActiveDocument.openTransaction()
            self.group_before = obj.Group

    ## @brief Qt slot method called when an object in an observed document was changed.
    #
    #This method is used to enforce a recommended structure of `Animate` objects in
    #Tree View. It checks that only allowed objects are inside `Animate` group
    #objects. It also checks that no `Animate` object is inside a group object that
    #does not belong to the `Animate` workbench. Lastly, it obstructs user from
    #deleting Collision objects from a CollisionDetector group object.
    #
    #
    # @param		obj	An object in the observed document about to change.
    # @param		prop	A str of a property about to change.
    #

    def slotChangedObject(self, obj, prop):
        # If objects are added to a group
        if prop == "Group" and len(obj.Group) > len(self.group_before):
            # If a new object is added to a group object from Animate workbench
            new_obj = obj.Group[-1]
            if self.isAnimateGroup(obj):
                # An object not from Animate workbench was added to it
                if self.foreignObjectInAnimateGroup(new_obj, obj):
                    QMessageBox.warning(
                            None, 'Forbidden action detected',
                            "Group objects from Animate workbench can group\n"
                            + "only selected objects from Animate workbench.\n"
                            + "Check the user guide for more info.")
                    FreeCAD.ActiveDocument.undo()
                else:
                    FreeCAD.ActiveDocument.commitTransaction()

            # An object is added to a group not from Animate workbench
            else:
                # The added object was from Animate workbench
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

        # If objects are removed from a group
        elif prop == "Group" and len(obj.Group) < len(self.group_before):
            # If a Collision is removed from
            removed = set(self.group_before).difference(set(obj.Group)).pop()
            if removed.Proxy.__class__.__name__ == "CollisionProxy" and \
                    hasattr(obj, "Proxy") and not obj.Proxy.resetting and \
                    not obj.Proxy.checking:
                QMessageBox.warning(
                        None, 'Forbidden action detected',
                        "Collision objects cannot be removed from\n"
                        + "a CollisionDetector group.")
                FreeCAD.ActiveDocument.undo()
            else:
                FreeCAD.ActiveDocument.commitTransaction()

    ## @brief Method to check whether a group object comes from the `Animate` workbench.
    #
    #As all `Animate` objects have a `Proxy` attached, its reasonable to firstly
    #check for it and then decide according to the `Proxy` object's name if it is
    #an `Animate` group.
    #
    # @return
    #    True if the group object is from `Animate` workbench and false otherwise.
    #

    def isAnimateGroup(self, obj):
        # If a proxy is NoneType extrapolate it from object name
        if not hasattr(obj, "Proxy"):
            return False
        else:
            if obj.Proxy.__class__.__name__ == "NoneType":
                obj_type = obj.Name.rstrip('0123456789') + "Proxy"
            else:
                obj_type = obj.Proxy.__class__.__name__

        # Check if proxy is an Animate group class
        if obj_type not in ANIMATE_OBJECT_GROUP_CLASSES:
            return False
        else:
            return True

    ## @brief Method to check whether an object comes from the `Animate` workbench.
    #
    #As all `Animate` objects have a `Proxy` attached, its reasonable to firstly
    #check for it and then decide according to the `Proxy` object's name if it is
    #from the `Animate` workbench.
    #
    # @return
    #    True if the object is from `Animate` workbench and false otherwise.
    #

    def isAnimateObject(self, obj):
        # If a proxy is NoneType extrapolate it from object name
        if not hasattr(obj, "Proxy"):
            return False
        else:
            if obj.Proxy.__class__.__name__ == "NoneType":
                obj_type = obj.Name.rstrip('0123456789') + "Proxy"
            else:
                obj_type = obj.Proxy.__class__.__name__

        # Check if proxy is an Animate object class
        if obj_type not in ANIMATE_CLASSES:
            return False
        else:
            return True

    ## @brief Method testing whether a forbidden object is in an `Animate` group object.
    #
    #Trajectory group objects are allowed to be stacked. Control objects can contain
    #any other `Animate` object. CollisionDetector objects can accommodate only
    #Collision objects.
    #
    #
    # @param		obj	A suspected foreign object in an `Animate` group object.
    # @param		group	The `Animate` group object possibly harboring an illegal object.
    #
    # @return
    #    True if a forbidden object is in a Animate group obj. and false otherwise.
    #

    def foreignObjectInAnimateGroup(self, obj, group):
        # If an obj proxy is NoneType extrapolate it from object name
        if not hasattr(obj, "Proxy"):
            return False
        else:
            if obj.Proxy.__class__.__name__ == "NoneType":
                obj_type = obj.Name.rstrip('0123456789') + "Proxy"
            else:
                obj_type = obj.Proxy.__class__.__name__

        # If an obj proxy is NoneType extrapolate it from object name
        if group.Proxy.__class__.__name__ == "NoneType":
            group_type = group.Name.rstrip('0123456789') + "Proxy"
        else:
            group_type = group.Proxy.__class__.__name__

        # Only a Trajectory can be in a Trajectory group
        if group_type == "TrajectoryProxy" and obj_type == "TrajectoryProxy":
            return False

        # Only some objects can be in a Control group
        elif group_type == "ControlProxy" and obj_type in ALLOWED_IN_CONTROL:
            return False

        elif group_type == "CollisionDetectorProxy" and \
                obj.Name.find("Collision") != -1:
            return False
        # Only RobRotation and RobTranslation can be in RobWorld, RobRotation
        # and RobTRanslation groups
        elif (group_type in ["RobWorldProxy", "RobRotationProxy",
                             "RobTranslationProxy"]) and \
                (obj_type in ["RobRotationProxy", "RobTranslationProxy"]):
            return False
        return True

    ## @brief Method testing whether an `Animate` object is in a foreign group object.
    #
    #
    # @param		obj	A suspected `Animate` object.
    # @param		group	A group object which is possibly not from the `Animate` workbench.
    #
    # @return
    #    True if an Animate object is not in a Animate group and false otherwise.
    #

    def animateObjectInForeignGroup(self, obj, group):
        return not self.isAnimateGroup(group) and self.isAnimateObject(obj)

    ## @brief Qt slot method called if a document is about to be closed.
    #
    #This method is used to notify all `ServerProxies` that the document they are in
    #is going to be closed.
    #
    #
    # @param		doc	A FreeCAD's `App.Document` document about to be closed.
    #

    def slotDeletedDocument(self, doc):
        # Check at least one server is in the document about to be closed
        if doc.Name in self.server_proxies:
            # Notify all servers in the document
            for server_proxy in self.server_proxies[doc.Name]:
                server_proxy.onDocumentClosed()

    ## @brief Method to add a server which needs to be notified when its document is closing.
    #
    #An active server must close a socket, it is using, when a document it's on is
    #closing, so that a socket won't be blocked when it is needed again.
    #
    #
    # @param		server_proxy	A `ServerProxy` which takes care of a `Server` instance.
    # @param		document_name	Name of a document with the `Server` instance.
    #

    def addServerToNotify(self, server_proxy, document_name):
        # Add a server proxy to the dictionary under a document name it's on
        if document_name in self.server_proxies:
            if server_proxy not in self.server_proxies[document_name]:
                self.server_proxies[document_name].append(server_proxy)

        # Add a new document name to the dictionary and assign it a list
        # with a server proxy
        else:
            self.server_proxies[document_name] = [server_proxy]


## @brief Adds an `AnimateDocumentObserver` between FreeCAD's document observers safely.
#
#It's preferred to add an `AnimateDocumentObserver` using this method, because
#other ways could result in having multiple document observers added to FreeCAD.
#Having a lot of document observers slows down FreeCAD due to necessity to
#inform them all about imminent changes and so on.
#

def addObserver():
    # Check FreeCAD doesn't have an AnimateDocumentObserver already assigned
    # and assign one
    if not hasattr(FreeCAD, "animate_observer"):
        FreeCAD.animate_observer = AnimateDocumentObserver()
        FreeCAD.addDocumentObserver(FreeCAD.animate_observer)
