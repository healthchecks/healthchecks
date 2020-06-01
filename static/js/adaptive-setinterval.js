function adaptiveSetInterval(fn, runNow) {
    // unconditionally run every minute
    setInterval(fn, 60000);

    // scheduleRun() keeps calling fn and decreasing quota
    // every 3 seconds, until quota runs out.
    var quota = 0;
    var scheduledId = null;
    function scheduleRun() {
        if (quota > 0) {
            quota -= 1;
            clearTimeout(scheduledId);
            scheduledId = setTimeout(scheduleRun, 3000);
            fn();
        }
    }

    document.addEventListener("visibilitychange", function() {
        if (document.visibilityState == "visible") {
            // tab becomes visible: reset quota
            if (quota == 0) {
                quota = 20;
                scheduleRun();
            } else {
                quota = 20;
            }
        } else {
            // lost visibility, clear quota
            quota = 0;
        }
    });

    // user moves mouse: reset quota
    document.addEventListener("mousemove", function() {
        if (quota == 0) {
            quota = 20;
            scheduleRun();
        } else {
            quota = 20;
        }
    });

    quota = 20;
    scheduledId = setTimeout(scheduleRun, runNow ? 1 : 3000);
}
