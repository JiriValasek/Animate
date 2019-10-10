% *************************************************************************
% *                                                                       *
% * MIT License                                                           *
% *                                                                       *
% * Copyright (c) 2019 Ji?í Valášek                                       *
% *                                                                       *
% * Permission is hereby granted, free of charge, to any person obtaining *
% * a copy of this software and associated documentation files            *
% * (the "Software"), to deal in the Software without restriction,        *
% * including without limitation the rights to use, copy, modify, merge,  *
% * publish, distribute, sublicense, and/or sell copies of the Software,  *
% * and to permit persons to whom the Software is furnished to do so,     *
% * subject to the following conditions:                                  *
% *                                                                       *
% * The above copyright notice and this permission notice shall be        *
% * included in all copies or substantial portions of the Software.       *
% *                                                                       *
% * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,       *
% * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF    *
% * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND                 *
% * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS   *
% * BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN       *
% * AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN  *
% * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE      *
% * SOFTWARE.                                                             *
% *                                                                       *
% *************************************************************************

% Using Matlabs's python binding and Animate communication module
% Set up parameters
animate_path = 'C:\\Program Files\\FreeCAD 0.18\\Mod\\Animate';
ip = "127.0.0.1";
port = 54321;
command = "FreeCAD.Console.PrintError(""Hi from Matlab\n"")";

% Add communications to the path
P = py.sys.path; % load python path
if count(P, animate_path) == 0
    % if the Animate folder is not there, add it
    insert(P,int32(0), animate_path);
end

% Create a CommandClient
client = py.communication.CommandClient(ip,port);

% Send a Command
client.sendCommand(command);