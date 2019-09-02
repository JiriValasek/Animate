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

##@package Control
# Classes related to the Control component of the Animate Workbench.
#
#The classes in this module provides funcionality for
#a `DocumentObjectGroupPython` Control instance.
#

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
PATH_TO_ICONS = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                        "Icons")

## Path to a folder with the necessary user interface files.
PATH_TO_UI = path.join(FreeCAD.getHomePath(), "Mod", "Animate", "Resources",
                     "UIs")

## Format string to format image number inside image name while recording
NAME_NUMBER_FORMAT = "%05d"


## @brief Class providing funcionality to a Control panel inside the TaskView.
#
#This class enables user to play, pause, rewind, record, export and seek through
#an animation.
#
#
#
#To create an instance of this class do:
# @code
#        form = FreeCADGui.PySideUic.loadUi(
#            path.join(PATH_TO_UI, "AnimationControl.ui"))
#        form.setWindowTitle(title)
#        panel = ControlPanel(fp, form)
#

class ControlPanel(QObject):

    ## @property		btn_abort
    # A QPushButton to abort exporting a sequence.

    ## @property		btn_confirm
    # A QPushButton to confirm sequence to export.

    ## @property		control_proxy
    # A proxy to an associated `Control` class.

    ## @property		form
    # A QDialog instance show in the TaskView.

    ## @property		image_number
    # An int number of a next recorded image.

    ## @property		last_clicked
    # A str showing which button was pressed last.

    ## @property		lyt_export
    # A QHBoxLayout with a `confirm` and `abort` buttons.

    ## @property		record_prefix
    # A str prefix for an image file name.

    ## @property		timer
    # A QTimer for timing animations.

    ## @property		trv_sequences
    # A QTreeView showing list of recorded sequences.

    ## @brief Initialization method for ControlPanel.
    #
    #A class instance is created. A proxy for an associated `Control` is added and
    #the control properties are set to read-only as not to change when control panel
    #is opened. A form and timer are assigned. `Pause` button is disabled as no
    #animation is playing.
    #
    #
    # @param		control_proxy	A proxy to a `Control` so properties can be set read-only.
    # @param		form	A Qt dialog loaded from a file.
    #

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

    ## @brief Feedback method called when play button was clicked.
    #
    #Invalid buttons are disabled. Active View's animation is disabled (Necessary).
    #Slider position is checked for invalid position (at the end) and if position
    #is plausible, all collisions are reset, current time is extrapolated from
    #the slider and an animation is played.
    #

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

    ## @brief Feedback method called when pause button was clicked.
    #
    #Invalid buttons are disabled in this method and that's it.
    #

    def pauseClicked(self):
        # Enable everything except for the pause button
        self.last_clicked = "pause"
        self.setInvalidButtons()

    ## @brief Feedback method called when rewind button was clicked.
    #
    #Invalid buttons are disabled. Active View's animation is disabled (Necessary).
    #Slider position is checked for invalid position (at the end) and if position
    #is plausible, all collisions are reset, current time is extrapolated from
    #the slider and an animation is played.
    #

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

    ## @brief Feedback method called when record button was clicked.
    #
    #Invalid buttons are disabled. A record prefix is generated. An Image number is
    #set to 0. Active View's animation is disabled (Necessary). Slider position is
    #checked for invalid position (at the end) and if position is plausible, all
    #collisions are reset, current time is extrapolated from the slider and an
    #animation is played/recorded.
    #

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

    ## @brief Feedback method called when export button was clicked.
    #
    #Invalid buttons are disabled. An `Export Path` is checked for files. The files
    #are checked for sequences. Sequences are shown with buttons to confirm or
    #cancel the selection.
    #

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

    ## @brief Feedback method called when slider position is changed.
    #
    #If slider is enabled (not used to show animation time) and slider position is
    #changed, time is extrapolated from slider position and animation in that time
    #is shown.
    #

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

    ## @brief Method to enable/disable buttons according to a `last clicked` button.
    #
    #If `pause` button was pressed, all others buttons are disabled. If any other
    #button was pressed, only `pause` button is left enabled.
    #

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

    ## @brief Feedback method called when Control panel is closing.
    #
    #Animation is stopped. Controls properties are set to be editable. Dialog is
    #closed.
    #

    def reject(self):
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

    ## @brief Method to set just one button (close) to close the dialog.
    #
    #
    #    *args: A tuple of unused arguments from Qt.
    #

    def getStandardButtons(self, *args):
        return QDialogButtonBox.Close

    ## @brief Method to tell FreeCAD if dialog is allowed to alter a selection.
    #
    # @return
    # @return		False	this dialog does not change a selection.
    #

    def isAllowedAlterSelection(self):
        return False

    ## @brief Method to tell FreeCAD if dialog is allowed to alter a view.
    #
    # @return
    # @return		True	this dialog does change a view.
    #

    def isAllowedAlterView(self):
        return True

    ## @brief Method to tell FreeCAD if dialog is allowed to alter a document.
    #
    # @return
    # @return		True	this dialog does change a document.
    #

    def isAllowedAlterDocument(self):
        return True

    ## @brief Method to show an animation frame at an animation time `t` during playing.
    #
    #Current clock time is loaded. If the pause button was clicked, an animation is
    #stopped. Otherwise the animation time `t` is distributed to appropriate
    #children. If the animation time `t` exceeded `Stop Time`, the animation is
    #stopped. Lastly next frame time is computed as well as pause time (to stick
    #with real time if computation did not exceeded `Step Time`). Finally the
    #timer is set to show the next animation frame after precomputed pause.
    #
    #
    # @param		t	An animation time to generate an animation frame at.
    #

    @Slot(float, float)
    def play(self, t):
        # Load current time
        time_ = time.clock()

        # Check pause button was not pressed
        if self.last_clicked == "pause":
            return

        # Disribute the animation time to trajectories so that they change
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

    ## @brief Method to show an animation frame at an animation time `t` during rewind.
    #
    #Current clock time is loaded. If the pause button was clicked, an animation is
    #stopped. Otherwise the animation time `t` is distributed to appropriate
    #children. If the animation time `t` exceeded `Stop Time`, the animation is
    #stopped. Lastly next frame time is computed as well as pause time (to stick
    #with real time if computation did not exceeded `Step Time`). Finally the
    #timer is set to show the next animation frame after precomputed pause.
    #
    #
    # @param		t	An animation time to generate an animation frame at.
    #

    @Slot(float, float)
    def rewind(self, t):
        # Load current time
        time_ = time.clock()

        # Check pause button was not pressed
        if self.last_clicked == "pause":
            return

        # Disribute the animation time to trajectories so that they change
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

    ## @brief Method to show and save an animation frame at an animation time `t`.
    #
    #Current clock time is loaded. If the pause button was clicked, an animation is
    #stopped. Otherwise the animation time `t` is distributed to appropriate
    #children. If the animation time `t` exceeded `Stop Time`, the animation is
    #stopped. Lastly next frame time is computed. Finally the timer is set to show
    #the next animation frame after precomputed pause.
    #
    #
    # @param		t	An animation time to generate an animation frame at.
    #

    @Slot(float, float)
    def record(self, t):
        # Check pause button was not pressed
        if self.last_clicked == "pause":
            return

        # Disribute the animation time to trajectories so that they change
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

    ## @brief Method to distribute a time `t` to children Trajectories.
    #
    #List of children is loaded. If a child is `Trajectory`, the time is set to it
    #and its children are added to the list.
    #
    #
    # @param		t	A time to distribute to all child `Trajectories`.
    #

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

    ## @brief Method to update collisions from CollisionDetector children.
    #
    #List of children is loaded. If a child is `CollisionDetector`, it's touched so
    #that it's recomputed.
    #

    def updateCollisions(self):
        # Load list of objects inside Control group
        objects = self.control_proxy.Group

        # if they are CollisionDetectors, then check for collisions
        while len(objects) > 0:
            obj = objects.pop(0)
            if obj.Proxy.__class__.__name__ == "CollisionDetectorProxy":
                obj.touch()

    ## @brief Method to reset collisions from CollisionDetector children.
    #
    #List of children is loaded. If a child is `CollisionDetector`, it's reset.
    #

    def resetCollisions(self):
        # Load list of objects inside Control group
        objects = self.control_proxy.Group

        # if they are CollisionDetectors, then check for collisions
        while len(objects) > 0:
            obj = objects.pop(0)
            if obj.Proxy.__class__.__name__ == "CollisionDetectorProxy":
                obj.Proxy.reset()

    ## @brief Method to show changes made to objects, collisions.
    #
    #This method is necessary to call after `distributeTime`, `updateCollisions` and
    #`resetCollisions`.
    #

    def showChanges(self):
        FreeCAD.ActiveDocument.recompute()
        FreeCADGui.updateGui()

    ## @brief Method to save current view as a PNG image.
    #
    #An image name is pieced together from `record prefix` and `image number`.
    #Then an image path is constructed. Animation is disabled(obligatory) and
    #current view is saved as an image. Finally the image number is incremented.
    #

    def saveImage(self):
        # Prepare complete path to an image
        #TODO save frame rate into an image
        name = self.record_prefix + (NAME_NUMBER_FORMAT % self.image_number) \
            + ".png"
        path_ = path.join(self.control_proxy.ExportPath, name)

        # Export image and increase image number
        FreeCADGui.ActiveDocument.ActiveView.setAnimationEnabled(False)
        FreeCADGui.ActiveDocument.ActiveView.saveImage(
                path_,
                self.control_proxy.VideoWidth, self.control_proxy.VideoHeight)
        self.image_number += 1

    ## @brief Method to find sequences between files.
    #
    #Files are scanned for sequences, the valid sequences are recognized and number
    #of frames is counted.
    #
    #
    # @param		files	A list of string file names.
    #
    # @return
    #    A dict with sequence names and numbers of frames.
    #

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

    ## @brief Method to show sequences to export on a dialog panel.
    #
    #Sequences and frame numbers are shown in a QTreeView, and buttons `'Confirm'`
    #and `'Abort'` are attached under it. All of this is put under the Export button
    #on the dialog panel.
    #
    #
    # @param		sequences	A dict with sequence names and numbers of frames.
    #

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

    ## @brief Feedback method called when confirm button was clicked.
    #
    #Buttons are disabled, frame rate is computed, selected sequence name is used
    #to create an `image name` template and a `video name` which can be used in a
    #FFMPEG command. Such a commnad is executed to convert the video, if FFMPEG is
    #installed. Otherwise warnings are shown.
    #

    def exportConfirmed(self):
        # Disable export and confirm buttons
        self.btn_confirm.setEnabled(False)
        self.btn_abort.setEnabled(False)

        # Prepare arguments for ffmpeg conversion
        #TODO load fps from the first image
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

    ## @brief Feedback method called when abort button was clicked.
    #
    #The part of the dialog panel used for video exporting is closed.
    #

    def exportAborted(self):
        # Close the export subform
        self.closeExportSubform()

    ## @brief Method used to close the part of the dialog panel used for video exporting.
    #
    #The QTreeView with sequence names and their numbers of frames are closed.
    #Then `'Confirm'` and `'Abort'` buttons are removed and the rest of buttons
    #is returned to the default state (the same as if pause button was pressed).
    #

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


## @brief Proxy class for a `DocumentObjectGroupPython` Control instance.
#
#A ControlProxy instance adds properties to a `DocumentObjectGroupPython`
#Control instance and responds to their changes. It provides a control panel
#to control animations.
#
#To access such a dialog double-click Control in Tree View or right click and
#select *Show control panel* option from a context menu.
#
#
#
#
#To connect this `Proxy` object to a `DocumentObjectGroupPython` Control do:
#
# @code
#        a = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroupPython",
#                                             "Control")
#        ControlProxy(a)
#

class ControlProxy:

    ## @property		updated
    # A bool - True if a property was changed by a class and not user.

    ## @property		temporary_export_path
    # A str path to an export folder.

    updated = False

    ## @brief Initialization method for ControlProxy.
    #
    #A class instance is created and made a `Proxy` for a generic
    #`DocumentObjectGroupPython` Control object. During initialization number of
    #properties are specified and preset.
    #
    #
    # @param		fp	A barebone `DocumentObjectGroupPython` Control object to be extended.
    #

    def __init__(self, fp):
        self.setProperties(fp)
        fp.Proxy = self

    ## @brief Method called when document is restored to make sure everything is as it was.
    #
    # 	Reinitialization	it creates properties and sets them to default, if
    #they were not restored automatically. Properties of connected `ViewObject` are
    #also recreated and reset if necessary.
    #
    #
    # @param		fp	A restored `DocumentObjectGroupPython` Control object.
    #

    def onDocumentRestored(self, fp):
        fp.ViewObject.Proxy.setProperties(fp.ViewObject)
        self.setProperties(fp)

    ## @brief Method called before `DocumentObjectGroupPython` Control is changed.
    #
    #An old export path is stored for a case in which a new export path is not
    #a valid path.
    #
    #
    # @param		fp	A `DocumentObjectGroupPython` Control object.
    # @param		prop	A str name of a property about to change.
    #

    def onBeforeChange(self, fp, prop):
        # Save an export path before it's changed to restore it if new
        # path is invalid
        if prop == "ExportPath" and hasattr(fp, "ExportPath") and \
           not self.updated:
            self.temporary_export_path = fp.ExportPath

    ## @brief Method called after `DocumentObjectGroupPython` Control was changed.
    #
    #Values of changed properties (start time, step time, stop time, export path)
    #are checked for validity and edited if they are not.
    #
    #
    # @param		fp	A `DocumentObjectGroupPython` Control object.
    # @param		prop	A str name of a changed property.
    #

    def onChanged(self, fp, prop):
        # Don't do anything if a value was updated because another property
        # had changed
        if self.updated:
            self.updated = False
            return

        # Control animation range so that step size is less than range size
        elif prop == "StartTime" and hasattr(fp, "StopTime") and \
                hasattr(fp, "StepTime"):
            self.updated = True
            fp.StopTime = (fp.StopTime, fp.StartTime + fp.StepTime,
                           float("inf"), 0.5)
            self.updated = True
            fp.StepTime = (fp.StepTime, 0.01, fp.StopTime - fp.StartTime, 0.1)
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
            fp.StepTime = (fp.StepTime, 0.01, fp.StopTime - fp.StartTime, 0.1)

        # Return to previous export path if the new one is invalid
        elif prop == "ExportPath":
            # Test access right in the folder an show warning if they are not
            # sufficient
            if not os.access(fp.ExportPath, os.W_OK | os.R_OK):
                QMessageBox.warning(None, 'Error while setting Export Path',
                                    "You don't have access to read and write "
                                    + "in this folder.")
                self.updated = True
                fp.ExportPath = self.temporary_export_path
                del self.temporary_export_path

    ## @brief Method to set properties during initialization or document restoration.
    #
    #The properties are set if they are not already present and an
    #`AnimateDocumentObserver` is recreated.
    #
    #
    # @param		fp	A restored or barebone `DocumentObjectGroupPython` Control object.
    #

    def setProperties(self, fp):
        # Add (and preset) properties
        if not hasattr(fp, "StartTime"):
            fp.addProperty(
                "App::PropertyFloatConstraint", "StartTime", "Timing",
                "Animation start time. \nRange is "
                "< - inf | Stop Time - Step Time >."
                ).StartTime = (0, -float("inf"), 9.5, 0.5)
        elif hasattr(fp, "StepTime") and hasattr(fp, "StopTime"):
            fp.StartTime = (fp.StartTime, -float("inf"),
                            fp.StopTime - fp.StepTime, 0.5)
        if not hasattr(fp, "StepTime"):
            fp.addProperty(
                "App::PropertyFloatConstraint", "StepTime", "Timing",
                "Animation step time. \nRange is "
                "< 0.01 | Stop Time - Start Time >."
                ).StepTime = (0.5, 0.01, 10, 0.1)
        elif hasattr(fp, "StartTime") and hasattr(fp, "StopTime"):
            fp.StepTime = (fp.StepTime, 0.01, fp.StopTime - fp.StartTime, 0.1)
        if not hasattr(fp, "StopTime"):
            fp.addProperty(
                "App::PropertyFloatConstraint", "StopTime", "Timing",
                "Animation stop time. \nRange is "
                + "< Start Time + Step Time | inf >."
                ).StopTime = (10, 0.5, float("inf"), 0.5)
        elif hasattr(fp, "StartTime") and hasattr(fp, "StepTime"):
            fp.StopTime = (fp.StopTime, fp.StartTime + fp.StepTime,
                           float("inf"), 0.5)

        if not hasattr(fp, "ExportPath"):
            fp.addProperty(
                "App::PropertyPath", "ExportPath", "Record & Export",
                "Path to a folder, where recorded rendered images will be "
                "saved to be converted into a video.")
        if not hasattr(fp, "VideoWidth"):
            fp.addProperty(
                "App::PropertyIntegerConstraint", "VideoWidth",
                "Record & Export", "Width of the exported video."
                ).VideoWidth = (1280, 32, 7680, 10)
        else:
            fp.VideoWidth = (fp.VideoWidth, 32, 7680, 10)
        if not hasattr(fp, "VideoHeight"):
            fp.addProperty(
                "App::PropertyIntegerConstraint", "VideoHeight",
                "Record & Export", "Height of the exported video."
                ).VideoHeight = (720, 32, 4320, 10)
        else:
            fp.VideoHeight = (fp.VideoHeight, 32, 4320, 10)

        # Add an document observer to control the structure
        import AnimateDocumentObserver
        AnimateDocumentObserver.addObserver()


## @brief Proxy class for `Gui.ViewProviderDocumentObject` Control.ViewObject.
#
#A ViewProviderControlProxy instance provides a Control's icon, double-click
#response and context menu with "Show control panel".
#
#
#
#To connect this `Proxy` object to a `Gui.ViewProviderDocumentObject`
#Control.ViewObject do:
#
# @code
#        a = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroupPython",
#                                             "Control")
#        ViewProviderControlProxy(a.ViewObject)
#

class ViewProviderControlProxy:

    ## @property		fp
    # A Control object.

    ## @property		panel
    # A ControlPanel if one is active or None.
    panel = None
    fp = None

    ## @brief Initialization method for ViewProviderControlProxy.
    #
    #A class instance is created and made a `Proxy` for a generic
    #`Gui.ViewProviderDocumentObject` Control.ViewObject. During initialization
    #number of properties are specified and preset.
    #
    #
    # @param		vp	A barebone `Gui.ViewProviderDocumentObject` Control.ViewObject.
    #

    def __init__(self, vp):
        self.setProperties(vp)
        vp.Proxy = self

    ## @brief Method called by FreeCAD after initialization.
    #
    #This method adds Control as the `fp` attribute.
    #
    #
    # @param		vp	A Control.ViewObject after initialization.
    #

    def attach(self, vp):
        # Add feature python as it's necessary to claimChildren
        self.fp = vp.Object

    ## @brief Method called by FreeCAD to retrieve assigned children.
    #
    #When a property of a Control is touched the Control and the FreeCAD
    #ActiveDocument are notified. The FreeCAD ActiveDocument then emits a signal
    #to inform all its observers e.g. the FreeCADGui ActiveDocument. The FreeCADGui
    #document then emits a new signal to inform e.g. the tree view. The tree view
    #then invokes `claimChildren()`.
    #

    def claimChildren(self):
        if hasattr(self, "fp"):
            if self.fp:
                return self.fp.Group
        return []

    ## @brief Method called by FreeCAD to ask if an object `obj` can be droped into a Group.
    #
    #FreeCAD objects of a Server, Trajectory and CollisionDetector type are allowed
    #to drop inside a Control group.
    #
    #
    # @param		obj	A FreeCAD object hovering above a Control item in the Tree View.
    #

    def canDropObject(self, obj):
        # Allow only some objects to be dropped into the Control group
        if hasattr(obj, "Proxy") and \
           (obj.Proxy.__class__.__name__ == "ServerProxy" or
           obj.Proxy.__class__.__name__ == "TrajectoryProxy" or
           obj.Proxy.__class__.__name__ == "CollisionDetectorProxy"):
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
        return path.join(PATH_TO_ICONS, "Control.xpm")

    ## @brief Method to hide unused properties.
    #
    #Properties Display Mode, Visibility are set to be invisible as they are unused.
    #
    #
    # @param		vp	A `Gui.ViewProviderDocumentObject` Control.ViewObject.
    #

    def setProperties(self, vp):
        # Hide unnecessary view properties
        vp.setEditorMode("DisplayMode", 2)
        vp.setEditorMode("Visibility", 2)

    ## @brief Method called by FreeCAD when Control is double-clicked in the Tree View.
    #
    #If no dialog is opened in the Task View, a new `ControlPanel` is opened.
    #If a `ControlPanel` is already opened, the Model tab on the Combo View
    #is swaped for the Tasks tab so that the panel becomes visible.
    #If another dialog is opened a warning is shown.
    #
    #
    # @param		vp	A `Gui.ViewProviderDocumentObject` Control.ViewObject.
    #

    def doubleClicked(self, vp):
        # Switch to the Task View if a Control panel is already opened
        if self.panel:
            FreeCADGui.Control.showTaskView()

        # Try to open new Control panel
        else:
            # Load the QDialog from a file and name it after this object
            form = FreeCADGui.PySideUic.loadUi(
                    path.join(PATH_TO_UI, "AnimationControl.ui"))
            form.setWindowTitle(vp.Object.Label)

            # Create a control panel and try to show it
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

    ## @brief Method called by the FreeCAD to customize a context menu for a Control.
    #
    #The *Transform* and *Set colors...* items are removed from the context menu
    #shown upon right click on `DocumentObjectGroupPython` Control in the
    #Tree View. The option to *Show control panel* is added instead.
    #
    #
    # @param		vp	A right-clicked `Gui.ViewProviderDocumentObject` Control.ViewObject.
    # @param		menu	A Qt's QMenu to be edited.
    #

    def setupContextMenu(self, vp, menu):
        # Add an option to open the Control panel
        menu.clear()
        action = menu.addAction("Show control panel")
        action.triggered.connect(lambda f=self.doubleClicked, arg=vp: f(arg))

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


## @brief ControlCommand class specifing Animate workbench's Control button/command.
#
#This class provides resources for a toolbar button and a menu button.
#It controls their behaivor(Active/Inactive) and responds to callbacks after
#either of them was clicked(Activated).
#

class ControlCommand(object):

    ## @brief Method used by FreeCAD to retrieve resources to use for this command.
    #
    # @return
    #    A dict with items `PixMap`, `MenuText` and `ToolTip` which contain
    #    a path to a command icon, a text to be shown in a menu and
    #    a tooltip message.
    #

    def GetResources(self):
        return {'Pixmap': path.join(PATH_TO_ICONS, "ControlCmd.xpm"),
                'MenuText': "Control",
                'ToolTip': "Create Control instance."}

    ## @brief Method used as a callback when the toolbar button or the menu item is clicked.
    #
    #This method creates a Control instance in currently active document.
    #Afterwards it adds a ControlProxy as a `Proxy` to this instance as well as
    #ViewProviderControlProxy to its `ViewObject.Proxy`, if FreeCAD runs in the
    #Graphic mode.
    #

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        a = doc.addObject("App::DocumentObjectGroupPython", "Control")
        ControlProxy(a)
        if FreeCAD.GuiUp:
            ViewProviderControlProxy(a.ViewObject)
        doc.recompute()
        return

    ## @brief Method to specify when the toolbar button and the menu item are enabled.
    #
    #The toolbar button `Control` and menu item `Control` are set to be active only
    #when there is an active document in which a Control instance can be created.
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
    FreeCADGui.addCommand('ControlCommand', ControlCommand())
