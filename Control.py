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
Created on Tue May 21 23:23:30 2019

@author: jirka
"""

import FreeCAD
import FreeCADGui
import numpy
import time

from PySide2.QtWidgets import QDialogButtonBox
from PySide2.QtWidgets import QMessageBox
from os import path
from threading import Timer, Thread

_PATH_ICONS = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                        "Icons")
_PATH_UI = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                     "UIs")


class ControlThread(Thread):

    def __init__(self):
        pass


class ControlPanel:

    timer = None

    def __init__(self, cp):
        self.cp = cp
        # this will create a Qt widget from our ui file
        self.form = FreeCADGui.PySideUic.loadUi(path.join(_PATH_UI,
                                                          "AnimationControl.ui"
                                                          ))
        self.form.btn_play.clicked.connect(self.play)
        self.form.btn_pause.clicked.connect(self.pause)
        self.form.btn_rewind.clicked.connect(self.rewind)
        self.form.btn_record.clicked.connect(self.record)
        self.form.btn_export.clicked.connect(self.export)
        self.form.sld_seek.valueChanged.connect(self.slider_changed)
        self.form.sld_seek.setPageStep(max(1, numpy.round(
                                       100 * self.cp.StepTime /
                                       (self.cp.StopTime - self.cp.StartTime)))
                                       )
        self.last_clicked = "pause"
        self.set_invalid_buttons()

    def play(self):
        self.last_clicked = "play"
        self.set_invalid_buttons()
        FreeCADGui.ActiveDocument.ActiveView.setAnimationEnabled(False)
        if self.form.sld_seek.value() == self.form.sld_seek.maximum():
            QMessageBox.warning(None, 'Error while playing',
                                "The animation is at the end.")
            self.pause()
        else:
            t = self.form.sld_seek.value() * \
                (self.cp.StopTime - self.cp.StartTime) / 100 + \
                self.cp.StartTime
            time_ = time.clock()
            for t in numpy.append(numpy.arange(t, self.cp.StopTime,
                                  self.cp.StepTime), self.cp.StopTime):
                print(time_)
                if self.last_clicked == "pause":
                    break
                self.distributeTime(t)
                self.form.sld_seek.setValue(numpy.round(100*(t - self.cp.StartTime)
                                            / (self.cp.StopTime - self.cp.StartTime)))
#                pause = self.cp.StepTime + time_ - time.clock()
#                time.sleep(pause * (pause > 0))
                time.sleep(0.02)
        self.pause()

    def pause(self):
        FreeCAD.Console.PrintLog("pause button clicked\n")
        self.last_clicked = "pause"
        self.set_invalid_buttons()

    def rewind(self):
        self.last_clicked = "rewind"
        self.set_invalid_buttons()
        FreeCADGui.ActiveDocument.ActiveView.setAnimationEnabled(False)
        if self.form.sld_seek.value() == self.form.sld_seek.minimum():
            QMessageBox.warning(None, 'Error while rewinding',
                                "The animation is at the beginning.")
            self.pause()
        else:
            t = self.form.sld_seek.value() * \
                (self.cp.StopTime - self.cp.StartTime) / 100 + \
                self.cp.StartTime
            self.updateScene(t)

    def record(self):
        FreeCAD.Console.PrintLog("record button clicked\n")
        self.last_clicked = "record"
        self.set_invalid_buttons()
        FreeCADGui.ActiveDocument.ActiveView.setAnimationEnabled(False)

    def export(self):
        FreeCAD.Console.PrintLog("export button clicked\n")
        self.last_clicked = "export"
        self.set_invalid_buttons()
        FreeCAD.Console.PrintLog("Will be implemented in the future.\n")
        width = 1024
        height = 768
        path = r"C:\Users\jirka\Desktop\Test1.png"
        FreeCADGui.ActiveDocument.ActiveView.saveImage(path, width, height)

    def slider_changed(self):
        if self.form.sld_seek.isEnabled():
            t = self.form.sld_seek.value() * \
                (self.cp.StopTime - self.cp.StartTime) / 100 + \
                self.cp.StartTime
            self.distributeTime(t)

    def set_invalid_buttons(self):
        self.form.btn_play.setEnabled(self.last_clicked == "pause")
        self.form.btn_pause.setEnabled(self.last_clicked != "pause")
        self.form.btn_rewind.setEnabled(self.last_clicked == "pause")
        self.form.btn_record.setEnabled(self.last_clicked == "pause")
        self.form.btn_export.setEnabled(self.last_clicked == "pause")
        self.form.lbl_seek.setEnabled(self.last_clicked == "pause")
        self.form.sld_seek.setEnabled(self.last_clicked == "pause")

    def reject(self):
        FreeCAD.Console.PrintLog("rejected \n")
        FreeCADGui.Control.closeDialog()

    def getStandardButtons(self, *args):
        FreeCAD.Console.PrintLog("getSTDButtons clicked \n")
        return QDialogButtonBox.Close

    def isAllowedAlterSelection(self):
        return False

    def isAllowedAlterView(self):
        return True

    def isAllowedAlterDocument(self):
        return False

    def updateScene(self, t):
        time_ = time.clock()
        print(time)
        if self.last_clicked == "pause":
            return
        self.distributeTime(t)
        self.form.sld_seek.setValue(numpy.round(100*(t - self.cp.StartTime)
                                    / (self.cp.StopTime - self.cp.StartTime)))
        if (t == self.cp.StartTime and self.last_clicked == "rewind") or \
           (t == self.cp.StopTime and self.last_clicked in ["play", "record"]):
            self.pause()
            return
        if self.last_clicked in ["play", "record"]:
            next_t = min(t + self.cp.StepTime, self.cp.StopTime)
        elif self.last_clicked == "rewind":
            next_t = max(t - self.cp.StepTime, self.cp.StartTime)
        print(next_t)
        pause = self.cp.StepTime + time_ - time.clock()
        self.timer = Timer(pause, lambda: self.updateScene(next_t))
        self.timer.start()

    def distributeTime(self, t):
        objects = self.cp.Group
        while len(objects) > 0:
            obj = objects.pop(0)
            if obj.Proxy.__class__.__name__ == "Trajectory":
                obj.Time = t
                objects += obj.Group
#        FreeCAD.ActiveDocument.recompute()
#        FreeCADGui.ActiveDocument.ActiveView.redraw()


class ControlProxy:

    updated = False

    def __init__(self, fp):
        '''"App two point properties" '''
        self.setProperties(fp)
        fp.Proxy = self

    def onDocumentRestored(self, fp):
        """
Method called when document is restored to make sure everything is as it was.

Reinitialization method - it creates properties and sets them to
default, if they were not restored automatically. It restarts a
server if it was running when document was closed. Properties of
connected `ViewObject` are also recreated and reset if necessary.

Args:
    fp : A restored `FeaturePython` Server object.
        """
        self.setProperties(fp)
#        fp.ViewObject.Proxy.setProperties(fp.ViewObject)

    def onChanged(self, fp, prop):
        """
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
        # check that a trajectory has valid format
        if self.updated:
            self.updated = False
            return
        elif prop == "StartTime" and hasattr(fp, "StopTime") and \
             hasattr(fp, "StepTime"):
            self.updated = True
            fp.StopTime = (fp.StopTime, fp.StartTime + fp.StepTime,
                           float("inf"), 0.5)
            self.updated = True
            fp.StepTime = (fp.StepTime, 0.01,
                           fp.StopTime - fp.StartTime, 0.1)
        elif prop == "StepTime" and hasattr(fp, "StartTime") and \
             hasattr(fp, "StopTime"):
            self.updated = True
            fp.StopTime = (fp.StopTime, fp.StartTime + fp.StepTime,
                           float("inf"), 0.5)
            self.updated = True
            fp.StartTime = (fp.StartTime, -float("inf"),
                            fp.StopTime - fp.StepTime, 0.5)
        elif prop == "StopTime" and hasattr(fp, "StartTime") and \
             hasattr(fp, "StepTime"):
            self.updated = True
            fp.StartTime = (fp.StartTime, -float("inf"),
                            fp.StopTime - fp.StepTime, 0.5)
            self.updated = True
            fp.StepTime = (fp.StepTime, 0.01,
                           fp.StopTime - fp.StartTime, 0.1)

    def execute(self, fp):
        """
        Event handler called to recompute the object after a property
        was changed to new valid value (processed by onChange()).

        We change the placement of connected parts/assemblies to agree with
        computed current placement.

        Parameters
        ----------
        fp : Part::FeaturePython Trajectory object
            `fp` is an object which property has changed.
        """
        pass

    def setProperties(self, fp):
        # add (and preset) properties
        if not hasattr(fp, "StartTime"):
            fp.addProperty("App::PropertyFloatConstraint", "StartTime",
                           "Timing", "Animation start time. \nRange is "
                           "< - inf | Stop Time - Step Time >."
                           ).StartTime = (0, -float("inf"), 9.5, 0.5)
        elif hasattr(fp, "StepTime") and hasattr(fp, "StopTime"):
            fp.StartTime = (fp.StartTime, -float("inf"),
                            fp.StopTime - fp.StepTime, 0.5)
        if not hasattr(fp, "StepTime"):
            fp.addProperty("App::PropertyFloatConstraint", "StepTime",
                           "Timing", "Animation step time. \nRange is "
                           "< 0.01 | Stop Time - Start Time >."
                           ).StepTime = (0.5, 0.01, 10, 0.1)
        elif hasattr(fp, "StartTime") and hasattr(fp, "StopTime"):
            fp.StepTime = (fp.StepTime, 0.01,
                           fp.StopTime - fp.StartTime, 0.1)
        if not hasattr(fp, "StopTime"):
            fp.addProperty("App::PropertyFloatConstraint", "StopTime",
                           "Timing", "Animation stop time. \nRange is "
                           + "< Start Time + Step Time | inf >."
                           ).StopTime = (10, 0.5, float("inf"), 0.5)
        elif hasattr(fp, "StartTime") and hasattr(fp, "StepTime"):
            fp.StopTime = (fp.StopTime, fp.StartTime + fp.StepTime,
                           float("inf"), 0.5)


class ViewProviderControlProxy:

    def __init__(self, vp):
        """
Set this object to the proxy object of the actual view provider.
        """
        self.setProperties(vp)
        vp.Proxy = self

    def getDefaultDisplayMode(self):
        """
Return the name of the default display mode.
It must be defined in getDisplayModes.
        """
        return None

    def canDropObject(self, obj):
        FreeCAD.Console.PrintLog(str(type(obj.Proxy)) + "\n")
        if hasattr(obj, "Proxy") and \
           (obj.Proxy.__class__.__name__ == "ServerProxy" or
           obj.Proxy.__class__.__name__ == "Trajectory"):
            return True
        return False

    def getIcon(self):
        """
        Get the icon in XMP format which will appear in the tree view.
        """
        return path.join(_PATH_ICONS, "Control.xpm")

    def setProperties(self, vp):
        # hide unnecessary view properties
        vp.setEditorMode("DisplayMode", 2)
        vp.setEditorMode("Visibility", 2)

    def doubleClicked(self, vp):
        """
Double clicked.
        """
        panel = ControlPanel(vp.Object)
        FreeCADGui.Control.showDialog(panel)
        return True


class ControlCommand(object):
    """Create Object command"""

    def GetResources(self):
        return {'Pixmap': path.join(_PATH_ICONS, "ControlCmd.xpm"),
                'MenuText': "Control",
                'ToolTip': "Create Control instance."}

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        a = doc.addObject("App::DocumentObjectGroupPython", "Control")
        ControlProxy(a)
        if FreeCAD.GuiUp:
            ViewProviderControlProxy(a.ViewObject)
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
    FreeCADGui.addCommand('ControlCommand', ControlCommand())
