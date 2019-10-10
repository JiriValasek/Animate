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

% Using Matlab's TCP client
% Set up parameters
ip = 'localhost';
port = 54321;
timeout = 20; %secs, client timeout for write and read
connection_timeout = 10; %secs, timeout for connecting client to server
command = "FreeCAD.Console.PrintError(""Hi from Matlab\n"")";

% Prepare a client and a command packet data
client = tcpclient(ip,port,'Timeout',timeout,...
                   'ConnectTimeout',connection_timeout);
data_length = uint16(length(command.char));
data = [uint8(bitshift(data_length,-8)),...
        uint8(bitand(data_length,hex2dec("FF"))),...
        uint8(command.char)];

% Send a command
disp("Sending: " + command)
client.write(data);

% Wait for a response
time = tic;
while (~client.BytesAvailable()) && (toc - time < timeout)
end 

% Receive and display the response
msg = client.read();
response = char(msg(3:end)); %remove bytes describing message size 
disp("Received: " + response);