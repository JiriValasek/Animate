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

##@package communication
# Classes related to interprocess communications.
#
#The Classes in this module...
#

import sys
try:
    import FreeCAD
except ImportError:
    pass

from PySide2.QtCore import QThread, QByteArray, QDataStream, QIODevice
from PySide2.QtNetwork import QTcpServer, QTcpSocket, QAbstractSocket, \
                              QHostAddress

## Size of uint16 in bytes used to leave space at the beginning of each message
# to specify tcp message length (maximal length is 65535 bytes).
SIZEOF_UINT16 = 2

## Error code used in startServer() when trying to connect CommandServer to an
# invalid address.
SERVER_ERROR_INVALID_ADDRESS = 1

## Error code used in startServer() when trying to connect CommandServer to an
# occupied port.
SERVER_ERROR_PORT_OCCUPIED = 2

## Time to wait in milliseconds - used to wait for incoming message etc.
WAIT_TIME_MS = 30000

## Message send from a `CommandServer` to a `CommandClient.sendCommand()` or
# `sendClientCommand()` after successful execution of a command.
COMMAND_EXECUTED_CONFIRMATION_MESSAGE = "Command executed successfully"

## `CommandClient.sendCommand()` or `sendClientCommand()` return value after
# confirmation of successful command execution.
CLIENT_COMMAND_EXECUTED = 0

## `CommandClient.sendCommand()` or `sendClientCommand()` return value if
# command execution failed (invalid command string).
CLIENT_COMMAND_FAILED = 1

## `CommandClient.sendCommand()` or `sendClientCommand()` error code to signal
# that response was no received complete.
CLIENT_ERROR_RESPONSE_NOT_COMPLETE = 2

## `CommandClient.sendCommand()` or `sendClientCommand()` error code to signal
# that no response from `CommandServer` was received.
CLIENT_ERROR_NO_RESPONSE = 3

## `CommandClient.sendCommand()` or `sendClientCommand()` error code to signal
# that message block was not written to a TCP socket.
CLIENT_ERROR_BLOCK_NOT_WRITTEN = 4

## `CommandClient.sendCommand()` or `sendClientCommand()` error code to signal
# that connection a host `CommandServer` was not established.
CLIENT_ERROR_NO_CONNECTION = 5


## @brief `QThread` class used to receive commands, try to execute and respond to them.
#
#This class describes a `QThread` used to receive a command string from
#a `QTcpSocket`, try to execute received string and send a repspondse
#whether the execution was successful or not.
#
#
#

class CommandThread(QThread):

    ## @property		socketDescriptor
    # A Qt's qintptr socket descriptor to initialize tcpSocket.

    ## @property		blockSize
    # An int representing size of incoming tcp message.

    ## @brief Initialization method for CommandThread.
    #
    #A class instance is created, `socketDescriptor` and `blockSize` are
    #initializated.
    #
    #
    # @param		socketDescriptor	A Qt's qintptr socket descriptor to initialize tcpSocket.
    # @param		parent	A reference to an instance which will take thread's ownership.
    #

    def __init__(self, socketDescriptor, parent):
        super(CommandThread, self).__init__(parent)
        self.socketDescriptor = socketDescriptor
        self.blockSize = 0

    ## @brief Thread's functionality method.
    #
    #The starting point for the thread. After calling start(), the newly created
    #thread calls this function. This function then tries to make QTcpSocket.
    #It waits `WAIT_TIME_MS` for an incoming message. If message is received
    #it checks its a whole message using blockSize sent in the first word as
    #an UINT16 number. If a whole message is received, the thread tries to execute
    #the message string and sends back an appropriate response. The response is
    #*Command failed - "error string"* if the execution failed, or *Command
    #executed successfully* otherwise. Then the thread is terminated.
    #

    def run(self):
        # Try to connect to an incoming tcp socket using its socket descriptor
        tcpSocket = QTcpSocket()
        if not tcpSocket.setSocketDescriptor(self.socketDescriptor):
            FreeCAD.Console.PrintError("Socket not accepted.\n")
            return

        # Wait for an incoming message
        if not tcpSocket.waitForReadyRead(msecs=WAIT_TIME_MS):
            FreeCAD.Console.PrintError("No request send.\n")
            return

        # Make an input data stream
        instr = QDataStream(tcpSocket)
        instr.setVersion(QDataStream.Qt_4_0)

        # Try to read the message size
        if self.blockSize == 0:
            if tcpSocket.bytesAvailable() < 2:
                return
            self.blockSize = instr.readUInt16()

        # Check message is sent complete
        if tcpSocket.bytesAvailable() < self.blockSize:
            return

        # Read message and inform about it
        instr = instr.readString()
        FreeCAD.Console.PrintLog("CommandServer received> "
                                 + str(instr) + "\n")

        # Try to execute the message string and prepare  a response
        try:
            exec(str(instr))
        except Exception as e:
            FreeCAD.Console.PrintError("Executing external command failed:"
                                       + str(e) + "\n")
            message = "Command failed - " + str(e)
        else:
            FreeCAD.Console.PrintLog("Executing external command succeeded!\n")
            message = COMMAND_EXECUTED_CONFIRMATION_MESSAGE

        # Prepare the data block to send back and inform about it
        FreeCAD.Console.PrintLog("CommandServer sending> " + message + " \n")
        block = QByteArray()
        outstr = QDataStream(block, QIODevice.WriteOnly)
        outstr.setVersion(QDataStream.Qt_4_0)
        outstr.writeUInt16(0)
        outstr.writeQString(message)
        outstr.device().seek(0)
        outstr.writeUInt16(block.size() - 2)

        # Send the block, disconnect from the socket and terminate the QThread
        tcpSocket.write(block)
        tcpSocket.disconnectFromHost()
        tcpSocket.waitForDisconnected()


## @brief `QTcpServer` class used to receive commands and execute them.
#
#This class is used by a `ServerProxy` instance to provide the interprocess
#communication between itself and outside client.
#

class CommandServer(QTcpServer):
    ## @brief Initialization method for CommandServer.
    #
    #A class instance is created.
    #
    #
    # @param		parent	A reference to an instance which will take servers's ownership.
    #

    def __init__(self, parent=None):
        super(CommandServer, self).__init__(parent)

    ## @brief Method to handle an incoming connection by dispatching a `CommandThread`.
    #
    #This method is called by Qt when an incoming connection with a socket
    #descriptor is received. A new `CommandThread` is created to serve to a received
    #request from the socket description. The `CommandThread` is set to terminate
    #when finished and then started.
    #
    #
    # @param		socketDescriptor	A Qt's qintptr socket descriptor to initialize tcpSocket.
    #

    def incomingConnection(self, socketDescriptor):
        thread = CommandThread(socketDescriptor, self)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    ## @brief Method used to close the CommandServer and inform user about it.
    #

    def close(self):
        super(CommandServer, self).close()
        FreeCAD.Console.PrintLog("Server closed.\n")


## @brief Method used to check a selected IP is possible to use with a Qt's QHostAddress.
#
#The IP can be either IPv4 address or *"localhost"* string with possible capital
#letters anywhere. IPv6 is not supported for now.
#
#
# @param		ip	A str with an IP address selected.
#

def checkIPIsValid(ip):
    if ip.upper() == "LOCALHOST":
        return True

    numbers = ip.split(".")
    if len(numbers) == 4:
        if all([(0 <= int(num) <= 255) for num in numbers]):
            return True

    return False


## @brief Method used to try to start a `CommandServer` at a valid IP address and port.
#
#This method checks that a chosen `addr` is valid IP address to be used to
#create Qt's QHostAddress using `checkIPIsValid()`. If the IP address is valid,
#then a `CommandServer` instance is created and tried to be made listen at
#selected `addr` and `port`. If it fails, then the used port had to be occupied.
#
#
# @param		addr	A str with a valid IPv4 Address or *"localhost"*.
# @param		port	An int selecting a port to be used for the `CommandServer`.
#
# @return
#    An integer error code signifying that and error occurred(either
#    `ERROR_INVALID ADDRESS` or `ERROR_PORT_OCCUPIED`) or a CommnadServer
#    instance if everything went hunky-dory.
#

def startServer(addr, port):

    if not checkIPIsValid(addr):
        return SERVER_ERROR_INVALID_ADDRESS

    if addr.upper() == "LOCALHOST":
        addr = QHostAddress(QHostAddress.LocalHost)
    else:
        addr = QHostAddress(addr)

    server = CommandServer()
    if not server.listen(addr, port):
        FreeCAD.Console.PrintLog("Unable to start the server: %s.\n"
                                 % server.errorString())
        return SERVER_ERROR_PORT_OCCUPIED

    else:
        FreeCAD.Console.PrintLog("The server is running on address %s"
                                 % server.serverAddress().toString()
                                 + " and port %d.\n" % server.serverPort())
        return server


## @brief Class to be used for sending commands.
#
#This class can be used in FreeCAD's or regular python console to send commands
#to a `CommandServer` using `sendCommand()`. The class prints logs as it moves
#along.
#
#
#
# @code
#    from PySide2.QtNetwork import QHostAddress
#    from communication import CommandClient
#    host = QHostAddress(QHostAddress.LocalHost)
#    client = CommandClient(host,54321)
#    client.sendCommand('FreeCAD.Console.PrintWarning("Hello World\\n")\n')
#

class CommandClient:

    ## @property		host
    # A QtHostAddress to the `CommandServer`.

    ## @property		port
    # An int of port at which `CommandServer` is listening.

    ## @property		tcpSocket
    # A QTcpSocket used to contact `CommandSErver`

    ## @property		blockSize
    # An int representing size of incoming tcp message.

    ## @brief Initialization method for CommandClient.
    #
    #A class instance is created and its attributes are initialized.
    #
    #
    # @param		host	A QtHostAddress to the `CommandServer`.
    # @param		port	An int of port at which `CommandServer` is listening.
    #

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.tcpSocket = QTcpSocket()
        self.blockSize = 0

    ## @brief Method used to send commands from client to `CommandServer`.
    #
    #This method tries to connect to a specified host `CommandServer` via
    #`tcpSocket`. If connection was successful, the command `cmd` is sent.
    #Then the response is expected. If the response is equal to
    #COMMAND_EXECUTED_CONFIRMATION_MESSAGE, then the execution was successful.
    #The progress and result of `sendCommand` can be obtained from printed logs and
    #return value.
    #
    #
    # @param		cmd	A str command to be executed.
    #
    # @return
    #    `CLIENT_COMMAND_EXECUTED` if all went great and command was executed.
    #    `CLIENT_COMMAND_FAILED` if `cmd` execution failed.
    #    `CLIENT_ERROR_RESPONSE_NOT_COMPLETE` if a response received was incomplete.
    #    `CLIENT_ERROR_NO_RESPONSE` if there was no response within `WAIT_TIME_MS`.
    #    `CLIENT_ERROR_BLOCK_NOT_WRITTEN` if communication failed during sending.
    #    `CLIENT_ERROR_NO_CONNECTION` if no connection to a host was established.
    #

    def sendCommand(self, cmd):

        # connect a Qt slot to receive and print errors
        self.tcpSocket.error.connect(self.displayError)

        # Try to connect to a host server
        self.tcpSocket.connectToHost(self.host, self.port, QIODevice.ReadWrite)
        if not self.tcpSocket.waitForConnected(msecs=WAIT_TIME_MS):
            if "FreeCAD" in sys.modules:
                FreeCAD.Console.PrintError("CommandClient.sendCommand error: "
                                           + "No connection\n")
            else:
                print("CommandClient.sendCommand error: No connection\n")
            return CLIENT_ERROR_NO_CONNECTION

        # Prepare a command message to be sent
        block = QByteArray()
        outstr = QDataStream(block, QIODevice.WriteOnly)
        outstr.setVersion(QDataStream.Qt_4_0)
        outstr.writeUInt16(0)
        outstr.writeQString(cmd)
        outstr.device().seek(0)
        outstr.writeUInt16(block.size() - 2)

        # Try to send the message
        if "FreeCAD" in sys.modules:
            FreeCAD.Console.PrintMessage("CommandClient sending> "
                                         + cmd + "\n")
        else:
            print("CommandClient sending> " + cmd + "\n")
        self.tcpSocket.write(block)
        if not self.tcpSocket.waitForBytesWritten(msecs=WAIT_TIME_MS):
            if "FreeCAD" in sys.modules:
                FreeCAD.Console.PrintError("CommandClient.sendCommand error: "
                                           + "Block not written\n")
            else:
                print("CommandClient.sendCommand error: Block not written\n")
            return CLIENT_ERROR_BLOCK_NOT_WRITTEN

        # Wait for a response from the host server
        if not self.tcpSocket.waitForReadyRead(msecs=WAIT_TIME_MS):
            if "FreeCAD" in sys.modules:
                FreeCAD.Console.PrintError("CommandClient.sendCommand error: "
                                           + "No response received.\n")
            else:
                print("CommandClient.sendCommand error: "
                      + "No response received.\n")
            return CLIENT_ERROR_NO_RESPONSE

        # Try to read the response
        instr = QDataStream(self.tcpSocket)
        instr.setVersion(QDataStream.Qt_4_0)
        if self.blockSize == 0:
            if self.tcpSocket.bytesAvailable() < 2:
                return CLIENT_ERROR_RESPONSE_NOT_COMPLETE
            self.blockSize = instr.readUInt16()

        if self.tcpSocket.bytesAvailable() < self.blockSize:
            return CLIENT_ERROR_RESPONSE_NOT_COMPLETE
        response = instr.readString()
        if "FreeCAD" in sys.modules:
            FreeCAD.Console.PrintMessage("CommandClient received> "
                                         + response + "\n")
        else:
            print("CommandClient received> " + response + "\n")

        # Wait until the host server terminates the connection
        self.tcpSocket.waitForDisconnected()
        # Reset blockSize to prepare for sending next command
        self.blockSize = 0

        # Return value representing a command execution status
        if response == COMMAND_EXECUTED_CONFIRMATION_MESSAGE:
            return CLIENT_COMMAND_EXECUTED
        else:
            return CLIENT_COMMAND_FAILED

    ## @brief `Qt`'s slot method to print out received `tcpSocket`'s error.
    #
    #QAbstractSocket.RemoteHostClosedError is not printed, because it occurs
    #naturally when the `tcpSocket` closes after a transaction is over. Except that
    #all errors are printed.
    #
    #
    # @param		socketError	A QAbstractSocket::SocketError enum describing occurred error.
    #

    def displayError(self, socketError):
        if socketError != QAbstractSocket.RemoteHostClosedError:
            if "FreeCAD" in sys.modules:
                FreeCAD.Console.PrintError("CommandClient error occurred> %s."
                                           % self.tcpSocket.errorString()
                                           + "\n")
            else:
                print("CommandClient error occurred> %s."
                      % self.tcpSocket.errorString() + "\n")


## @brief Method to be used for sending commands.
#
#This method is an alternative to using `CommandClient`. It does not print any
#logs, just returns a value saying how the execution went.
#
#
# @param		cmd	A str command to be executed.
# @param		host	A QtHostAddress to the `CommandServer`.
# @param		port	An int of port at which `CommandServer` is listening.
#
#
# @param		wait_time	An int setting milliseconds to wait for connection or message.
#
# @return
#    `CLIENT_COMMAND_EXECUTED` if all went great and command was executed.
#    `CLIENT_COMMAND_FAILED` if `cmd` execution failed.
#    `CLIENT_ERROR_RESPONSE_NOT_COMPLETE` if a response received was incomplete.
#    `CLIENT_ERROR_NO_RESPONSE` if there was no response within `WAIT_TIME_MS`.
#    `CLIENT_ERROR_BLOCK_NOT_WRITTEN` if communication failed during sending.
#    `CLIENT_ERROR_NO_CONNECTION` if no connection to a host was established.
#

def sendClientCommand(host, port, cmd, wait_time=WAIT_TIME_MS):
    # Try to connect to a host server
    tcpSocket = QTcpSocket()
    tcpSocket.connectToHost(host, port, QIODevice.ReadWrite)
    if not tcpSocket.waitForConnected(msecs=wait_time):
        return CLIENT_ERROR_NO_CONNECTION

    # Prepare a command message to be sent
    block = QByteArray()
    outstr = QDataStream(block, QIODevice.WriteOnly)
    outstr.setVersion(QDataStream.Qt_4_0)
    outstr.writeUInt16(0)
    outstr.writeQString(cmd)
    outstr.device().seek(0)
    outstr.writeUInt16(block.size() - 2)
    tcpSocket.write(block)

    # Try to send the message
    if not tcpSocket.waitForBytesWritten(msecs=wait_time):
        return CLIENT_ERROR_BLOCK_NOT_WRITTEN

    # Wait for a response from the host server
    if not tcpSocket.waitForReadyRead(msecs=10000):
        return CLIENT_ERROR_NO_RESPONSE

    # Try to read the response
    instr = QDataStream(tcpSocket)
    instr.setVersion(QDataStream.Qt_4_0)
    blockSize = 0
    if blockSize == 0:
        if tcpSocket.bytesAvailable() < 2:
            return CLIENT_ERROR_RESPONSE_NOT_COMPLETE
        blockSize = instr.readUInt16()
    if tcpSocket.bytesAvailable() < blockSize:
        return CLIENT_ERROR_RESPONSE_NOT_COMPLETE

    # Wait until the host server terminates the connection
    tcpSocket.waitForDisconnected()

    # Return value representing a command execution status
    if instr.readString() == COMMAND_EXECUTED_CONFIRMATION_MESSAGE:
        return CLIENT_COMMAND_EXECUTED
    else:
        return CLIENT_COMMAND_FAILED
