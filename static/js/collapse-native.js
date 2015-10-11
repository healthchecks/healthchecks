// Native Javascript for Bootstrap 3 | Collapse
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
		window.Collapse = factory();
	}

})(function(){

	// COLLAPSE DEFINITION
	// ===================
	var Collapse = function( element, options ) {
		options = options || {};
		
		this.btn = typeof element === 'object' ? element : document.querySelector(element);
		this.accordion = null;
		this.collapse = null;
		this.duration = 300; // default collapse transition duration
		this.options = {};
		this.options.duration = /ie/.test(document.documentElement.className) ? 0 : (options.duration || this.duration);
		this.init();
	}

	// COLLAPSE METHODS
	// ================
	Collapse.prototype = {

		init : function() {
			this.actions();
			this.btn.addEventListener('click', this.toggle, false);

			// allows the collapse to expand
			// ** when window gets resized
			// ** or via internal clicks handers such as dropwowns or any other
			document.addEventListener('click', this.update, false);
			window.addEventListener('resize', this.update, false)
		},

		actions : function() {
			var self = this;

			this.toggle = function(e) {
				self.btn = self.getTarget(e).btn;
				self.collapse = self.getTarget(e).collapse;

				if (!/in/.test(self.collapse.className)) {
					self.open(e)
				} else {
					self.close(e)
				}
			},
			this.close = function(e) {
				e.preventDefault();
				self.btn = self.getTarget(e).btn;
				self.collapse = self.getTarget(e).collapse;
				self._close(self.collapse);
				self.btn.className = self.btn.className.replace(' collapsed','');
			},
			this.open = function(e) {
				e.preventDefault();
				self.btn = self.getTarget(e).btn;
				self.collapse = self.getTarget(e).collapse;
				self.accordion = self.btn.getAttribute('data-parent') && self.getClosest(self.btn, self.btn.getAttribute('data-parent'));

				self._open(self.collapse);
				self.btn.className += ' collapsed';

				if ( self.accordion !== null ) {
					var active = self.accordion.querySelectorAll('.collapse.in'), al = active.length, i = 0;
					for (i;i<al;i++) {
						if ( active[i] !== self.collapse) self._close(active[i]);						
					}
				}
			},
			this._open = function(c) {

				c.className += ' in';
				c.style.height = 0;
				c.style.overflow = 'hidden';
				c.setAttribute('area-expanded','true');

				// the collapse MUST have a childElement div to wrap them all inside, just like accordion/well
				var oh = this.getMaxHeight(c).oh, br = this.getMaxHeight(c).br;

				c.style.height = oh + br + 'px';
				setTimeout(function() {
					c.style.overflow = '';
				}, self.options.duration)
			},
			this._close = function(c) {

				c.style.overflow = 'hidden';
				c.style.height = 0;
				setTimeout(function() {
					c.className = c.className.replace(' in','');
					c.style.overflow = '';
					c.setAttribute('area-expanded','false');
				}, self.options.duration)
			},
			this.update = function(e) {
				var evt = e.type, tg = e.target, closest = self.getClosest(tg,'.collapse'),
					itms = document.querySelectorAll('.collapse.in'), i = 0, il = itms.length;
				for (i;i<il;i++) {
					var itm = itms[i], oh = self.getMaxHeight(itm).oh, br = self.getMaxHeight(itm).br;
					
					if ( evt === 'resize' && !/ie/.test(document.documentElement.className) ){
						setTimeout(function() {
							itm.style.height =  oh + br + 'px';
						}, self.options.duration)						
					} else if ( evt === 'click' && closest === itm ) {
						itm.style.height =  oh + br + 'px';								
					}
				}
			},
			this.getMaxHeight = function(l) { // get collapse trueHeight and border
				var t = l.children[0];
				var cs = l.currentStyle || window.getComputedStyle(l);

				return {
					oh : getOuterHeight(t),
					br : parseInt(cs.borderTop||0) + parseInt(cs.borderBottom||0)
				}
			},
			this.getTarget = function(e) {
				var t = e.currentTarget || e.srcElement,
					h = t.href && t.getAttribute('href').replace('#',''),
					d = t.getAttribute('data-target') && ( t.getAttribute('data-target') ),
					id = h || ( d && /#/.test(d)) && d.replace('#',''),
					cl = (d && d.charAt(0) === '.') && d, //the navbar collapse trigger targets a class
					c = id && document.getElementById(id) || cl && document.querySelector(cl);

				return {
					btn : t,
					collapse : c
				}
			},

			this.getClosest = function (el, s) { //el is the element and s the selector of the closest item to find
			// source http://gomakethings.com/climbing-up-and-down-the-dom-tree-with-vanilla-javascript/
				var f = s.charAt(0);
				for ( ; el && el !== document; el = el.parentNode ) {// Get closest match

					if ( f === '.' ) {// If selector is a class
						if ( document.querySelector(s) !== undefined ) { return el; }
					}

					if ( f === '#' ) { // If selector is an ID
						if ( el.id === s.substr(1) ) { return el; }
					}
				}
				return false;
			}
		}
    }

	var getOuterHeight = function (el) {
		var s = el && el.currentStyle || window.getComputedStyle(el),
			mtp = /px/.test(s.marginTop)	? Math.round(s.marginTop.replace('px',''))		: 0,
			mbp = /px/.test(s.marginBottom)	? Math.round(s.marginBottom.replace('px',''))	: 0,
			mte = /em/.test(s.marginTop)	? Math.round(s.marginTop.replace('em','')		* parseInt(s.fontSize)) : 0,
			mbe = /em/.test(s.marginBottom)	? Math.round(s.marginBottom.replace('em','')	* parseInt(s.fontSize)) : 0;

		return el.offsetHeight + parseInt( mtp ) + parseInt( mbp ) + parseInt( mte ) + parseInt( mbe ) //we need an accurate margin value	
	}

	// COLLAPSE DATA API
	// =================
    var Collapses = document.querySelectorAll('[data-toggle="collapse"]'), i = 0, cll = Collapses.length;
	for (i;i<cll;i++) {
		var item = Collapses[i], options = {};
		options.duration = item.getAttribute('data-duration');
		new Collapse(item,options);
	}

	//we must add the height to the pre-opened collapses
	window.addEventListener('load', function() {
		var openedCollapses = document.querySelectorAll('.collapse'), i = 0, ocl = openedCollapses.length;
		for (i;i<ocl;i++) {
			var oc = openedCollapses[i];
			if (/in/.test(oc.className)) {
				var s = oc.currentStyle || window.getComputedStyle(oc);
				var oh = getOuterHeight(oc.children[0]);
				var br = parseInt(s.borderTop||0) + parseInt(s.borderBottom||0);
				oc.style.height = oh + br + 'px';
			}
		}
	});

	return Collapse;

});
