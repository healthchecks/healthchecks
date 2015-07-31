$(function () {

    var secsToText = function(total) {
        total = Math.floor(total / 60);
        var m = total % 60; total = Math.floor(total / 60);
        var h = total % 24; total = Math.floor(total / 24);
        var d = total % 7; total = Math.floor(total / 7);
        var w = total;

        var result = "";
        if (w) result += w + (w == 1 ? " week " : " weeks ");
        if (d) result += d + (d == 1 ? " day " : " days ");
        if (h) result += h + (h == 1 ? " hour " : " hours ");
        if (m) result += m + (m == 1 ? " minute " : " minutes ");

        return result;
    }

    var periodSlider = document.getElementById("period-slider");
    noUiSlider.create(periodSlider, {
        start: [20],
        connect: "lower",
        range: {
            'min': [60, 60],
            '30%': [3600, 3600],
            '82.80%': [86400, 86400],
            'max': 604800
        },
        pips: {
            mode: 'values',
            values: [60, 1800, 3600, 43200, 86400, 604800],
            density: 5,
            format: {
                to: secsToText,
                from: function() {}
            }
        }
    });

    periodSlider.noUiSlider.on("update", function(a, b, value) {
        var rounded = Math.round(value);
        $("#period-slider-value").text(secsToText(rounded));
        $("#update-timeout-timeout").val(rounded);
    });


    var graceSlider = document.getElementById("grace-slider");
    noUiSlider.create(graceSlider, {
        start: [20],
        connect: "lower",
        range: {
            'min': [60, 60],
            '30%': [3600, 3600],
            '82.80%': [86400, 86400],
            'max': 604800
        },
        pips: {
            mode: 'values',
            values: [60, 1800, 3600, 43200, 86400, 604800],
            density: 5,
            format: {
                to: secsToText,
                from: function() {}
            }
        }
    });

    graceSlider.noUiSlider.on("update", function(a, b, value) {
        var rounded = Math.round(value);
        $("#grace-slider-value").text(secsToText(rounded));
        $("#update-timeout-grace").val(rounded);
    });


    $('[data-toggle="tooltip"]').tooltip();

    $(".my-checks-name").click(function() {
        var $this = $(this);

        $("#update-name-form").attr("action", $this.data("url"));
        $("#update-name-input").val($this.data("name"));
        $('#update-name-modal').modal("show");
        $("#update-name-input").focus();

        return false;
    });

    $(".timeout-grace").click(function() {
        var $this = $(this);

        $("#update-timeout-form").attr("action", $this.data("url"));
        periodSlider.noUiSlider.set($this.data("timeout"))
        graceSlider.noUiSlider.set($this.data("grace"))
        $('#update-timeout-modal').modal({"show":true, "backdrop":"static"});

        return false;
    });

    $(".check-menu-remove").click(function() {
        var $this = $(this);

        $("#remove-check-form").attr("action", $this.data("url"));
        $(".remove-check-name").text($this.data("name"));
        $('#remove-check-modal').modal("show");

        return false;
    });


});