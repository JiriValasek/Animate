# -*- coding: utf-8 -*-

# ***************************************************************************
# *                                                                         *
# *   Animate workbench - FreeCAD Workbench for lightweight animation       *
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

"""@package RobotPanel
RobotPanel class for the Animate Workbench.

This class is used by RobTranslation and RobRotation components.
"""

import FreeCAD
import FreeCADGui

from PySide2.QtWidgets import QDialogButtonBox
from PySide2.QtCore import QObject


class RobotPanel(QObject):
    """
Class providing funcionality to a RobRotation panel inside the TaskView.

This class enables user to see a manipulator in different configurations.
It provides a dialogs to be shown in the TaskView. These dialogs have sliders
which allow user to go through a rotation range.

Attributes:
    robot_joints: A list of RobRotation and RobTranslation instances.
    form: A list of QDialog instances to show in the TaskView.
    """

    def __init__(self, robot_joints, forms):
        """
Initialization method for RobotPanel.

A class instance is created. A list of proxies for associated `RobRotation`
instances are loaded as well as corresponding QDialog forms.
Previously visible properties are set to be read-only as not to change when a
`RobotPanel` is open. Finally all sliders on dialogs are moved to
a position corresponding to a `RobRotation` angle.

Args:
    robot_joints: A list of RobRotation and RobTranslation instances.
    forms: A list of QDialog instances to show in the TaskView.
        """
        super(RobotPanel, self).__init__()
        self.robot_joints = robot_joints

        # Disable editing of RobRotation properties and store previous
        # joint variable values
        self.previous_joint_values = []
        for joint in robot_joints:
            if joint.Proxy.__class__.__name__ == "RobRotationProxy":
                self.previous_joint_values.append(joint.Theta)
            elif joint.Proxy.__class__.__name__ == "RobTranslationProxy":
                self.previous_joint_values.append(joint.d)

            for prop in joint.PropertiesList:
                joint.setEditorMode(prop, 1)
            # Leave some properties hidden
            joint.setEditorMode("Placement", 2)
            joint.setEditorMode("ValidRotation", 2)

        # Add QDialogs to be displayed in freeCAD
        self.form = forms

        # Add callbacks to sliders on all forms and move sliders to a position
        # corresponding with time values
        for i in range(len(forms)):
            forms[i].sld_value.valueChanged.connect(
                lambda value, form=forms[i], joint=robot_joints[i]:
                self.sliderChanged(value, form, joint))
            if joint.Proxy.__class__.__name__ == "RobRotationProxy":
                val = (100 * (robot_joints[i].Theta
                              - robot_joints[i].ThetaMinimum)) / \
                      (joint.ThetaMaximum - joint.ThetaMinimum)
            elif joint.Proxy.__class__.__name__ == "RobTranslationProxy":
                val = (100 * (robot_joints[i].d
                              - robot_joints[i].dMinimum)) / \
                      (joint.dMaximum - joint.dMinimum)

            forms[i].sld_value.setValue(val)

    def sliderChanged(self, value, form, joint):
        """
Feedback method called when any slider position is changed.

A joint value is extrapolated from the slider position. The value is shown
on the dialog and set to a joint. Finally, the FreeCAD document and
the FreeCADGui document are updated.

Args:
    value: A slider position.
    form: A Dialog panel on which slider was moved.
    joint: A RobRotation or RobTranslation associated with the `form`.
        """
        # Compute a time from the slider position and joint variable range
        if joint.Proxy.__class__.__name__ == "RobRotationProxy":
                val = value * (joint.ThetaMaximum - joint.ThetaMinimum) / 100 \
                      + joint.ThetaMinimum
                joint.Theta = val
        elif joint.Proxy.__class__.__name__ == "RobTranslationProxy":
                val = value * (joint.dMaximum - joint.dMinimum) / 100 \
                      + joint.dMinimum
                joint.d = val

        form.lbl_value.setText("Value: " + ("%5.3f" % val))

        # Recompute the document to show changes
        FreeCAD.ActiveDocument.recompute()
        FreeCADGui.updateGui()

    def reject(self):
        """
Feedback method called when 'Close' button was pressed to close the panel.

Joint properties are return to be editable/read-only/invisible as they
were before. After that `RobotPanel` is closed.

RobRotation and RobTranslation joint variables are set to the original values.
`RobotPanel` is closed. FreeCAD and FreeCADGui documents are updated.
        """
        # Return RobRotation times to previous values
        for i in range(len(self.robot_joints)):
            if self.robot_joints[i].Proxy.__class__.__name__ \
                    == "RobRotationProxy":
                self.robot_joints[i].Theta = self.previous_joint_values[i]
            elif self.robot_joints[i].Proxy.__class__.__name__ \
                    == "RobTranslationProxy":
                self.robot_joints[i].d = self.previous_joint_values[i]

        # Close the panel and recompute the document to show changes
        # Allow editing of Trajecotry properties again
        for joint in self.robot_joints:
            for prop in joint.PropertiesList:
                joint.setEditorMode(prop, 0)
            joint.ViewObject.Proxy.panel = None

            # Keep some properties read-only state if they were in it before
            joint.setEditorMode("ObjectPlacement", 1)
            joint.setEditorMode("ParentFramePlacement", 1)
            if joint.Proxy.__class__.__name__ == "RobRotationProxy":
                joint.setEditorMode("Theta", 1)
            elif joint.Proxy.__class__.__name__ == "RobTranslationProxy":
                joint.setEditorMode("d", 1)

            # Keep some properties hidden state if they were hidden before
            joint.setEditorMode("Placement", 2)
            joint.setEditorMode("ValidRotation", 2)

        FreeCADGui.Control.closeDialog()
        FreeCAD.ActiveDocument.recompute()
        FreeCADGui.updateGui()

    def getStandardButtons(self, *args):
        """
Method to set just one button (close) to close the dialog.

Args:
    *args: A tuple of unused arguments from Qt.
        """
        return QDialogButtonBox.Close

    def isAllowedAlterSelection(self):
        """
Method to tell FreeCAD if dialog is allowed to alter a selection.

Returns:
    False - this dialog does not change a selection.
        """
        return False

    def isAllowedAlterView(self):
        """
Method to tell FreeCAD if dialog is allowed to alter a view.

Returns:
    True - this dialog does change a view.
        """
        return True

    def isAllowedAlterDocument(self):
        """
Method to tell FreeCAD if dialog is allowed to alter a document.

Returns:
    True - this dialog does change a document.
        """
        return True
