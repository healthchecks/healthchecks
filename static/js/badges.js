$(function() {

    $(".json-response").each(function(idx, el) {
        $.getJSON(el.dataset.url, function(data) {
            el.innerHTML = "<code>" + JSON.stringify(data) + "</code>";
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
});
