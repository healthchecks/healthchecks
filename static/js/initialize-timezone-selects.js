$(function() {
    function makeOptions(domId) {
        var s = document.getElementById(domId).textContent;
        return s.split(",").map(tz => ({value: tz, group: domId}))
    }

    $("select[name=tz]").selectize({
        labelField: "value",
        searchField: ["value"],
        options: makeOptions("common-timezones").concat(makeOptions("all-timezones")),
        optgroups: [
            {label: "Common time zones", value: "common-timezones"},
            {label: "All time zones (search by typing)", value: "all-timezones"}
        ],
        optgroupField: "group"
    });
});