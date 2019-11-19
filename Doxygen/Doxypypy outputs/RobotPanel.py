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

##@package RobotPanel
#RobotPanel class for the Animate Workbench.
#
#This class is used by RobTranslation and RobRotation components to let the user
#see whole joint range.
#

import FreeCAD
import FreeCADGui

from PySide2.QtWidgets import QDialogButtonBox
from PySide2.QtCore import QObject


## @brief Class providing funcionality to a RobRotation panel inside the TaskView.
#
#This class enables user to see a manipulator in different configurations.
#It provides a dialogs to be shown in the TaskView. These dialogs have sliders
#which allow user to go through a joint range.
#
#
#

class RobotPanel(QObject):

    ## @property		robot_joints
    # A list of RobRotation and RobTranslation instances.

    ## @property		form
    # A list of QDialog instances to show in the TaskView.

    ## @brief Initialization method for RobotPanel.
    #
    #A class instance is created. A list of proxies for associated `RobRotation`
    #and `RobTranslation` instances are loaded as well as corresponding QDialog
    #forms. Previously visible properties are set to be read-only as not to change
    #when a `RobotPanel` is open. Finally all sliders on dialogs are moved to
    #a position corresponding to current a `RobRotation` angle / `RobTranslation`
    #displacement. If current value exceeds given joint range, the slider is placed
    #to minimum or maximum.
    #
    #
    # @param		robot_joints	A list of RobRotation and RobTranslation instances.
    # @param		forms	A list of QDialog instances to show in the TaskView.
    #

    def __init__(self, robot_joints, forms):
        super(RobotPanel, self).__init__()
        self.robot_joints = robot_joints

        # Disable editing of RobRotation properties, leave some properties
        # hidden and store previous joint variable values
        self.previous_joint_values = []
        for joint in robot_joints:
            if joint.Proxy.__class__.__name__ == "RobRotationProxy":
                self.previous_joint_values.append(joint.theta)
                joint.setEditorMode("ValidRotation", 2)
            elif joint.Proxy.__class__.__name__ == "RobTranslationProxy":
                self.previous_joint_values.append(joint.d)
                joint.setEditorMode("ValidTranslation", 2)

            for prop in joint.PropertiesList:
                joint.setEditorMode(prop, 1)
            joint.setEditorMode("Placement", 2)
            joint.setEditorMode("RobotPanelActive", 2)
            joint.RobotPanelActive = True

        # Add QDialogs to be displayed in freeCAD
        self.form = forms

        # Add callbacks to sliders on all forms and move sliders to a position
        # corresponding with time values
        for i in range(len(forms)):
            rj = robot_joints[i]
            forms[i].sld_value.valueChanged.connect(
                lambda value, form=forms[i], joint=rj:
                self.sliderChanged(value, form, joint))
            if rj.Proxy.__class__.__name__ == "RobRotationProxy":
                val = (100 * (rj.theta - rj.thetaOffset - rj.thetaMinimum)) / \
                      (rj.thetaMaximum - rj.thetaMinimum)
                val = min([100, max([val, 0])])
            elif rj.Proxy.__class__.__name__ == "RobTranslationProxy":
                val = (100 * (rj.d - rj.dOffset - rj.dMinimum)) / \
                      (rj.dMaximum - rj.dMinimum)
                val = min([100, max([val, 0])])

            forms[i].sld_value.setValue(val)

    ## @brief Feedback method called when any slider position is changed.
    #
    #A joint value is extrapolated from the slider position. The value is shown
    #on the dialog and set to a joint. Finally, the FreeCAD document and
    #the FreeCADGui document are updated.
    #
    #
    # @param		value	A slider position.
    # @param		form	A Dialog panel on which slider was moved.
    # @param		joint	A RobRotation or RobTranslation associated with the `form`.
    #

    def sliderChanged(self, value, form, joint):
        # Compute a time from the slider position and joint variable range
        if joint.Proxy.__class__.__name__ == "RobRotationProxy":
                val = value * (joint.thetaMaximum - joint.thetaMinimum) / 100 \
                      + joint.thetaMinimum + joint.thetaOffset
                joint.theta = val
        elif joint.Proxy.__class__.__name__ == "RobTranslationProxy":
                val = value * (joint.dMaximum - joint.dMinimum) / 100 \
                      + joint.dMinimum + joint.dOffset
                joint.d = val

        form.lbl_value.setText("Value: " + ("%5.3f" % val))

        # Recompute the document to show changes
        FreeCAD.ActiveDocument.recompute()
        FreeCADGui.updateGui()

    ## @brief Feedback method called when 'Close' button was pressed to close the panel.
    #
    #Joint properties are return to be editable/read-only/invisible as they
    #were before. After that `RobotPanel` is closed.
    #
    #RobRotation and RobTranslation joint variables are set to the original values.
    #`RobotPanel` is closed. FreeCAD and FreeCADGui documents are updated.
    #

    def reject(self):
        # Return RobRotation times to previous values
        for i in range(len(self.robot_joints)):
            if self.robot_joints[i].Proxy.__class__.__name__ \
                    == "RobRotationProxy":
                self.robot_joints[i].theta = self.previous_joint_values[i]
            elif self.robot_joints[i].Proxy.__class__.__name__ \
                    == "RobTranslationProxy":
                self.robot_joints[i].d = self.previous_joint_values[i]

        # Close the panel and recompute the document to show changes
        # Allow editing of properties again
        for joint in self.robot_joints:
            for prop in joint.PropertiesList:
                joint.setEditorMode(prop, 0)
            joint.ViewObject.Proxy.panel = None

            # Keep some properties in read-only or hidden state
            # if they were in it before
            joint.setEditorMode("ObjectPlacement", 1)
            joint.setEditorMode("ParentFramePlacement", 1)
            if joint.Proxy.__class__.__name__ == "RobRotationProxy":
                joint.setEditorMode("theta", 1)
                joint.setEditorMode("ValidRotation", 2)
            elif joint.Proxy.__class__.__name__ == "RobTranslationProxy":
                joint.setEditorMode("d", 1)
                joint.setEditorMode("ValidTranslation", 2)
            joint.setEditorMode("Placement", 2)
            joint.setEditorMode("RobotPanelActive", 2)
            joint.RobotPanelActive = False

        FreeCADGui.Control.closeDialog()
        FreeCAD.ActiveDocument.recompute()
        FreeCADGui.updateGui()

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
