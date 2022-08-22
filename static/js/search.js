$(function() {
    var base = document.getElementById("base-url").getAttribute("href").slice(0, -1);
    var input = $("#docs-search");

    input.on("keyup focus", function() {
        var q = this.value;
        if (q.length < 3) {
            $("#search-results").removeClass("on");
            $("#docs-nav").removeClass("off");
            return
        }

        $.ajax({
            url: base + "/docs/search/",
            type: "get",
            data: {q: q},
            success: function(data) {
                if (q != input.val()) {
                    return;  // ignore stale results
                }

                $("#search-results").html(data).addClass("on");
                $("#docs-nav").addClass("off");
            }
        });
    });
});