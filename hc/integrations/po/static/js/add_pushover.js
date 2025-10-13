$(function() {
    function makeOption(item, escape) {
        var parts = item.text.split(":");
        return `<div class="option">${parts[0]}. <span class="help">${parts[1]}</span></div>`;
    }

    $("select").selectize({render: {option: makeOption, item: makeOption}});    
});