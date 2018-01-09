$(function () {
    $("#period-controls :input").change(function() {
        if (this.value == "monthly") {
            $("#s-price").text("$5");
            $("#p-price").text("$50");
        }

        if (this.value == "annual") {
            $("#s-price").text("$4");
            $("#p-price").text("$40");
        }
    });
});