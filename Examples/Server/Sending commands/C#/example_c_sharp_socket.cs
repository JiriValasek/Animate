// **********************************************************************************
// *                                                                                *
// * MIT License                                                                    *
// *                                                                                *
// * Copyright(c) 2019 Jiří Valášek                                                 *
// *                                                                                *
// * Permission is hereby granted, free of charge, to any person obtaining a copy   *
// * of this software and associated documentation files (the "Software"), to deal  *
// * in the Software without restriction, including without limitation the rights   *
// * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell      *
// * copies of the Software, and to permit persons to whom the Software is          *
// * furnished to do so, subject to the following conditions:                       *
// *                                                                                *
// * The above copyright notice and this permission notice shall be included in all *
// * copies or substantial portions of the Software.                                *
// *                                                                                *
// * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR     *
// * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,       *
// * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE    *
// * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER         *
// * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,  *
// * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE  *
// * SOFTWARE.                                                                      *
// *                                                                                *
// **********************************************************************************

using System;
using System.Net.Sockets;
using System.Text;

namespace AnimateServerExample
{
    class Program
    {
        // Sends a command to a server and receives a response
        /// <summary>
        /// Sends a <paramref name="command"/> to a <paramref name="server"/> and receives a response
        /// </summary>
        /// <remarks>
        /// <para>
        /// This method is designed to communicate with an Animate server tool in FreeCAD. 
        /// If you use it for interproess communication (IPC) on your localhost, use IP address "127.0.0.1". 
        /// Also, command strings must become valid FreeCAD commands when printed.
        /// </para>
        /// <para>
        /// To have a valid command string do not use "\n" inside strings in your commands as this causes "EOL while scanning string literal" exception. 
        /// Use "\\n" to break line in strings inside commands. 
        /// Also, you can send multiple FreeCAD commands in one message if you separate them by "\n" e.g. "FreeCAD.Console.PrintError('Hi from C#\\n')\nFreeCAD.Console.PrintError('Good bye from C#\\n')". 
        /// </para>
        /// </remarks>
        /// <param name="server">A string with an IP address e.g. "127.0.0.1" or domain name such as "www.google.com".</param>
        /// <param name="port">An UInt16 TCP port number to connect to.</param>
        /// <param name="command">A String command to be send to the <paramref name="server"/>.</param>
        /// <param name="receiveTimeout">An Int32 time in milliseconds to wait for a response.</param>
        /// <param name="receiveBufferSize">An Int32 size of a receive buffer in bytes.</param>
        /// <example>
        /// <code>
        /// SendCommand("127.0.0.1", 54321, "FreeCAD.Console.PrintError(\"Hi from C#\\n\")");
        /// </code>
        /// </example>
        static void SendCommand(String server, UInt16 port, String command, Int32 receiveTimeout = 5000, Int32 receiveBufferSize = 512)
        {
            TcpClient tcpclient;
            NetworkStream stream;
            try
            {
                tcpclient = new TcpClient(server, port);
                tcpclient.ReceiveTimeout = receiveTimeout;
                tcpclient.SendBufferSize = receiveBufferSize;

                // Prepare command message data
                Byte[] encodedCommand = Encoding.UTF8.GetBytes(command);
                Byte[] data = new Byte[2 + encodedCommand.Length];
                UInt16 messageLength = (UInt16)(encodedCommand.Length);
                data[0] = (Byte)(messageLength >> 8);
                data[1] = (Byte)(messageLength & 0xFF);
                for (int i = 0; i < encodedCommand.Length; i++)
                {
                    data[2 + i] = encodedCommand[i];
                }

                // Send data
                stream = tcpclient.GetStream();
                stream.Write(data, 0, data.Length);
                Console.WriteLine("Sending: {0}", command);

                // Receive and display a response
                data = new Byte[tcpclient.ReceiveBufferSize];
                messageLength = (UInt16)stream.Read(data, 0, data.Length);
                String responseData = Encoding.UTF8.GetString(data, 2, messageLength); // skip bytes describing message size
                Console.WriteLine("Received: {0}", responseData);

                // Close connection
                stream.Close();
                tcpclient.Close();
            }
            catch (Exception e)
            {
                Console.WriteLine("Exception occurred: {0}", e.Message);
            }
        }

        static void Main(string[] args)
        {
            SendCommand("127.0.0.1", 54321, "FreeCAD.Console.PrintError(\"Hi from C#\\n\")");
            Console.WriteLine("Press enter to close this window.");
            Console.Read();
        }
    }
}