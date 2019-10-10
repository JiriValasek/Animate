# -*- coding: utf-8 -*-

# *****************************************************************************
# *                                                                           *
# * MIT License                                                               *
# *                                                                           *
# * Copyright (c) 2019 Jiří Valášek                                           *
# *                                                                           *
# * Permission is hereby granted, free of charge, to any person obtaining     *
# * a copy of this software and associated documentation files                *
# * (the "Software"), to deal in the Software without restriction, including  *
# * without limitation the rights to use, copy, modify, merge, publish,       *
# * distribute, sublicense, and/or sell copies of the Software, and to permit *
# * persons to whom the Software is furnished to do so, subject to            *
# * the following conditions:                                                 *
# *                                                                           *
# * The above copyright notice and this permission notice shall be included   *
# * in all copies or substantial portions of the Software.                    *
# *                                                                           *
# * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS   *
# * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF                *
# * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.    *
# * IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR          *
# * ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,  *
# * TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH             *
# * THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                *
# *                                                                           *
# *****************************************************************************

# Add Animate workbench to the python path
import sys
path_to_animate = "C:\\Program Files\\FreeCAD 0.18\\Mod\\Animate"

if path_to_animate not in sys.path:
    sys.path.insert(0, path_to_animate)

# Import CommandClient
from communication import sendClientCommand

# Use CommandClient
sendClientCommand("127.0.0.1", 54333,
                  "FreeCAD.Console.PrintWarning('Hello World\\n')")
