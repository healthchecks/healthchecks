$(function () {
    $pw = $("#password");
    $meter = $("#meter");
    $pw.on("input", function() {
        var result = zxcvbn($pw.val());
        $meter.attr("class", "score-" + result.score);
    });
});
