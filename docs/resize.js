/*
 @licstart  The following is the entire license notice for the
 JavaScript code in this file.

 Copyright (C) 1997-2017 by Dimitri van Heesch

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 2 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License along
 with this program; if not, write to the Free Software Foundation, Inc.,
 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

 @licend  The above is the entire license notice
 for the JavaScript code in this file
 */
function initResizable()
{
  var content,header,desktop_vp=768;

  function resizeHeight()
  {
    var headerHeight = header.outerHeight();
    var footerHeight = footer.outerHeight();
    var windowHeight = $(window).height() - headerHeight - footerHeight;
    content.css({height:windowHeight + "px"});
  }

  header  = $("#top");
  content = $("#doc-content");
  footer  = $("#nav-path");
  $(window).resize(function() { resizeHeight(); });
  var url = location.href;
  var i=url.indexOf("#");
  if (i>=0) window.location.hash=url.substr(i);
  $(window).load(resizeHeight);
}
/* @license-end */
