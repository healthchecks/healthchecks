$(function () {
    $("input[type=radio][name=theme]").change(function() {
        this.form.submit();
    });
    
    // Initialize selectize for default time zone selection dropdown
    var $select = $("select[name=default_timezone_selection]").selectize();
    
    // Auto-submit form when timezone selection changes
    if ($select.length > 0) {
        $select[0].selectize.on('change', function() {
            this.$input[0].form.submit();
        });
    }
});
