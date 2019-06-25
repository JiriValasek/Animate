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
import os
import re
import subprocess

from PySide2.QtWidgets import QDialogButtonBox
from PySide2.QtWidgets import QMessageBox
from PySide2.QtCore import Slot, QTimer, QObject
from os import path

_PATH_ICONS = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                        "Icons")
_PATH_UI = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                     "UIs")
NAME_NUMBER_FORMAT = "%05d"


class ControlPanel(QObject):

    def __init__(self, cp, form):
        super(ControlPanel, self).__init__()
        self.cp = cp
        for prop in self.cp.PropertiesList:
            self.cp.setEditorMode(prop, 1)
        # this will create a Qt widget from our ui file
        self.form = form
        self.form.btn_play.clicked.connect(self.playClicked)
        self.form.btn_pause.clicked.connect(self.pauseClicked)
        self.form.btn_rewind.clicked.connect(self.rewindClicked)
        self.form.btn_record.clicked.connect(self.recordClicked)
        self.form.btn_export.clicked.connect(self.exportClicked)
        self.form.sld_seek.valueChanged.connect(self.sliderChanged)
        self.timer = QTimer(self)
        self.last_clicked = "pause"
        self.set_invalid_buttons()

    def playClicked(self):
        self.last_clicked = "play"
        self.set_invalid_buttons()
        FreeCADGui.ActiveDocument.ActiveView.setAnimationEnabled(False)
        if self.form.sld_seek.value() == self.form.sld_seek.maximum():
            QMessageBox.warning(None, 'Error while playing',
                                "The animation is at the end.")
            self.pauseClicked()
        else:
            t = self.form.sld_seek.value() * \
                (self.cp.StopTime - self.cp.StartTime) / 100 + \
                self.cp.StartTime
            self.play(t)

    def pauseClicked(self):
        self.last_clicked = "pause"
        self.set_invalid_buttons()

    def rewindClicked(self):
        self.last_clicked = "rewind"
        self.set_invalid_buttons()
        FreeCADGui.ActiveDocument.ActiveView.setAnimationEnabled(False)
        if self.form.sld_seek.value() == self.form.sld_seek.minimum():
            QMessageBox.warning(None, 'Error while rewinding',
                                "The animation is at the beginning.")
            self.pauseClicked()
        else:
            t = self.form.sld_seek.value() * \
                (self.cp.StopTime - self.cp.StartTime) / 100 + \
                self.cp.StartTime
            self.rewind(t)

    def recordClicked(self):
        self.last_clicked = "record"
        self.set_invalid_buttons()
        self.recordPrefix = "seq" + time.strftime("%Y%m%d%H%M%S") + "-"
        self.imageNumber = 0
        FreeCADGui.ActiveDocument.ActiveView.setAnimationEnabled(False)
        if self.form.sld_seek.value() == self.form.sld_seek.maximum():
            QMessageBox.warning(None, 'Error while playing',
                                "The animation is at the end.")
            self.pauseClicked()
        else:
            t = self.form.sld_seek.value() * \
                (self.cp.StopTime - self.cp.StartTime) / 100 + \
                self.cp.StartTime
            self.record(t)

    def exportClicked(self):
        self.last_clicked = "export"
        self.set_invalid_buttons()
        try:
            files = os.listdir(self.cp.ExportPath)
        except FileNotFoundError as e:
            QMessageBox.warning(None, 'Export Path error', str(e))
        sequences = self.findSequences(files)
        if sequences != {}:
            self.showSequences(sequences)
        else:
            QMessageBox.warning(None, 'Export error',
                                "No sequences to export.")
            self.last_clicked = "pause"
            self.set_invalid_buttons()

    def sliderChanged(self):
        if self.form.sld_seek.isEnabled():
            t = self.form.sld_seek.value() * \
                (self.cp.StopTime - self.cp.StartTime) / 100 + \
                self.cp.StartTime
            self.distributeTime(t)

    def set_invalid_buttons(self):
        self.form.btn_play.setEnabled(self.last_clicked == "pause" and
                                      self.last_clicked != "export")
        self.form.btn_pause.setEnabled(self.last_clicked != "pause" and
                                       self.last_clicked != "export")
        self.form.btn_rewind.setEnabled(self.last_clicked == "pause" and
                                        self.last_clicked != "export")
        self.form.btn_record.setEnabled(self.last_clicked == "pause" and
                                        self.last_clicked != "export")
        self.form.btn_export.setEnabled(self.last_clicked == "pause" and
                                        self.last_clicked != "export")
        self.form.lbl_seek.setEnabled(self.last_clicked == "pause" and
                                      self.last_clicked != "export")
        self.form.sld_seek.setEnabled(self.last_clicked == "pause" and
                                      self.last_clicked != "export")

    def reject(self):
        self.pauseClicked()
        for prop in self.cp.PropertiesList:
            self.cp.setEditorMode(prop, 0)
        self.cp.ViewObject.Proxy.panel = None
        FreeCADGui.Control.closeDialog()

    def getStandardButtons(self, *args):
        """ To have just one button - close """
        return QDialogButtonBox.Close

    def isAllowedAlterSelection(self):
        return True

    def isAllowedAlterView(self):
        return True

    def isAllowedAlterDocument(self):
        return True

    @Slot(float, float)
    def play(self, t):
        time_ = time.clock()
        if self.last_clicked == "pause":
            return

        self.distributeTime(t)
        self.form.sld_seek.setValue(numpy.round(100*(t - self.cp.StartTime)
                                    / (self.cp.StopTime - self.cp.StartTime)))
        if t >= self.cp.StopTime:
            self.last_clicked = "pause"
            self.set_invalid_buttons()
            return
        next_t = min(t + self.cp.StepTime, self.cp.StopTime)

        pause = round(1000*(self.cp.StepTime + time_ - time.clock()))
        pause = pause*(pause > 0)
        if self.last_clicked != "pause":
            self.timer.singleShot(pause, lambda: self.play(next_t))

    @Slot(float, float)
    def rewind(self, t):
        time_ = time.clock()
        if self.last_clicked == "pause":
            return

        self.distributeTime(t)
        self.form.sld_seek.setValue(numpy.round(100*(t - self.cp.StartTime)
                                    / (self.cp.StopTime - self.cp.StartTime)))
        if t <= self.cp.StartTime:
            self.last_clicked = "pause"
            self.set_invalid_buttons()
            return
        next_t = max(t - self.cp.StepTime, self.cp.StartTime)

        pause = round(1000*(self.cp.StepTime + time_ - time.clock()))
        pause = pause*(pause > 0)
        if self.last_clicked != "pause":
            self.timer.singleShot(pause, lambda: self.rewind(next_t))

    @Slot(float, float)
    def record(self, t):
        if self.last_clicked == "pause":
            return

        self.distributeTime(t)
        self.saveImage()
        self.form.sld_seek.setValue(numpy.round(100*(t - self.cp.StartTime)
                                    / (self.cp.StopTime - self.cp.StartTime)))
        if t >= self.cp.StopTime:
            self.last_clicked = "pause"
            self.set_invalid_buttons()
            return
        next_t = min(t + self.cp.StepTime, self.cp.StopTime)

        pause = 0
        if self.last_clicked != "pause":
            self.timer.singleShot(pause, lambda: self.record(next_t))

    def distributeTime(self, t):
        objects = self.cp.Group
        while len(objects) > 0:
            obj = objects.pop(0)
            if obj.Proxy.__class__.__name__ == "TrajectoryProxy":
                obj.Time = t
                objects += obj.Group

        FreeCAD.ActiveDocument.recompute()
        FreeCADGui.updateGui()

    def saveImage(self):
        width = self.cp.VideoWidth
        height = self.cp.VideoHeight
        name = self.recordPrefix + (NAME_NUMBER_FORMAT % self.imageNumber) \
            + ".png"
        self.imageNumber += 1
        path_ = path.join(self.cp.ExportPath, name)
        FreeCADGui.ActiveDocument.ActiveView.setAnimationEnabled(False)
        FreeCADGui.ActiveDocument.ActiveView.saveImage(path_, width, height)

    def findSequences(self, files):
        if len(files) == 0:
            return []
        sequences = {}
        for f in files:
            img_name = re.search(r"(seq\d+)-(\d+)(?=\.png)", f)
            if img_name is not None:
                if img_name.group(1) not in list(sequences.keys()):
                    if int(img_name.group(2)) == 0:
                        sequences[img_name.group(1)] = 1
                        last_frame = int(img_name.group(2))
                elif int(img_name.group(2)) == (last_frame + 1):
                    sequences[img_name.group(1)] += 1
                    last_frame += 1
        sequences = {key: val for key, val in sequences.items() if val > 1}
        return sequences

    def showSequences(self, sequences):
        import PySide2
        NAME, N_FRAMES = range(2)
        self.tree = PySide2.QtWidgets.QTreeView()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setToolTip("Select a sequence to export.")
        self.tree.setSizeAdjustPolicy(self.tree.AdjustToContents)
        self.tree.setSizePolicy(self.tree.sizePolicy().Ignored,
                                self.tree.sizePolicy().Minimum)
        self.tree.header().setResizeMode(self.tree.header().Fixed)
        self.tree.header().setDefaultSectionSize(120)
        self.tree.setSelectionMode(self.tree.SingleSelection)

        model = PySide2.QtGui.QStandardItemModel(0, 2, self.tree)
        name_h = PySide2.QtGui.QStandardItem("Sequence Name")
        num_h = PySide2.QtGui.QStandardItem("# of frames")
        num_h.setTextAlignment(PySide2.QtCore.Qt.AlignmentFlag.AlignRight)
        model.setHorizontalHeaderItem(NAME, name_h)
        model.setHorizontalHeaderItem(N_FRAMES, num_h)

        for seq_name, n_frames in sequences.items():
            name = PySide2.QtGui.QStandardItem(seq_name)
            name.setSelectable(True)
            name.setEditable(False)
            frames = PySide2.QtGui.QStandardItem(str(n_frames))
            frames.setSelectable(True)
            frames.setEditable(False)
            frames.setTextAlignment(PySide2.QtCore.Qt.AlignmentFlag.AlignRight)
            model.appendRow((name, frames))

        self.tree.setModel(model)
        self.form.verticalLayout.insertWidget(5, self.tree)
        self.tree.setColumnWidth(1, 80)
        # tree.close()
        self.tree.setCurrentIndex(model.index(0, 0))
        self.hor_layout = PySide2.QtWidgets.QHBoxLayout()
        self.form.verticalLayout.insertLayout(6, self.hor_layout)
        self.btn_confirm = PySide2.QtWidgets.QPushButton("Confirm")
        self.btn_confirm.setStyleSheet(
            """
            QPushButton {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #0B0, stop: 1.0 #0D0);
                font-weight: bold;
            }
            QPushButton:hover {border-color: #0D0;}
            QPushButton:focus {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #0C0, stop: 1.0 #0F0);
                border-color: #0E0; color: #FFF;
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #0F0, stop: 1.0 #0C0);
            }""")
        self.btn_confirm.clicked.connect(self.exportConfirmed)
        self.btn_abort = PySide2.QtWidgets.QPushButton("Abort")
        self.btn_abort.setStyleSheet(
            """
            QPushButton {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #B00, stop: 1.0 #D00);
                font-weight: bold;
            }
            QPushButton:hover {border-color: #D00;}
            QPushButton:focus {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #C00, stop: 1.0 #F00);
                border-color: #E00; color: #FFF;
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #F00, stop: 1.0 #C00);
            }""")
        self.btn_abort.clicked.connect(self.exportAborted)
        self.hor_layout.addWidget(self.btn_confirm)
        self.hor_layout.addWidget(self.btn_abort)

        def mySelectionChanged(selected, deselected):
            if selected.isEmpty() and not deselected.isEmpty():
                self.tree.selectionModel().select(
                                            deselected.first().indexes()[0],
                                            self.tree.selectionModel().Select
                                            | self.tree.selectionModel().Rows)

        self.tree.selectionModel().selectionChanged.connect(mySelectionChanged)

    def exportConfirmed(self):
        self.btn_confirm.setEnabled(False)
        self.btn_abort.setEnabled(False)
        fps = str(1 / self.cp.StepTime)
        selected_seq = self.tree.selectionModel().selectedRows()[0].data()
        image_name = '"' + path.normpath(path.join(self.cp.ExportPath,
                                                   selected_seq + "-"
                                                   + NAME_NUMBER_FORMAT
                                                   + ".png")) + '"'
        video_name = '"' + path.normpath(path.join(self.cp.ExportPath,
                                                   selected_seq
                                                   + ".mp4")) + '"'
        export_command = 'ffmpeg -r ' + fps + ' -i ' + image_name \
            + ' -c:v libx264 -pix_fmt yuv420p ' + video_name
        try:
            return_val = subprocess.call(export_command)
        except OSError as e:
            if e.errno == os.errno.ENOENT:
                QMessageBox.warning(None, 'FFMPEG not available',
                                    "FFMPEG is necessary to export video.\n"
                                    + "Please install it")
            else:
                QMessageBox.warning(None, 'Something failed', str(e))
        if return_val == 0:
            QMessageBox.information(None, 'Export successfull!',
                                    "FFMPEG successfully converted image "
                                    + "sequence into a video.")
        else:
            QMessageBox.warning(None, 'FFMPEG unsuccessfull',
                                "FFMPEG failed to convert sequence into "
                                + "a video")

        self.form.verticalLayout.removeWidget(self.tree)
        self.tree.close()
        self.hor_layout.removeWidget(self.btn_abort)
        self.btn_abort.close()
        self.hor_layout.removeWidget(self.btn_confirm)
        self.btn_confirm.close()
        self.form.verticalLayout.removeItem(self.hor_layout)
        self.last_clicked = "pause"
        self.set_invalid_buttons()

    def exportAborted(self):
        self.form.verticalLayout.removeWidget(self.tree)
        self.tree.close()
        self.hor_layout.removeWidget(self.btn_abort)
        self.btn_abort.close()
        self.hor_layout.removeWidget(self.btn_confirm)
        self.btn_confirm.close()
        self.form.verticalLayout.removeItem(self.hor_layout)
        self.last_clicked = "pause"
        self.set_invalid_buttons()


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
        fp.ViewObject.Proxy.setProperties(fp.ViewObject)
        self.setProperties(fp)

    def onBeforeChange(self, fp, prop):
        if prop == "ExportPath" and hasattr(fp, "ExportPath") and \
           not self.updated:
            self.temporaryExportPath = fp.ExportPath

    def onChanged(self, fp, prop):
        """
        Event handler for a property change in Data table. The property
        value validity is checked here.

        Parameters
        ----------
        fp : Part::FeaturePython Control object
            `fp` is an object which property has changed.
        prop : String
            `prop` is a name of a changed property.
        """
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
        elif prop == "ExportPath":
            # test access right in the folder an show warning if they are not
            # sufficient
            if not os.access(fp.ExportPath, os.W_OK | os.R_OK):
                QMessageBox.warning(None, 'Error while setting Export Path',
                                    "You don't have access to read and write "
                                    + "in this folder.")
                self.updated = True
                fp.ExportPath = self.temporaryExportPath
                del self.temporaryExportPath

    def execute(self, fp):
        """
        Event handler called to recompute the object after a property
        was changed to new valid value (processed by onChange()).

        We change the placement of connected parts/assemblies to agree with
        computed current placement.

        Parameters
        ----------
        fp : Part::FeaturePython Control object
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

        if not hasattr(fp, "ExportPath"):
            fp.addProperty("App::PropertyPath", "ExportPath",
                           "Record & Export", "Path to a folder, where "
                           + "recorded rendered images will be saved to be "
                           + "converted into a video."
                           )
        if not hasattr(fp, "VideoWidth"):
            fp.addProperty("App::PropertyIntegerConstraint", "VideoWidth",
                           "Record & Export", "Width of the exported video."
                           ).VideoWidth = (1280, 32, 7680, 10)
        else:
            fp.VideoWidth = (fp.VideoWidth, 32, 7680, 10)
        if not hasattr(fp, "VideoHeight"):
            fp.addProperty("App::PropertyIntegerConstraint", "VideoHeight",
                           "Record & Export", "Height of the exported video."
                           ).VideoHeight = (720, 32, 4320, 10)
        else:
            fp.VideoHeight = (fp.VideoHeight, 32, 4320, 10)

        import AnimateDocumentObserver
        AnimateDocumentObserver.addObserver()


class ViewProviderControlProxy:

    panel = None

    def __init__(self, vp):
        """
Set this object to the proxy object of the actual view provider.
        """
        self.setProperties(vp)
        vp.Proxy = self

    def attach(self, vp):
        self.Object = vp.Object

    def claimChildren(self):
        if hasattr(self, "Object"):
            if self.Object:
                return self.Object.Group
        return []

    def canDropObject(self, obj):
        if hasattr(obj, "Proxy") and \
           (obj.Proxy.__class__.__name__ == "ServerProxy" or
           obj.Proxy.__class__.__name__ == "TrajectoryProxy"):
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
        if self.panel:
            FreeCADGui.Control.showTaskView()
        else:
            form = FreeCADGui.PySideUic.loadUi(
                    path.join(_PATH_UI, "AnimationControl.ui"))
            form.setWindowTitle(vp.Object.Label)
            self.panel = ControlPanel(vp.Object, form)
            try:
                FreeCADGui.Control.showDialog(self.panel)
            except RuntimeError as e:
                self.panel = None
                if str(e) == "Active task dialog found":
                    QMessageBox.warning(None,
                                        'Error while opening control panel',
                                        "A panel is already active on "
                                        + "the Tasks tab of the Combo View.")
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
        action = menu.addAction("Show control panel")
        action.triggered.connect(lambda f=self.doubleClicked,
                                 arg=vp: f(arg))

    def __getstate__(self):
        #TODO rewrite docstring
        """
Necessary method to avoid errors when trying to save unserializable objects.

This method is used by JSON to serialize unserializable objects during
autosave. Without this an Error would rise when JSON would try to do
that itself.

We need this for unserializable `server` and `observer` attributes,
but we don't serialize them, because it's enough to reset them
when object is restored.

Returns:
    None, because we don't serialize anything.
        """
        return None

    def __setstate__(self, state):
        #TODO rewrite docstring
        """
Necessary method to avoid errors when trying to restore unserializable objects.

This method is used during a document restoration. We need this for
unserializable `server` and `observer` attributes, but we do not restore them,
because it's enough to reset them from saved parameters.

Returns:
    None, because we don't restore anything.
        """
        return None


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
