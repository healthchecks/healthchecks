$(function() {
    var timezones = document.getElementById("all-timezones").textContent;
    $("select[name=tz]").selectize({
        labelField: "value",
        searchField: ["value"],
        options: timezones.split(",").map(tz => ({value: tz}))
    });
});