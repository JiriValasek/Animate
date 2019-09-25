$(function(){
	function setCrossroadOrientation() {
		let btngroup = $("#cr-buttons");
		btngroup.css("visibility", "hidden");
		btngroup.attr("class","btn-group");
		if (window.innerWidth < (btngroup.position()["left"] + btngroup.offset()["left"] + btngroup.outerWidth())) {
			btngroup.attr("class", "btn-group-vertical");
			$("#crossroad .btn").css("text-align","left")
		} else {
			$("#crossroad .btn").css("text-align","center")
		}
		btngroup.css("visibility", "visible");

	}
	$(window).resize(setCrossroadOrientation);
	setCrossroadOrientation();
})