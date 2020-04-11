$(function () {
    $("#period-controls :input").change(function() {
        if (this.value == "monthly") {
            $("#supporter-price").text("$5");
            $("#business-price").text("$20");
            $("#business-plus-price").text("$80");
        }

        if (this.value == "annual") {
            $("#supporter-price").text("$4");
            $("#business-price").text("$16");
            $("#business-plus-price").text("$64");
        }
    });

    $('[data-help]').tooltip({
        html: true,
        title: function() {
            return $("#" + this.dataset.help).html();
        }
    });
});