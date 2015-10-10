// Native Javascript for Bootstrap 3 | Tab
// by dnp_theme

(function(factory){

	// CommonJS/RequireJS and "native" compatibility
	if(typeof module !== "undefined" && typeof exports == "object") {
		// A commonJS/RequireJS environment
		if(typeof window != "undefined") {
			// Window and document exist, so return the factory's return value.
			module.exports = factory();
		} else {
			// Let the user give the factory a Window and Document.
			module.exports = factory;
		}
	} else {
		// Assume a traditional browser.
		window.Tab = factory();
	}

})(function(){

	// TAB DEFINITION
	// ===================
	var Tab = function( element,options ) {
		options = options || {};
		
		this.tab = typeof element === 'object' ? element : document.querySelector(element);
		this.tabs = this.tab.parentNode.parentNode;
		this.dropdown = this.tabs.querySelector('.dropdown');
		if ( this.tabs.classList.contains('dropdown-menu') ) {
			this.dropdown = this.tabs.parentNode;
			this.tabs = this.tabs.parentNode.parentNode;
		}
		this.options = {};

		// default tab transition duration
		this.duration = 150;
		this.options.duration = document.documentElement.classList.contains('ie') ? 0 : (options.duration || this.duration);
		this.init();
	}

	// TAB METHODS
	// ================
	Tab.prototype = {

		init : function() {
			var self = this;
			self.actions();
			self.tab.addEventListener('click', self.action, false);
		},

		actions : function() {
			var self = this;

			this.action = function(e) {
				e = e || window.e;
				var next = e.target; //the tab we clicked is now the next tab
				var nextContent = document.getElementById(next.getAttribute('href').replace('#','')); //this is the actual object, the next tab content to activate

				var activeTab = self.getActiveTab();
				var activeContent = self.getActiveContent();

				//toggle "active" class name
				activeTab.classList.remove('active');
				next.parentNode.classList.add('active');

				//handle dropdown menu "active" class name
				if ( !self.tab.parentNode.parentNode.classList.contains('dropdown-menu')){
					self.dropdown && self.dropdown.classList.remove('active');
				} else {
					self.dropdown && self.dropdown.classList.add('active');
				}

				//1. hide current active content first
				activeContent.classList.remove('in');

				setTimeout(function() {
					//2. toggle current active content from view
					activeContent.classList.remove('active');
					nextContent.classList.add('active');
				}, self.options.duration);
				setTimeout(function() {
					//3. show next active content
					nextContent.classList.add('in');
				}, self.options.duration*2);
				e.preventDefault();
			},

			this.getActiveTab = function() {
				var activeTabs = self.tabs.querySelectorAll('.active');
				if ( activeTabs.length === 1 && !activeTabs[0].classList.contains('dropdown') ) {
					return activeTabs[0]
				} else if ( activeTabs.length > 1 ) {
					return activeTabs[activeTabs.length-1]
				}

				console.log(activeTabs.length)
			},
			this.getActiveContent = function() {
				var a = self.getActiveTab().getElementsByTagName('A')[0].getAttribute('href').replace('#','');
				return a && document.getElementById(a)
			}
		}
	}


	// TAB DATA API
	// =================
    var Tabs = document.querySelectorAll("[data-toggle='tab'], [data-toggle='pill']"), tbl = Tabs.length, i=0;
	for ( i;i<tbl;i++ ) {
		var tab = Tabs[i], options = {};
		options.duration = tab.getAttribute('data-duration') && tab.getAttribute('data-duration') || false;
		new Tab(tab,options);
	}

	return Tab;

});
