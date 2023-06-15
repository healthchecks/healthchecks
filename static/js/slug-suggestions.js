$(function () {
    function slugify(text) {
        return text
            .normalize("NFKD")
            .split("")
            .map(ch => ch.charCodeAt(0) < 256 ? ch : "")
            .join("")
            .toLowerCase()
            .replace(/[^\w\s-]/g, "")
            .replace(/[-\s]+/g, "-")
            .replace(/^-+/, "")
            .replace(/-+$/, "");
    }

    $(".with-slug-suggestions").each(function() {
        var nameInput = $("input[name='name']", this);
        var slugInput = $("input[name='slug']", this);
        var btn = $(".use-suggested-slug", this);
        var help = $(".slug-help-block", this);

        function update() {
            var suggested = slugify(nameInput.val());
            if (suggested) {
                help.html(`Suggested value: <code>${suggested}</code>`);
            } else {
                help.text("Allowed characters: a-z, 0-9, hyphens, underscores.");
            }

            btn.attr("disabled", !suggested);
        }

        $(nameInput).on("keyup change", update);
        $(this).on("shown.bs.modal", update);

        btn.click(function() {
            slugInput.val(slugify(nameInput.val()));
        });
    });

});
