$(function () {
    $("select[name=tz]").selectize();
    
    // Auto-hide success messages after 3 seconds (only on settings pages)
    // To apply this to ALL panel footers across the entire app, change the selector to:
    // var $footers = $('.panel-footer');
    // Note: This would affect project settings, team management, API keys, etc.
    // Consider adding data attributes or specific classes to distinguish message types
    setTimeout(function() {
        var $footers = $('.settings-block').closest('.panel').find('.panel-footer');
        var $panels = $footers.closest('.panel');
        
        if ($footers.length === 0) return; // No settings success messages to hide
        
        // Get current computed border color and animate to default
        var currentColor = $panels.css('border-color');
        var defaultColor = '#ddd';
        
        // Set initial color explicitly and add transition
        $panels.css({
            'border-color': currentColor,
            'transition': 'border-color 600ms ease'
        });
        
        // Trigger the color change after a small delay to ensure transition applies
        setTimeout(function() {
            $panels.css('border-color', defaultColor);
        }, 50);
        
        $footers.slideUp(600);
    }, 3000);
});
