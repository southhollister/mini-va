jQuery.fn.reverse = [].reverse;

$(document).ready(function(){
	
	var ht = 0;

	$(".current-tran").each(function(i, obj){

		$(obj).delay((50*i)*$(obj).text().length).fadeIn(100)
        ht += $(obj).height();
	});


	$("#convo-history").stop().animate({
            scrollTop: ht
    });

});