$(function () {
    var base = document.getElementById("base-url").getAttribute("href").slice(0, -1);
    var favicon = document.querySelector('link[rel="icon"]');

    // Schedule refresh to run every 3s when tab is visible and user
    // is active, every 60s otherwise
    var lastStatus = {};
    var lastStarted = {};
    function refreshStatus() {
        $.ajax({
            url: base + "?refresh=1",
            dataType: "json",
            timeout: 2000,
            success: function(data) {
                var anyDown = false;
                for (var code in data) {
                    var el = data[code];
                    anyDown = anyDown || (el.status == "down");

                    if (el.status != lastStatus[code]) {
                        $("#" + code + " div.status").attr("class", "status ic-" + el.status);
                        lastStatus[code] = el.status;
                    }

                    if (el.started != lastStarted[code]) {
                        $("#" + code + " div.spinner").toggleClass("started", el.started);
                        lastStarted[code] = el.started;
                    }
                }
                var downPostfix = anyDown ? "_down" : "";
                favicon.href = `${base}/static/img/favicon${downPostfix}.svg`;
            }
        });
    }

    adaptiveSetInterval(refreshStatus);
});
