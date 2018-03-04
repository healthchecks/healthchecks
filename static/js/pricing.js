$(function () {
    $("#period-controls :input").change(function() {
        if (this.value == "monthly") {
            $("#s-price").text("$20");
            $("#p-price").text("$80");
        }

        if (this.value == "annual") {
            $("#s-price").text("$16");
            $("#p-price").text("$64");
        }
    });
});