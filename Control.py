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


"""@package Control
 Classes related to Control component of Animate Workbench.

The classes in this module provides funcionality for
a `DocumentObjectGroupPython` Control instance.
"""

import FreeCAD
import FreeCADGui
import numpy
import time
import os
import re
import subprocess

from PySide2.QtWidgets import QDialogButtonBox, QMessageBox, QTreeView, \
    QHBoxLayout, QPushButton
from PySide2.QtCore import Slot, QTimer, QObject
from PySide2.QtCore import Qt
from PySide2.QtGui import QStandardItemModel, QStandardItem
from os import path


## Path to a folder with the necessary icons.
_PATH_ICONS = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                        "Icons")

## Path to a folder with the necessary user interface files.
_PATH_UI = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                     "UIs")

## format string to format image number inside image name while recording
NAME_NUMBER_FORMAT = "%05d"


class ControlPanel(QObject):
    """
Class providing funcionality to a Control panel inside TaskView.

This class enables user to play, pause, rewind, record, export and seek through
an animation.

Attributes:
    form: A QDialog instance show in the TaskView.
    timer: A QTimer for timing animations.
    last_clicked: A str showing which button was pressed last.
    image_number: An int number of a next recorded image.
    record_prefix: A str prefix for an image file name.
    trv_sequences: A QTreeView showing list of recorded sequences.
    lyt_export: A QHBoxLayout with a `confirm` and `abort` buttons.
    btn_confirm: A QPushButton to confirm sequence to export.
    btn_abort: A QPushButton to abort exporting a sequence.

To create an instance of this class do:
        form = FreeCADGui.PySideUic.loadUi(
            path.join(_PATH_UI, "AnimationControl.ui"))
        form.setWindowTitle(title)
        panel = ControlPanel(feature_python, form)
    """

    def __init__(self, control_proxy, form):
        super(ControlPanel, self).__init__()
        self.control_proxy = control_proxy

        # Disable editing of Control properties
        for prop in self.control_proxy.PropertiesList:
            self.control_proxy.setEditorMode(prop, 1)

        # Add QDialog to be displayed in freeCAD
        self.form = form

        # Connect callback functions
        self.form.btn_play.clicked.connect(self.playClicked)
        self.form.btn_pause.clicked.connect(self.pauseClicked)
        self.form.btn_rewind.clicked.connect(self.rewindClicked)
        self.form.btn_record.clicked.connect(self.recordClicked)
        self.form.btn_export.clicked.connect(self.exportClicked)
        self.form.sld_seek.valueChanged.connect(self.sliderChanged)

        # Create timer for the animations
        self.timer = QTimer(self)

        # Disable pause button as animation is not running when the panel is
        # opened
        self.last_clicked = "pause"
        self.setInvalidButtons()

    def playClicked(self):
        # Disable everything except for the pause button
        self.last_clicked = "play"
        self.setInvalidButtons()
        FreeCADGui.ActiveDocument.ActiveView.setAnimationEnabled(False)

        # Check that we are not already at the end of an animation range
        if self.form.sld_seek.value() == self.form.sld_seek.maximum():
            # Show error if we are
            QMessageBox.warning(None, 'Error while playing',
                                "The animation is at the end.")
            self.pauseClicked()
        else:
            # Reset collisions
            self.resetCollisions()
            # Load current time from the time slider and start playing
            t = self.form.sld_seek.value() \
                * (self.control_proxy.StopTime
                   - self.control_proxy.StartTime) / 100 \
                + self.control_proxy.StartTime
            self.play(t)

    def pauseClicked(self):
        # Enable everything except for the pause button
        self.last_clicked = "pause"
        self.setInvalidButtons()

    def rewindClicked(self):
        # Disable everything except for the pause button
        self.last_clicked = "rewind"
        self.setInvalidButtons()
        FreeCADGui.ActiveDocument.ActiveView.setAnimationEnabled(False)

        # Check that we are not already at the start of an animation range
        if self.form.sld_seek.value() == self.form.sld_seek.minimum():
            # Show error if we are
            QMessageBox.warning(None, 'Error while rewinding',
                                "The animation is at the beginning.")
            self.pauseClicked()
        else:
            # Reset collisions
            self.resetCollisions()
            # Load current time from the time slider and start rewinding
            t = self.form.sld_seek.value() \
                * (self.control_proxy.StopTime
                   - self.control_proxy.StartTime) / 100 \
                + self.control_proxy.StartTime
            self.rewind(t)

    def recordClicked(self):
        # Disable everything except for the pause button
        self.last_clicked = "record"
        self.setInvalidButtons()

        # Create an unique prefix for the image files which will be made
        self.record_prefix = "seq" + time.strftime("%Y%m%d%H%M%S") + "-"
        # Reset image number for new image sequence
        self.image_number = 0
        FreeCADGui.ActiveDocument.ActiveView.setAnimationEnabled(False)

        # Check that we are not already at the end of an animation range
        if self.form.sld_seek.value() == self.form.sld_seek.maximum():
            # Show error if we are
            QMessageBox.warning(None, 'Error while playing',
                                "The animation is at the end.")
            self.pauseClicked()
        else:
            # Reset collisions
            self.resetCollisions()
            # Load current time from the time slider and start recording
            t = self.form.sld_seek.value() \
                * (self.control_proxy.StopTime
                   - self.control_proxy.StartTime) / 100 \
                + self.control_proxy.StartTime
            self.record(t)

    def exportClicked(self):
        # Disable everything
        self.last_clicked = "export"
        self.setInvalidButtons()

        # Try to load file names from an export folder
        try:
            files = os.listdir(self.control_proxy.ExportPath)
        except FileNotFoundError as e:
            QMessageBox.warning(None, 'Export Path error', str(e))
            return

        # Find all recorded sequences between the files
        sequences = self.findSequences(files)
        if sequences != {}:
            # Show them in an export menu
            self.showSequences(sequences)
        else:
            # Show error if none found
            QMessageBox.warning(None, 'Export error',
                                "No sequences to export.")
            self.last_clicked = "pause"
            self.setInvalidButtons()

    def sliderChanged(self):
        # Check if the slider is enabled i.e. the change is an user input,
        # not a visualization of animation progress
        if self.form.sld_seek.isEnabled():
            # Load current time from the time slider and show it.
            t = self.form.sld_seek.value() \
                * (self.control_proxy.StopTime
                   - self.control_proxy.StartTime) / 100 \
                + self.control_proxy.StartTime
            self.distributeTime(t)
            self.updateCollisions()
            self.showChanges()

    def setInvalidButtons(self):
        # Disable invalid buttons with respect to the last clicked button
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
        """
Control panel was is closing.
        """
        # Stop animaiton, if it's running by clicking pause button
        self.pauseClicked()

        # Allow editing of Control properties again
        for prop in self.control_proxy.PropertiesList:
            self.control_proxy.setEditorMode(prop, 0)

        # Delete refrence to this panel from the view provider as the panel
        # will no longer exist
        self.control_proxy.ViewObject.Proxy.panel = None

        # Close the dialog
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

        # Load current time
        time_ = time.clock()

        # Chech pause button was not pressed
        if self.last_clicked == "pause":
            return

        # Disribute the animaiton time to trajectories so that they change
        # positions of all animated objects
        self.distributeTime(t)
        self.updateCollisions()
        self.showChanges()

        # Display current progres on the seek slider
        self.form.sld_seek.setValue(
            numpy.round(100*(t - self.control_proxy.StartTime)
                        / (self.control_proxy.StopTime
                           - self.control_proxy.StartTime)))

        # Stop the animation if the animation time reached a range boundary
        if t >= self.control_proxy.StopTime:
            self.last_clicked = "pause"
            self.setInvalidButtons()
            return

        # Compute an animation time for the next frame
        next_t = min(t + self.control_proxy.StepTime,
                     self.control_proxy.StopTime)

        # Compute pause period so that animaiton time roughly corresponds to
        # the real time
        pause = round(1000*(self.control_proxy.StepTime + time_
                            - time.clock()))
        pause = pause*(pause > 0)

        # Setup a timer to show next frame if animaiton wasn't paused
        if self.last_clicked != "pause":
            self.timer.singleShot(pause, lambda: self.play(next_t))

    @Slot(float, float)
    def rewind(self, t):

        # Load current time
        time_ = time.clock()

        # Chech pause button was not pressed
        if self.last_clicked == "pause":
            return

        # Disribute the animaiton time to trajectories so that they change
        # positions of all animated objects
        self.distributeTime(t)
        self.updateCollisions()
        self.showChanges()

        # Display current progres on the seek slider
        self.form.sld_seek.setValue(
                numpy.round(100*(t - self.control_proxy.StartTime)
                            / (self.control_proxy.StopTime
                               - self.control_proxy.StartTime)))

        # Stop the animation if the animation time reached a range boundary
        if t <= self.control_proxy.StartTime:
            self.last_clicked = "pause"
            self.setInvalidButtons()
            return

        # Compute an animation time for the next frame
        next_t = max(t - self.control_proxy.StepTime,
                     self.control_proxy.StartTime)

        # Compute pause period so that animaiton time roughly corresponds to
        # the real time
        pause = round(1000*(self.control_proxy.StepTime + time_
                            - time.clock()))
        pause = pause*(pause > 0)

        # Setup a timer to show next frame if animaiton wasn't paused
        if self.last_clicked != "pause":
            self.timer.singleShot(pause, lambda: self.rewind(next_t))

    @Slot(float, float)
    def record(self, t):

        # Chech pause button was not pressed
        if self.last_clicked == "pause":
            return

        # Disribute the animaiton time to trajectories so that they change
        # positions of all animated objects, save the image
        self.distributeTime(t)
        self.updateCollisions()

        # Show changes and save view
        self.showChanges()
        self.saveImage()

        # Display current progres on the seek slider
        self.form.sld_seek.setValue(
                numpy.round(100*(t - self.control_proxy.StartTime)
                            / (self.control_proxy.StopTime
                               - self.control_proxy.StartTime)))

        # Stop the animation if the animation time reached a range boundary
        if t >= self.control_proxy.StopTime:
            self.last_clicked = "pause"
            self.setInvalidButtons()
            return

        # Compute an animation time for the next frame
        next_t = min(t + self.control_proxy.StepTime,
                     self.control_proxy.StopTime)

        # Setup a timer to show next frame if animaiton wasn't paused
        if self.last_clicked != "pause":
            self.timer.singleShot(0, lambda: self.record(next_t))

    def distributeTime(self, t):
        # Load list of objects inside Control group
        objects = self.control_proxy.Group

        # Go through them, their children and update time,
        # if they are Trajectories
        while len(objects) > 0:
            obj = objects.pop(0)
            if obj.Proxy.__class__.__name__ == "TrajectoryProxy":
                obj.Time = t
                objects += obj.Group

    def updateCollisions(self):
        # Load list of objects inside Control group
        objects = self.control_proxy.Group

        # if they are CollisionDetectors, then check for collisions
        while len(objects) > 0:
            obj = objects.pop(0)
            if obj.Proxy.__class__.__name__ == "CollisionDetectorProxy":
                obj.touch()

    def resetCollisions(self):
        # Load list of objects inside Control group
        objects = self.control_proxy.Group

        # if they are CollisionDetectors, then check for collisions
        while len(objects) > 0:
            obj = objects.pop(0)
            if obj.Proxy.__class__.__name__ == "CollisionDetectorProxy":
                obj.Proxy.reset()

    def showChanges(self):
            FreeCAD.ActiveDocument.recompute()
            FreeCADGui.updateGui()

    def saveImage(self):

        # Prepare complete path to an image
        name = self.record_prefix + (NAME_NUMBER_FORMAT % self.image_number) \
            + ".png"
        path_ = path.join(self.control_proxy.ExportPath, name)

        # Export image and increase image number
        FreeCADGui.ActiveDocument.ActiveView.setAnimationEnabled(False)
        FreeCADGui.ActiveDocument.ActiveView.saveImage(
                path_,
                self.control_proxy.VideoWidth,
                self.control_proxy.VideoHeight)
        self.image_number += 1

    def findSequences(self, files):

        # Check there are any files
        if len(files) == 0:
            return {}

        # Go through the files
        sequences = {}
        for f in files:

            # Check they fit the name pattern
            img_name = re.search(r"(seq\d+)-(\d+)(?=\.png)", f)
            if img_name is not None:

                # Add new sequences
                if img_name.group(1) not in list(sequences.keys()):

                    # Add sequence if it's starting with 0
                    if int(img_name.group(2)) == 0:
                        sequences[img_name.group(1)] = 1
                        last_frame = int(img_name.group(2))

                # Compute number of successive frames
                elif int(img_name.group(2)) == (last_frame + 1):
                    sequences[img_name.group(1)] += 1
                    last_frame += 1

                # Remove sequence if a frame is missing
                else:
                    sequences.pop(img_name.group(1))

        # Leave sequences longer than 1 frame
        sequences = {key: val for key, val in sequences.items() if val > 1}
        return sequences

    def showSequences(self, sequences):

        # Add names to columns
        NAME, N_FRAMES = range(2)

        # Create a tree view  and set it up
        self.trv_sequences = QTreeView()
        self.trv_sequences.setRootIsDecorated(False)
        self.trv_sequences.setAlternatingRowColors(True)
        self.trv_sequences.setToolTip("Select a sequence to export.")
        self.trv_sequences.setSizeAdjustPolicy(
                self.trv_sequences.AdjustToContents)
        self.trv_sequences.setSizePolicy(
                self.trv_sequences.sizePolicy().Ignored,
                self.trv_sequences.sizePolicy().Minimum)
        self.trv_sequences.header().setResizeMode(
                self.trv_sequences.header().Fixed)
        self.trv_sequences.header().setDefaultSectionSize(120)
        self.trv_sequences.setSelectionMode(self.trv_sequences.SingleSelection)

        # Prepare a table
        model = QStandardItemModel(0, 2, self.trv_sequences)

        # Prepare a header
        hdr_name = QStandardItem("Sequence Name")
        model.setHorizontalHeaderItem(NAME, hdr_name)
        hdr_frames = QStandardItem("# of frames")
        hdr_frames.setTextAlignment(Qt.AlignmentFlag.AlignRight)
        model.setHorizontalHeaderItem(N_FRAMES, hdr_frames)

        # Add data to the table
        for name, frames in sequences.items():
            itm_name = QStandardItem(name)
            itm_name.setSelectable(True)
            itm_name.setEditable(False)
            itm_frames = QStandardItem(str(frames))
            itm_frames.setSelectable(True)
            itm_frames.setEditable(False)
            itm_frames.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            model.appendRow((itm_name, itm_frames))

        # Add the table to the tree view
        self.trv_sequences.setModel(model)

        # Add the tree view to the panel under the EXPORT button
        self.form.lyt_main.insertWidget(5, self.trv_sequences)

        # Make column with the numbers of frames smaller
        self.trv_sequences.setColumnWidth(1, 80)
        # Select the first item
        self.trv_sequences.setCurrentIndex(model.index(0, 0))

        # Add horizontal layout under the tree view
        self.lyt_export = QHBoxLayout()
        self.form.lyt_main.insertLayout(6, self.lyt_export)

        # Add buttons for confirmation of a selected sequence and
        # export abortion
        self.btn_confirm = QPushButton("Confirm")
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
        self.btn_abort = QPushButton("Abort")
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
        self.lyt_export.addWidget(self.btn_confirm)
        self.lyt_export.addWidget(self.btn_abort)

        # Create a function to disable deselection
        def mySelectionChanged(selected, deselected):
            if selected.isEmpty() and not deselected.isEmpty():
                self.trv_sequences.selectionModel().select(
                        deselected.first().indexes()[0],
                        self.trv_sequences.selectionModel().Select
                        | self.trv_sequences.selectionModel().Rows)

        # Connect the function as a slot for signal emitted when selection is
        # changed
        self.trv_sequences.selectionModel().selectionChanged.connect(
                mySelectionChanged)

    def exportConfirmed(self):

        # Disable export and confirm buttons
        self.btn_confirm.setEnabled(False)
        self.btn_abort.setEnabled(False)

        # Prepare arguments for ffmpeg conversion
        fps = str(1 / self.control_proxy.StepTime)
        selected_seq = \
            self.trv_sequences.selectionModel().selectedRows()[0].data()
        image_name = '"' + path.normpath(
                path.join(self.control_proxy.ExportPath, selected_seq + "-"
                          + NAME_NUMBER_FORMAT + ".png")) + '"'
        video_name = '"' + path.normpath(
                path.join(self.control_proxy.ExportPath,
                          selected_seq + ".mp4")) + '"'

        # Prepare an ffmpeg command
        export_command = 'ffmpeg -r ' + fps + ' -i ' + image_name \
            + ' -c:v libx264 -pix_fmt yuv420p ' + video_name

        # Try to run the command
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

        # Close the export subform
        self.closeExportSubform()

    def exportAborted(self):
        # Close the export subform
        self.closeExportSubform()

    def closeExportSubform(self):
        # Close all parts of export subform and remove them from the panel
        self.trv_sequences.close()
        self.form.lyt_main.removeWidget(self.trv_sequences)
        self.btn_abort.close()
        self.lyt_export.removeWidget(self.btn_abort)
        self.btn_confirm.close()
        self.lyt_export.removeWidget(self.btn_confirm)
        self.form.lyt_main.removeItem(self.lyt_export)
        self.last_clicked = "pause"
        self.setInvalidButtons()


class ControlProxy:
    """
Attributes:
    updated
    temporary_export_path
    """

    updated = False

    def __init__(self, feature_python):
        '''"App two point properties" '''
        self.setProperties(feature_python)
        feature_python.Proxy = self

    def onDocumentRestored(self, feature_python):
        """
Method called when document is restored to make sure everything is as it was.

Reinitialization method - it creates properties and sets them to
default, if they were not restored automatically. It restarts a
server if it was running when document was closed. Properties of
connected `ViewObject` are also recreated and reset if necessary.

Args:
    feature_python : A restored `FeaturePython` Server object.
        """
        feature_python.ViewObject.Proxy.setProperties(
                feature_python.ViewObject)
        self.setProperties(feature_python)

    def onBeforeChange(self, feature_python, prop):
        """
adsfa.
        """
        # Save an export path before it's changed to restore it if new
        # path is invalid
        if prop == "ExportPath" and hasattr(feature_python, "ExportPath") and \
           not self.updated:
            self.temporary_export_path = feature_python.ExportPath

    def onChanged(self, feature_python, prop):
        """
        Event handler for a property change in Data table. The property
        value validity is checked here.

        Parameters
        ----------
        feature_python : Part::FeaturePython Control object
            `feature_python` is an object which property has changed.
        prop : String
            `prop` is a name of a changed property.
        """
        # Don't do anything if a value was updated because another property
        # had changed
        if self.updated:
            self.updated = False
            return

        # Control animation range so that step size is less than range size
        elif prop == "StartTime" and hasattr(feature_python, "StopTime") and \
                hasattr(feature_python, "StepTime"):
            self.updated = True
            feature_python.StopTime = (feature_python.StopTime,
                                       feature_python.StartTime
                                       + feature_python.StepTime,
                                       float("inf"), 0.5)
            self.updated = True
            feature_python.StepTime = (feature_python.StepTime, 0.01,
                                       feature_python.StopTime
                                       - feature_python.StartTime, 0.1)
        elif prop == "StepTime" and hasattr(feature_python, "StartTime") and \
                hasattr(feature_python, "StopTime"):
            self.updated = True
            feature_python.StopTime = (feature_python.StopTime,
                                       feature_python.StartTime
                                       + feature_python.StepTime,
                                       float("inf"), 0.5)
            self.updated = True
            feature_python.StartTime = (feature_python.StartTime,
                                        -float("inf"),
                                        feature_python.StopTime
                                        - feature_python.StepTime, 0.5)
        elif prop == "StopTime" and hasattr(feature_python, "StartTime") and \
                hasattr(feature_python, "StepTime"):
            self.updated = True
            feature_python.StartTime = (feature_python.StartTime,
                                        -float("inf"),
                                        feature_python.StopTime
                                        - feature_python.StepTime, 0.5)
            self.updated = True
            feature_python.StepTime = (feature_python.StepTime, 0.01,
                                       feature_python.StopTime
                                       - feature_python.StartTime, 0.1)

        # Return to previous export path if the new one is invalid
        elif prop == "ExportPath":
            # Test access right in the folder an show warning if they are not
            # sufficient
            if not os.access(feature_python.ExportPath, os.W_OK | os.R_OK):
                QMessageBox.warning(None, 'Error while setting Export Path',
                                    "You don't have access to read and write "
                                    + "in this folder.")
                self.updated = True
                feature_python.ExportPath = self.temporary_export_path
                del self.temporary_export_path

    def setProperties(self, feature_python):
        # Add (and preset) properties
        if not hasattr(feature_python, "StartTime"):
            feature_python.addProperty(
                "App::PropertyFloatConstraint", "StartTime", "Timing",
                "Animation start time. \nRange is "
                "< - inf | Stop Time - Step Time >."
                ).StartTime = (0, -float("inf"), 9.5, 0.5)
        elif hasattr(feature_python, "StepTime") and \
                hasattr(feature_python, "StopTime"):
            feature_python.StartTime = (feature_python.StartTime,
                                        -float("inf"),
                                        feature_python.StopTime
                                        - feature_python.StepTime, 0.5)
        if not hasattr(feature_python, "StepTime"):
            feature_python.addProperty(
                "App::PropertyFloatConstraint", "StepTime", "Timing",
                "Animation step time. \nRange is "
                "< 0.01 | Stop Time - Start Time >."
                ).StepTime = (0.5, 0.01, 10, 0.1)
        elif hasattr(feature_python, "StartTime") and \
                hasattr(feature_python, "StopTime"):
            feature_python.StepTime = (feature_python.StepTime, 0.01,
                                       feature_python.StopTime
                                       - feature_python.StartTime, 0.1)
        if not hasattr(feature_python, "StopTime"):
            feature_python.addProperty(
                "App::PropertyFloatConstraint", "StopTime", "Timing",
                "Animation stop time. \nRange is "
                + "< Start Time + Step Time | inf >."
                ).StopTime = (10, 0.5, float("inf"), 0.5)
        elif hasattr(feature_python, "StartTime") and \
                hasattr(feature_python, "StepTime"):
            feature_python.StopTime = (feature_python.StopTime,
                                       feature_python.StartTime
                                       + feature_python.StepTime,
                                       float("inf"), 0.5)

        if not hasattr(feature_python, "ExportPath"):
            feature_python.addProperty(
                "App::PropertyPath", "ExportPath", "Record & Export",
                "Path to a folder, where recorded rendered images will be "
                "saved to be converted into a video.")
        if not hasattr(feature_python, "VideoWidth"):
            feature_python.addProperty(
                "App::PropertyIntegerConstraint", "VideoWidth",
                "Record & Export", "Width of the exported video."
                ).VideoWidth = (1280, 32, 7680, 10)
        else:
            feature_python.VideoWidth = (
                    feature_python.VideoWidth, 32, 7680, 10)
        if not hasattr(feature_python, "VideoHeight"):
            feature_python.addProperty(
                "App::PropertyIntegerConstraint", "VideoHeight",
                "Record & Export", "Height of the exported video."
                ).VideoHeight = (720, 32, 4320, 10)
        else:
            feature_python.VideoHeight = (
                    feature_python.VideoHeight, 32, 4320, 10)

        # Add an document observer to control the structure
        import AnimateDocumentObserver
        AnimateDocumentObserver.addObserver()


class ViewProviderControlProxy:

    panel = None
    feature_python = None

    def __init__(self, view_provider):
        """
Set this object to the proxy object of the actual view provider.
        """
        self.setProperties(view_provider)
        view_provider.Proxy = self

    def attach(self, view_provider):
        # Add feature python as it's necessary to claimChildren
        self.feature_python = view_provider.Object

    def claimChildren(self):
        if hasattr(self, "feature_python"):
            if self.feature_python:
                return self.feature_python.Group
        return []

    def canDropObject(self, obj):
        # Allow only some objects to be dropped into the Control group
        if hasattr(obj, "Proxy") and \
           (obj.Proxy.__class__.__name__ == "ServerProxy" or
           obj.Proxy.__class__.__name__ == "TrajectoryProxy" or
           obj.Proxy.__class__.__name__ == "CollisionDetectorProxy"):
            return True
        return False

    def getIcon(self):
        """
        Get the icon in XMP format which will appear in the trv_sequences view.
        """
        return path.join(_PATH_ICONS, "Control.xpm")

    def setProperties(self, view_provider):
        # Hide unnecessary view properties
        view_provider.setEditorMode("DisplayMode", 2)
        view_provider.setEditorMode("Visibility", 2)

    def doubleClicked(self, view_provider):
        """
Double clicked.
        """
        # Switch to the Task View if a Control panel is already opened
        if self.panel:
            FreeCADGui.Control.showTaskView()

        # Try to open new Control panel
        else:
            # Load the QDialog from a file and name it after this object
            form = FreeCADGui.PySideUic.loadUi(
                    path.join(_PATH_UI, "AnimationControl.ui"))
            form.setWindowTitle(view_provider.Object.Label)

            # Create a control panel and try to show it
            self.panel = ControlPanel(view_provider.Object, form)
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

    def setupContextMenu(self, view_provider, menu):
        """
Method editing a context menu for right click on `FeaturePython` Server.

The *Transform* and *Set colors...* items are removed from the context menu
shown upon right click on `FeaturePython` Server in the trv_sequences View.
The option to *Disconnect Server*, or *Connect Server* is added instead.

Args:
    view_provider: A right-clicked `Gui.ViewProviderDocumentObject`
    Server.ViewObject.
    menu: A Qt's QMenu to be edited.
        """
        # Add an option to open the Control panel
        menu.clear()
        action = menu.addAction("Show control panel")
        action.triggered.connect(lambda f=self.doubleClicked,
                                 arg=view_provider: f(arg))

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
