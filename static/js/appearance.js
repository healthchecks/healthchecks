$(function () {
    $("input[type=radio][name=theme]").change(function() {
        this.form.submit();
    });
    
    // Initialize selectize for default time zone selection dropdown
    var $select = $("select[name=default_timezone_selection]").selectize();
    
    // Auto-submit form when time zone selection changes (but not when cleared)
    if ($select.length > 0) {
        $select[0].selectize.on('change', function(value) {
            // Only submit if a valid value is selected (not empty)
            if (value && value.trim() !== '') {
                this.$input[0].form.submit();
            }
        });
    }
    
    // Detect browser time zone and update the default option before initializing selectize
    var detectedTimezone = '';
    try {
        detectedTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        var $defaultOption = $('#default-option');
        if ($defaultOption.length > 0 && detectedTimezone) {
            $defaultOption.text('Default (' + detectedTimezone + ')');
        }
    } catch (e) {
        // Fallback if time zone detection fails
    }

    // Initialize selectize for browser time zone override dropdown
    var $browserTzSelect = $("select[name=browser_timezone_override]").selectize({
        maxItems: 1,
        searchField: 'text',
        placeholder: 'Select a time zone...',
        openOnFocus: false, // Don't open immediately on focus
        render: {
            item: function(item, escape) {
                if (item.value === 'default') {
                    return '<div>' + escape(detectedTimezone ? 'Default (' + detectedTimezone + ')' : 'Default') + '</div>';
                }
                return '<div>' + escape(item.text) + '</div>';
            },
            option: function(item, escape) {
                if (item.value === 'default') {
                    return '<div>' + escape(detectedTimezone ? 'Default (' + detectedTimezone + ')' : 'Default') + '</div>';
                }
                return '<div>' + escape(item.text) + '</div>';
            }
        },
        onDropdownClose: function($dropdown) {
            // Remove our custom class when closing
            $dropdown.removeClass('dropdown-upward');
        },
        onDropdownOpen: function($dropdown) {
            var $input = this.$input;
            
            // Temporarily hide dropdown to prevent flicker during repositioning
            $dropdown.css('visibility', 'hidden');
            
            // Use setTimeout to ensure our positioning happens after selectize's positioning
            setTimeout(function() {
                // Preferred height for 6-8 options (~280px) - larger to encourage upward  
                var preferredHeight = 280;
                var minHeight = 120; // Minimum height for at least 4 options
                var padding = 50; // Larger padding to encourage upward opening
                
                var viewportHeight = window.innerHeight || document.documentElement.clientHeight;
                
                // Get the actual visible selectize control element (not the hidden select)
                var $selectizeControl = $input.next('.selectize-control');
                if (!$selectizeControl.length) {
                    // Try parent approach if next() doesn't work
                    $selectizeControl = $input.parent().find('.selectize-control');
                }
                if (!$selectizeControl.length) {
                    // Last resort: find by element with selectize class
                    $selectizeControl = $('select[name="browser_timezone_override"]').next('.selectize-control');
                }
                
                // Find the visible selectize control for positioning
                var visibleInputRect;
                if ($selectizeControl.length > 0) {
                    visibleInputRect = $selectizeControl[0].getBoundingClientRect();
                } else {
                    // Fallback: use the dropdown's parent position
                    var $dropdownParent = $dropdown.parent();
                    visibleInputRect = $dropdownParent[0].getBoundingClientRect();
                }
                
                var spaceBelow = viewportHeight - visibleInputRect.bottom;
                var spaceAbove = visibleInputRect.top;
                
                // Smart positioning logic: prefer upward if it gives more space
                var availableBelow = spaceBelow - padding;
                var availableAbove = spaceAbove - padding;
            
            if (availableBelow >= preferredHeight) {
                // Plenty of space below - use preferred height downward
                $dropdown.css({
                    'position': 'absolute',
                    'top': '100%',
                    'bottom': 'auto'
                });
                $dropdown.find('.selectize-dropdown-content').css('max-height', preferredHeight + 'px');
            } else if (availableAbove >= preferredHeight) {
                // Better space above - open upward with preferred height
                $dropdown.addClass('dropdown-upward');
                var upwardPosition = -preferredHeight - 5;
                
                $dropdown.css({
                    'position': 'absolute',
                    'top': upwardPosition + 'px',
                    'bottom': 'auto',
                    'margin-bottom': '0',
                    'margin-top': '0',
                    'transform': 'none'
                });
                
                $dropdown[0].style.setProperty('top', upwardPosition + 'px', 'important');
                $dropdown[0].style.setProperty('bottom', 'auto', 'important');
                
                $dropdown.find('.selectize-dropdown-content').css('max-height', preferredHeight + 'px');
            } else if (availableBelow >= minHeight) {
                // Some space below - use what's available downward
                $dropdown.css({
                    'position': 'absolute',
                    'top': '100%',
                    'bottom': 'auto'
                });
                $dropdown.find('.selectize-dropdown-content').css('max-height', availableBelow + 'px');
            } else if (spaceAbove >= preferredHeight + padding) {
                // Not enough space below, but plenty above - open upward with preferred height
                console.log('Opening upward with preferred height');
                $dropdown.addClass('dropdown-upward');
                var upwardPosition = -preferredHeight - 5;
                
                // Multiple attempts to force upward positioning
                $dropdown.css({
                    'position': 'absolute',
                    'top': upwardPosition + 'px',
                    'bottom': 'auto',
                    'margin-bottom': '0',
                    'margin-top': '0',
                    'transform': 'none'
                });
                
                // Force it again with setAttribute for more aggressive override
                $dropdown[0].style.setProperty('top', upwardPosition + 'px', 'important');
                $dropdown[0].style.setProperty('bottom', 'auto', 'important');
                
                $dropdown.find('.selectize-dropdown-content').css('max-height', preferredHeight + 'px');
            } else if (spaceAbove >= minHeight + padding) {
                // Limited space above - use what's available
                console.log('Opening upward with limited height');
                $dropdown.addClass('dropdown-upward');
                var availableHeight = spaceAbove - padding;
                var upwardPosition = -availableHeight - 5;
                
                $dropdown.css({
                    'position': 'absolute',
                    'top': upwardPosition + 'px',
                    'bottom': 'auto',
                    'margin-bottom': '0',
                    'margin-top': '0',
                    'transform': 'none'
                });
                
                // Force it with setProperty for aggressive override
                $dropdown[0].style.setProperty('top', upwardPosition + 'px', 'important');
                $dropdown[0].style.setProperty('bottom', 'auto', 'important');
                
                $dropdown.find('.selectize-dropdown-content').css('max-height', availableHeight + 'px');
            } else {
                // Very limited space - use the larger of the two spaces
                if (spaceBelow >= spaceAbove) {
                    // Use space below
                    $dropdown.css({
                        'position': 'absolute',
                        'top': '100%',
                        'bottom': 'auto'
                    });
                    $dropdown.find('.selectize-dropdown-content').css('max-height', Math.max(spaceBelow - padding, 120) + 'px');
                } else {
                    // Use space above
                    console.log('Opening upward (limited space scenario)');
                    $dropdown.addClass('dropdown-upward');
                    var upwardHeight = Math.max(spaceAbove - padding, 120);
                    var upwardPos = -upwardHeight - 5;
                    
                    $dropdown.css({
                        'position': 'absolute',
                        'top': upwardPos + 'px',
                        'bottom': 'auto',
                        'margin-bottom': '0',
                        'margin-top': '0',
                        'transform': 'none'
                    });
                    
                    // Force it with setProperty for aggressive override
                    $dropdown[0].style.setProperty('top', upwardPos + 'px', 'important');
                    $dropdown[0].style.setProperty('bottom', 'auto', 'important');
                    
                    $dropdown.find('.selectize-dropdown-content').css('max-height', upwardHeight + 'px');
                }
            }
            
                // Ensure overflow is always auto for scrolling
                $dropdown.find('.selectize-dropdown-content').css('overflow-y', 'auto');
                
                // Show dropdown after positioning is complete
                $dropdown.css('visibility', 'visible');
            }, 0); // No delay to minimize flicker
        }
    });
    
    // Auto-submit form when browser time zone override changes (but not when cleared)
    if ($browserTzSelect.length > 0) {
        $browserTzSelect[0].selectize.on('change', function(value) {
            // Only submit if a valid value is selected (not empty)
            if (value && value.trim() !== '') {
                this.$input[0].form.submit();
            }
        });
    }
    
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
