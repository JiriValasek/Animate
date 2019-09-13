const cookie_name = "Animate_documentation_width";
var sidenav_collapsed, sidenav_minimized = false;
var handle_width = $(".ui-resizable-handle").outerWidth();
var md_screen_width = 768; //px

function saveWidthCookie(value){
	// saves a cookie with width value
	if (value !== undefined) {
		let date = new Date();
		//delete after 30 days
		date.setTime(date.getTime() + (30*24*60*60*1000));
		document.cookie = cookie_name + "=" + value + ";expires=" + date.toGMTString();
	}
}

function readWidthCookie() {
	// reads a cookie with width value
	let cookie_start = document.cookie.indexOf(cookie_name);
	if ( cookie_start == -1) {
		return 0;
	}
	let value_start = cookie_start + cookie_name.length + 1; // + 1 for the "="
	let value_end = document.cookie.indexOf(";", value_start);
	return document.cookie.substring(value_start, value_end);
}

function sidebarResizeHandler() {
	// adjusts document content and saves sidebar's width
	$("#doc-content").css("padding-left", $("#side-nav").outerWidth());
	if ( (document.getElementById("doc-content").scrollWidth <= $(window).width()) |
	     (readWidthCookie() > $("#side-nav").outerWidth()) ){
		saveWidthCookie($("#side-nav").outerWidth());
	} else {
		$(this).mouseup();
		setSidebarWidth(readWidthCookie());
	}
}

function setSidebarWidth(width) {
	// adjusts document content and sidebar's width
	$("#side-nav").css("width", width);
	$("#doc-content").css("padding-left", $("#side-nav").outerWidth());
}

function updateLayout() {
	// adjust height, width and position of webpage's content
	$("#doc-content").css("padding-top", $("#titlearea").outerHeight());
	$("#doc-content").css("min-height", $(window).height() - $("#nav-path").outerHeight() - $("#titlearea").outerHeight() - 10)
	$("#side-nav").css("top", $("#titlearea").outerHeight());
	updateSidebarHeight();
	$("#side-nav").resizable({ maxWidth: $("body").prop("clientWidth") - handle_width , minWidth: 0 });
	// collapse sidebar if screen is smaller than md
	if ($(window).width() < md_screen_width & !sidenav_minimized) {
		sidebarToggleMinimize();
	} else if ($(window).width() > md_screen_width & sidenav_minimized) {
		sidebarToggleMinimize();
	}
}

function sidebarToggleMinimize() {
	// Minimizes sidebar if screen is smaller than md
	if(!sidenav_minimized) {
		setSidebarWidth(0);
		sidenav_minimized = true;
	} else {
		let sidebar_width = readWidthCookie();
		if (!sidenav_collapsed){
			setSidebarWidth(sidebar_width);
		}
		sidenav_minimized = false;
	}
}

function sidebarToggleCollapse() {
	// collapse sidebar by double clicking it when screen larger than md
	if(!sidenav_minimized) {
		if ($("#side-nav").width()){
			setSidebarWidth(0);
			sidenav_collapsed = true;
		} else {
			let sidebar_width = readWidthCookie();
			setSidebarWidth(sidebar_width);
			sidenav_collapsed = false;
		}	
	}
}

function updateSidebarHeight(){
	// sidebar
	if (($("#nav-path").offset().top - $(window).scrollTop() - $("#titlearea").outerHeight()) < ($(window).height() - $("#titlearea").height())){
		$("#side-nav").css("height", $("#nav-path").offset().top - $(window).scrollTop() - $("#titlearea").height());
	} else {
		$("#side-nav").css("height", $(window).height() - $("#titlearea").height());
	}
}


$(function(){
	// Rewrite handlers etc. from resize.js
	$("#side-nav").resizable({ resize: function(event, ui) { sidebarResizeHandler(); }});
	$("#side-nav").resizable({ maxWidth: $("body").prop("clientWidth") - handle_width , minWidth: 0 });
	$(window).resize(updateLayout);
	let sidebar_width = readWidthCookie();
	if (sidebar_width) {
		setSidebarWidth(sidebar_width);
	} else {
		sidebarResizeHandler();
	}
	if ($(window).width() < md_screen_width){
		sidebarToggleMinimize();
	}
  	$(".ui-resizable-handle").dblclick(sidebarToggleCollapse);
  	$(window).load(updateLayout);
  	$(window).scroll(updateSidebarHeight);
	sidebarResizeHandler();
	updateLayout();
});