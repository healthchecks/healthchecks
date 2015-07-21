$(function () {
    $('[data-toggle="tooltip"]').tooltip();

    var code = $("#check-code").text();
    var url = $("#pitch-url").text();
    url = url.replace("http://", "//");

    var lastPing = null;
    var lastPingHuman = null;

    $("#run-it").click(function() {
        $.get(url);
    });

    function checkLastPing() {
        $.getJSON("/status/" + code + "/", function(data) {
            if (data.last_ping != lastPing) {
                lastPing = data.last_ping;
                $("#timer").data("timer", data.secs_to_alert);
            }

            var lph = data.last_ping_human;
            if (lph && lph.indexOf("seconds ago") > 0)
                data.last_ping_human = "seconds ago";

            if (data.last_ping_human != lastPingHuman) {
                lastPingHuman = data.last_ping_human;
                $("#last-ping").text(lastPingHuman);
            }
        });
    }

    function updateTimer() {
        var timer = parseInt($("#timer").data("timer"));
        if (timer == 0)
            return;

        var s = timer % 60;
        var m = parseInt(timer / 60) % 60;
        var h = parseInt(timer / 3600);
        $("#timer").text(h + "h " + m + "m " + s + "s");

        $("#timer").data("timer", timer - 1);
    }

    setInterval(checkLastPing, 3000);
    setInterval(updateTimer, 1000);

});