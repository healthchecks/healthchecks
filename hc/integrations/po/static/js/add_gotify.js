$(function() {
    function makeOption(item, escape) {
        var parts = item.text.split(":");
        return `<div>${parts[0]}. <span class="help">${parts[1]}</span></div>`;
    }

    var config = {
        maxItems: 1,
        controlInput: null,
        plugins: ["no_backspace_delete"],
        render: {option: makeOption, item: makeOption}
    };

    document.querySelectorAll("select").forEach((el) => {
        new TomSelect(el, config)
    });

});