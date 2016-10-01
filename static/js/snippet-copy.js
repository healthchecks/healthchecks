$(function() {
    if (/Mac/i.test(navigator.userAgent)) {
        // No support for Safari :(
        return;
    }

    var markup = '<button class="btn btn-default hidden-sm">' +
                 '<span class="icon-clippy"></span>' +
                 '</button>';



    $(".highlight").append(markup);


    var reBlankLines = new RegExp("^\\s*[\\r\\n]", "gm");
    var reTrailingWhitespace = new RegExp("\\s+$");

    var clipboard = new Clipboard(".highlight button", {
        text: function (trigger) {
            var snippetElement = $(trigger).parent().children().clone();
            /* remove pygmentize comment elements */
            snippetElement.find(".c, .cm, .cp, .c1, .cs").remove();
            /* remove blank lines and trailing whitespace */
            return snippetElement.text().replace(reBlankLines, '').replace(reTrailingWhitespace, '');
        }
    });

    clipboard.on("success", function(e) {
        $(e.trigger)
            .tooltip({title: "Copied!", trigger: "hover"})
            .tooltip("show")
            .on("hidden.bs.tooltip", function(){
                $(this).tooltip("destroy");
            })
    });

    clipboard.on("error", function(e) {
        prompt("Press Ctrl+C to select:", e.text)
    });
});
