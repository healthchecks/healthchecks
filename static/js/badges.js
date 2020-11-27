$(function() {

    $(".fetch-json").each(function(idx, el) {
        $.getJSON(el.dataset.url, function(data) {
            el.innerText = JSON.stringify(data);
        });
    });

    $("#show-svg").click(function() {
        $("#badges-svg").show();
        $("#badges-json").hide();
        $("#badges-shields").hide();
    })

    $("#show-json").click(function() {
        $("#badges-svg").hide();
        $("#badges-json").show();
        $("#badges-shields").hide();
    })

    $("#show-shields").click(function() {
        $("#badges-svg").hide();
        $("#badges-json").hide();
        $("#badges-shields").show();
    })

    $("#show-with-late").click(function() {
        $(".no-late").hide();
        $(".with-late").show();
    })

    $("#show-no-late").click(function() {
        $(".with-late").hide();
        $(".no-late").show();
    })

});
