$(function() {

    $(".json-response").each(function(idx, el) {
        $.getJSON(el.dataset.url, function(data) {
            el.innerHTML = "<code>" + JSON.stringify(data) + "</code>";
        });
    });

    $("#show-svg").click(function() {
        $("#badges-json").hide();
        $("#badges-svg").show();
    })

    $("#show-json").click(function() {
        $("#badges-svg").hide();
        $("#badges-json").show();
    })

});