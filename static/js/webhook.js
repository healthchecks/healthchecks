$(function() {
    $("#webhook_headers").on("click", ".webhook_header_btn.btn-danger", function(e) {
        e.preventDefault();
        $(this).closest("div.row").remove();
    });

    $("#webhook_headers").on("click", ".webhook_header_btn.btn-info", function(e) {
        e.preventDefault();

        // Add new header form
        $("#webhook_headers").append(
'<div class="row">\
    <div class="col-xs-6 col-sm-6" style="padding-right: 0px;">\
        <input type="text" class="form-control" name="header_key[]" placeholder="Key">\
    </div>\
    <div class="col-xs-6 col-sm-6" style="padding-left: 0px;">\
        <div class="input-group">\
            <input type="text" class="form-control" name="header_value[]" placeholder="Value">\
            <span class="input-group-btn">\
                <button class="webhook_header_btn btn btn-danger" type="button" class="btn">X</button>\
            </span>\
        </div>\
    </div>\
</div>');
    });
});