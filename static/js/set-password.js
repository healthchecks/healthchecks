$(function () {
    var $pw = $("#password");
    var $meter = $("#meter");
    $pw.on("input", function() {
        var candidate = $pw.val();
        if (!candidate) {
            $meter.attr("class", "score-0");
            return;
        }

        var result = zxcvbn(candidate);
        // If user has entered anything at all cap score at 1
        var score = Math.max(result.score, 1);
        $meter.attr("class", "score-" + score);
    });
});
