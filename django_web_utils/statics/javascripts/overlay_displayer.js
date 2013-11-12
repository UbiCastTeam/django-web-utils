/*******************************************
* Overlay displayer                        *
* Copyright: UbiCast, all rights reserved  *
* Author: Stephane Diemer                  *
*******************************************/

/* supported modes and required params for each mode:
"images":
    resource = {
        mode: "image",
        url: "url of image",
        title: "The title", // optionnal
        buttons: [], // optionnal
        on_hide: function () { } // optionnal
    };
    or
    resource = "url of image";
"iframe":
    resource = {
        mode: "iframe",
        url: "url of iframe",
        title: "The title", // optionnal
        buttons: [], // optionnal
        on_hide: function () { } // optionnal
    };
"html":
    resource = {
        mode: "html",
        html: "html code",
        title: "The title", // optionnal
        buttons: [], // optionnal
        on_hide: function () { } // optionnal
    };

buttons list should look like:
[
    { label: "button", id: "button_id", callback: function (btn_dom) { } }
]
*/

// global function
function isinstance(obj, type) {
    if (typeof obj == "object") {
        var matching = obj.constructor.toString().match(new RegExp(type, "i")); 
        return (matching !== null);
    }
    return false;
}


function OverlayDisplayer(options) {
    // params
    this.language = "en";
    this.enable_effects = true;
    this.enable_transition_effects = true;
    this.margin = 30;
    this.top_bar_height = 30;
    this.bottom_bar_height = 40;
    this.default_buttons_class = "";
    this.hide_on_escape = true;
    
    // vars
    this.messages = { };
    this.init_done = false;
    this.widget = null;
    this.max_width = 0;
    this.max_height = 0;
    this.image = null;
    this.displayed = false;
    this.top_bar_displayed = false;
    this.bottom_bar_displayed = false;
    this.display_mode = null;
    this.changing = true;
    this.next_command = null;
    this.resources = null;
    this.current_index = 0;
    this.current_resource = null;
    this.no_fixed = false;
    this.loading = {
        timeout_id: null,
        displayed: false
    };
    
    if (options)
        this.set_options(options);
    this.set_language(this.language);
    var obj = this;
    $(document).ready(function () {
        obj._init();
    });
    $(window).resize(function () {
        obj.on_resize();
    });
    $(window).keypress(function (event) {
        if (obj.hide_on_escape && event.keyCode == 27)
            obj.hide();
    });
}

OverlayDisplayer.prototype.set_options = function (options) {
    if ("language" in options)
        this.language = options.language;
    if ("enable_effects" in options)
        this.enable_effects = options.enable_effects;
    if ("enable_transition_effects" in options)
        this.enable_transition_effects = options.enable_transition_effects;
    if ("margin" in options)
        this.margin = options.margin;
    if ("top_bar_height" in options)
        this.top_bar_height = options.top_bar_height;
    if ("bottom_bar_height" in options)
        this.bottom_bar_height = options.bottom_bar_height;
    if ("default_buttons_class" in options)
        this.default_buttons_class = options.default_buttons_class;
    if ("hide_on_escape" in options)
        this.hide_on_escape = options.hide_on_escape;
};

OverlayDisplayer.prototype._init = function () {
    if (this.init_done)
        return;
    this.init_done = true;
    var extra_class = "";
    if (navigator.platform == "iPad" || navigator.platform == "iPhone" || navigator.platform == "iPod") {
        this.enable_effects = false;
        this.enable_transition_effects = false;
        this.no_fixed = true;
        extra_class = "no-fixed";
    }
    var html = "";
    html += "<div class=\"overlay "+extra_class+"\">";
    html +=     "<div class=\"overlay-aligner\">";
    html +=         "<div class=\"overlay-layer\">";
    html +=             "<table class=\"overlay-table\"><tr class=\"overlay-table\"><td class=\"overlay-table\">";
    html +=                 "<div class=\"overlay-loading\"><div class=\"overlay-loading-content\">"+this.messages.loading+"</div></div>";
    html +=             "</td></tr></table>";
    html +=         "</div>";
    html +=         "<div class=\"overlay-layer\">";
    html +=             "<table class=\"overlay-table\"><tr class=\"overlay-table\"><td class=\"overlay-table\">";
    html +=                 "<div class=\"overlay-error\"><div class=\"overlay-error-content\">"+this.messages.error+"</div></div>";
    html +=             "</td></tr></table>";
    html +=         "</div>";
    html +=         "<div class=\"overlay-layer overlay-element-layer\">";
    html +=             "<table class=\"overlay-table\"><tr class=\"overlay-table\"><td class=\"overlay-table\">";
    html +=             "<div class=\"overlay-block\"><div class=\"overlay-block-bg\">";
    html +=                 "<div class=\"overlay-top-bar\">";
    html +=                     "<div class=\"overlay-title\"></div>";
    html +=                     "<div class=\"overlay-resources\"></div>";
    html +=                 "</div>";
    html +=                 "<div class=\"overlay-element-container\">";
    html +=                     "<div class=\"overlay-element-content\"></div>";
    html +=                     "<div class=\"overlay-element-mask\"></div>";
    html +=                     "<div class=\"overlay-hover-loading\"><div>"+this.messages.loading+"</div></div>";
    html +=                     "<div class=\"overlay-previous\">";
    html +=                         "<table class=\"overlay-table\"><tr class=\"overlay-table\"><td class=\"overlay-table\"><div class=\"overlay-btn-bg\">";
    html +=                             "<div class=\"overlay-btn-icon\">"+this.messages.previous+"</div></div></td></tr></table></div>";
    html +=                     "<div class=\"overlay-next\">";
    html +=                         "<table class=\"overlay-table\"><tr class=\"overlay-table\"><td class=\"overlay-table\"><div class=\"overlay-btn-bg\">";
    html +=                             "<div class=\"overlay-btn-icon\">"+this.messages.next+"</div></div></td></tr></table></div>";
    html +=                 "</div>";
    html +=                 "<div class=\"overlay-bottom-bar\">";
    html +=                     "<div class=\"overlay-buttons\"></div>";
    html +=                 "</div>";
    html +=                 "<div class=\"overlay-close\"><div></div></div>";
    html +=             "</div></div>";
    html +=             "</td></tr></table>";
    html +=         "</div>";
    html +=         "<div class=\"overlay-layer overlay-closer\"></div>";
    html +=     "</div>";
    html += "</div>";
    this.widget = $(html);
    $("body").append(this.widget);
    
    // bind events
    $(".overlay-previous", this.widget).click({ obj: this }, function (event) {
        event.data.obj.previous();
    });
    $(".overlay-next", this.widget).click({ obj: this }, function (event) {
        event.data.obj.next();
    });
    $(".overlay-close", this.widget).click({ obj: this }, function (event) {
        event.data.obj.hide();
    });
    $(".overlay-closer", this.widget).click({ obj: this }, function (event) {
        event.data.obj.hide();
    });

    this.on_resize();
    this.changing = false;
    this._check_next_command();
};

OverlayDisplayer.prototype.set_language = function (lang) {
    if (lang == "fr") {
        this.language = "fr";
        this.messages = {
            loading: "Chargement...",
            error: "Image introuvable",
            previous: "Pr&eacute;c&eacute;dent",
            next: "Suivant"
        };
    }
    else {
        this.language = "en";
        this.messages = {
            loading: "Loading...",
            error: "Image not found",
            previous: "Previous",
            next: "Next"
        };
    }
    if (this.init_done) {
        // replace messages
        $(".overlay-loading-content", this.widget).html(this.messages.loading);
        $(".overlay-error-content", this.widget).html(this.messages.error);
        $(".overlay-hover-loading", this.widget).html(this.messages.loading);
        $(".overlay-previous .overlay-btn-icon", this.widget).html(this.messages.previous);
        $(".overlay-next .overlay-btn-icon", this.widget).html(this.messages.next);
    }
};

OverlayDisplayer.prototype.on_resize = function () {
    this.max_width = $(window).width() - this.margin;
    this.max_height = $(window).height() - this.margin;
    if (this.top_bar_displayed)
        this.max_height -= this.top_bar_height;
    if (this.bottom_bar_displayed)
        this.max_height -= this.bottom_bar_height;
    if (this.max_width > 0)
        $(".overlay-element", this.widget).css("max-width", this.max_width+"px");
    if (this.max_height > 0)
        $(".overlay-element", this.widget).css("max-height", this.max_height+"px");
};

OverlayDisplayer.prototype._check_next_command = function () {
    if (this.next_command !== null) {
        var fct = this.next_command.fct;
        var params = this.next_command.params;
        this.next_command = null;
        if (fct == "go_to_index")
            this.go_to_index(params);
        else if (fct == "change")
            this.change(params);
        else if (fct == "show")
            this.show(params);
        else if (fct == "hide")
            this.hide();
    }
};

OverlayDisplayer.prototype._check_title_display = function (title) {
    if (title == $(".overlay-title", this.widget).html())
        return;
    
    var obj = this;
    if ((!title && (this.resources === null || this.resources.length < 2)) && obj.top_bar_displayed) {
        if (obj.enable_effects && obj.displayed) {
            $(".overlay-top-bar", obj.widget).slideUp("fast", function () {
                obj.widget.removeClass("top-bar-displayed");
                obj.top_bar_displayed = false;
                obj.on_resize();
                $(".overlay-title", obj.widget).html("");
            });
        }
        else {
            $(".overlay-top-bar", obj.widget).css("display", "none");
            obj.widget.removeClass("top-bar-displayed");
            obj.top_bar_displayed = false;
            obj.on_resize();
            $(".overlay-title", obj.widget).html("");
        }
    }
    else if (title) {
        if (obj.top_bar_displayed && obj.displayed) {
            if (obj.enable_transition_effects) {
                $(".overlay-title", obj.widget).fadeOut("fast", function () {
                    $(".overlay-title", obj.widget).html(title);
                    $(".overlay-title", obj.widget).fadeIn("fast");
                });
            }
            else {
                $(".overlay-title", obj.widget).html(title);
            }
        }
        else {
            $(".overlay-title", obj.widget).html(title);
            if (obj.enable_effects && obj.displayed) {
                $(".overlay-top-bar", obj.widget).slideDown("fast", function () {
                    obj.widget.addClass("top-bar-displayed");
                    obj.top_bar_displayed = true;
                    obj.on_resize();
                });
            }
            else {
                $(".overlay-top-bar", obj.widget).css("display", "block");
                obj.widget.addClass("top-bar-displayed");
                obj.top_bar_displayed = true;
                obj.on_resize();
            }
        }
    }
    else if ((this.resources !== null && this.resources.length > 1)) {
        if (!title && obj.top_bar_displayed) {
            if (obj.enable_effects && obj.displayed)
                $(".overlay-title", obj.widget).fadeOut("fast", function () {
                    $(".overlay-title", obj.widget).html("");
                });
            else
                $(".overlay-title", obj.widget).html("");
        }
        else if (!obj.top_bar_displayed) {
            if (obj.enable_effects && obj.displayed) {
                $(".overlay-top-bar", obj.widget).slideDown("fast", function () {
                    obj.widget.addClass("top-bar-displayed");
                    obj.top_bar_displayed = true;
                    obj.on_resize();
                });
            }
            else {
                $(".overlay-top-bar", obj.widget).css("display", "block");
                obj.widget.addClass("top-bar-displayed");
                obj.top_bar_displayed = true;
                obj.on_resize();
            }
        }
    }
};

OverlayDisplayer.prototype._check_buttons_display = function (buttons) {
    var obj = this;
    //alert(buttons[0].label);
    if (buttons) {
        // update buttons
        if (!buttons.loaded) {
            $(".overlay-buttons", obj.widget).html("");
            for (var i = 0; i < buttons.length; i++) {
                var btn = $("<button class=\""+this.default_buttons_class+"\"/>");
                if (buttons[i].id)
                    btn.attr("id", buttons[i].id);
                if (buttons[i].disabled)
                    btn.attr("disabled", "disabled");
                if (buttons[i].klass)
                    btn.attr("class", this.default_buttons_class+" "+buttons[i].klass);
                btn.html(buttons[i].label);
                btn.click({ callback: buttons[i].callback, btn_dom: btn }, function (event) { event.data.callback(event.data.btn_dom); });
                $(".overlay-buttons", obj.widget).append(btn);
            }
            buttons.loaded = true;
        }
        // show bottom bar
        if (!obj.bottom_bar_displayed) {
            if (obj.enable_effects && obj.displayed) {
                $(".overlay-bottom-bar", obj.widget).slideDown("fast", function () {
                    obj.widget.addClass("bottom-bar-displayed");
                    obj.bottom_bar_displayed = true;
                    obj.on_resize();
                });
            }
            else {
                $(".overlay-bottom-bar", obj.widget).css("display", "block");
                obj.widget.addClass("bottom-bar-displayed");
                obj.bottom_bar_displayed = true;
                obj.on_resize();
            }
        }
        // focus first button
        obj._focus_button();
    }
    else if (obj.bottom_bar_displayed) {
        // hide bottom bar and clear buttons
        if (obj.enable_effects && obj.displayed) {
            $(".overlay-bottom-bar", obj.widget).slideUp("fast", function () {
                obj.widget.removeClass("bottom-bar-displayed");
                $(".overlay-buttons", obj.widget).html("");
                obj.bottom_bar_displayed = false;
                obj.on_resize();
            });
        }
        else {
            $(".overlay-bottom-bar", obj.widget).css("display", "none");
            obj.widget.removeClass("bottom-bar-displayed");
            $(".overlay-buttons", obj.widget).html("");
            obj.bottom_bar_displayed = false;
            obj.on_resize();
        }
    }
};

OverlayDisplayer.prototype._focus_button = function () {
    // focus first button
    try {
        // this can crash on IE
        $(".overlay-bottom-bar button:first", this.widget).focus();
    }
    catch (e) { }
};

OverlayDisplayer.prototype._check_bars_display = function (resource) {
    this._check_title_display(resource.title);
    this._check_buttons_display(resource.buttons);
};

OverlayDisplayer.prototype._show_loading = function () {
    if (this.loading.displayed)
        return;
    
    this.loading.displayed = true;
    
    if (this.loading.timeout_id !== null) {
        clearTimeout(this.loading.timeout_id);
        this.loading.timeout_id = null;
    }
    
    var obj = this;
    this.loading.timeout_id = setTimeout(function () {
        $(".overlay-hover-loading", obj.widget).css("display", "block");
        $(".overlay-loading", obj.widget).css("display", "block");
    }, 500);
};

OverlayDisplayer.prototype._hide_loading = function () {
    if (!this.loading.displayed)
        return;
    
    this.loading.displayed = false;
    
    if (this.loading.timeout_id !== null) {
        clearTimeout(this.loading.timeout_id);
        this.loading.timeout_id = null;
    }
    
    $(".overlay-hover-loading", this.widget).css("display", "none");
    $(".overlay-loading", this.widget).css("display", "none");
};

//---------------------------
// Image management
//---------------------------
OverlayDisplayer.prototype._load_image = function (resource, callback) {
    if (this.display_mode != "image") {
        this.display_mode = "image";
        var html = "<img class=\"overlay-element\" src=\"\" style=\"max-width: "+this.max_width+"px; max-height: "+this.max_height+"px;\"/>";
        if (navigator.appVersion.indexOf("MSIE 6") != -1 || navigator.appVersion.indexOf("MSIE 7") != -1) {
            html = "<a href=\"javascript: return;\">"+html+"</a>";
            var dom = $(html).click({ obj: this }, function (event) { event.data.obj.hide(); });
            $(".overlay-element-content", this.widget).html("");
            $(".overlay-element-content", this.widget).append(dom);
        }
        else
            $(".overlay-element-content", this.widget).html(html);
    }
    else {
        if (this.image !== null && this.image.source == resource.url) {
            if (this.image.error)
                return callback(false);
            else
                return callback(true);
        }
    }
    
    if (this.resources === null || this.resources.length < 2) {
        // allow overlay hide by clicking on image
        $(".overlay-element", this.widget).click({ obj: this }, function (event) { event.data.obj.hide(); });
    }
    else {
        // disallow overlay hide by clicking on image
        $(".overlay-element", this.widget).unbind("click");
    }
    
    this.image = new Image();
    this.image.source = resource.url;
    this.image.src = resource.url;
    if (this.image.complete) {
        this.on_image_load(resource, callback);
    }
    else {
        var obj = this;
        this.image.onload = function () { obj.on_image_load(resource, callback); };
        this.image.onabort = function () { obj.on_image_load(resource, callback); };
        this.image.onerror = function () { obj.on_image_error(resource, callback); };
    }
};
OverlayDisplayer.prototype.on_image_load = function (resource, callback) {
    var obj = this;
    if (this.enable_transition_effects) {
        //$(".overlay-element-content", obj.widget).css("width", $(".overlay-element-content", obj.widget).width()+"px");
        //$(".overlay-element-content", obj.widget).css("height", $(".overlay-element-content", obj.widget).height()+"px");
        $(".overlay-element-mask", obj.widget).fadeIn("fast", function () {
            $(".overlay-element", obj.widget).attr("src", obj.image.source);
            $(".overlay-error", obj.widget).css("display", "none");
            obj._check_bars_display(resource);
            
            $(".overlay-element-mask", obj.widget).fadeOut("fast", function () {
                //$(".overlay-element-content").css("width", "auto");
                //$(".overlay-element-content").css("height", "auto");
                $(".overlay-element-mask", obj.widget).css("display", "none");
                callback(true);
            });
        });
    }
    else {
        $(".overlay-element", obj.widget).attr("src", obj.image.source);
        $(".overlay-error", obj.widget).css("display", "none");
        obj._check_bars_display(resource);
        
        callback(true);
    }
};
OverlayDisplayer.prototype.on_image_error = function (resource, callback) {
    $(".overlay-element-layer", this.widget).css("display", "none");
    $(".overlay-error", this.widget).css("display", "block");
    this._check_bars_display(resource);
    this.image.error = true;
    //this.display_mode = null;
    callback(false);
};

//---------------------------
// Iframe management
//---------------------------
OverlayDisplayer.prototype._load_iframe = function (resource, callback) {
    var width = this.max_width + "px";
    if (resource.width)
        width = resource.width;
    var height = this.max_height + "px";
    if (resource.height)
        height = resource.height;
    
    if (this.display_mode != "iframe") {
        this.display_mode = "iframe";
        var html = "<iframe class=\"overlay-element\" src=\""+resource.url+"\" style=\"width: "+width+"; height: "+height+"; margin: 0; padding: 0; border: 0 none; vertical-align: top;\"></iframe>";
        $(".overlay-element-content", this.widget).html(html);
    }
    else {
        $(".overlay-element", this.widget).css("width", width);
        $(".overlay-element", this.widget).css("height", height);
    }
    
    // no effects for iframes because we don't know when they are loaded 
    $(".overlay-element", this.widget).attr("src", resource.url);
    $(".overlay-error", this.widget).css("display", "none");
    this._check_bars_display(resource);
    
    callback(true);
};

//---------------------------
// HTML management
//---------------------------
OverlayDisplayer.prototype._load_html = function (resource, callback) {
    if (this.display_mode != "html") {
        this.display_mode = "html";
        var html = "<div class=\"overlay-element\" style=\"max-width: "+this.max_width+"px; max-height: "+this.max_height+"px;\"></div>";
        $(".overlay-element-content", this.widget).html(html);
    }
    
    var obj = this;
    if (this.enable_transition_effects) {
        $(".overlay-element-mask", obj.widget).fadeIn("fast", function () {
            if (resource.overflow)
                $(".overlay-element", obj.widget).css("overflow", resource.overflow);
            else
                $(".overlay-element", obj.widget).css("overflow", "");
            $(".overlay-element", obj.widget).html("");
            $(".overlay-element", obj.widget).append(resource.html);
            $(".overlay-error", obj.widget).css("display", "none");
            obj._check_bars_display(resource);
            
            $(".overlay-element-mask").fadeOut("fast", function () {
                $(".overlay-element-mask").css("display", "none");
                callback(true);
            });
        });
    }
    else {
        if (resource.overflow)
            $(".overlay-element", obj.widget).css("overflow", resource.overflow);
        else
            $(".overlay-element", obj.widget).css("overflow", "");
        $(".overlay-element", obj.widget).html("");
        $(".overlay-element", obj.widget).append(resource.html);
        $(".overlay-error", obj.widget).css("display", "none");
        obj._check_bars_display(resource);
        callback(true);
    }
};

//---------------------------
// Resources list functions
//---------------------------
OverlayDisplayer.prototype.go_to_index = function (index) {
    if (index >= this.resources.length || index < 0)
        return;
    
    $(".overlay-resources", this.widget).html((index + 1) + " / " + this.resources.length);
    if (index > 0)
        $(".overlay-previous", this.widget).css("display", "block");
    else
        $(".overlay-previous", this.widget).css("display", "none");
    if (index < this.resources.length - 1)
        $(".overlay-next", this.widget).css("display", "block");
    else
        $(".overlay-next", this.widget).css("display", "none");
    if (this.changing) {
        this.next_command = { fct: "go_to_index", params: index };
    }
    else {
        if (this.current_index != index) {
            this.changing = true;
            
            this._show_loading();
            
            this.current_index = index;
            var params = this.resources[this.current_index];
            var resource;
            if (typeof params == "string")
                resource = { mode: "image", url: params };
            else
                resource = params;
            
            var obj = this;
            this._load_resource(resource, function (success) {
                obj._hide_loading();
                obj.changing = false;
                obj._check_next_command();
            });
        }
    }
};
OverlayDisplayer.prototype.next = function () {
    if (this.next_command !== null && this.next_command.fct == "go_to_index") {
        index = this.next_command.params;
        if (this.resources !== null && this.resources.length > 0 && index + 1 < this.resources.length)
            this.go_to_index(index + 1);
    }
    else {
        if (this.resources !== null && this.resources.length > 0 && this.current_index + 1 < this.resources.length)
            this.go_to_index(this.current_index + 1);
    }
};
OverlayDisplayer.prototype.previous = function () {
    if (this.next_command !== null && this.next_command.fct == "go_to_index") {
        index = this.next_command.params;
        if (this.resources !== null && this.resources.length > 0 && index - 1 >= 0)
            this.go_to_index(index - 1);
    }
    else {
        if (this.resources !== null && this.resources.length > 0 && this.current_index - 1 >= 0)
            this.go_to_index(this.current_index - 1);
    }
};



OverlayDisplayer.prototype._set_resources = function (params) {
    this.resources = null;
    this.current_index = 0;
    
    var first_resource;
    if (typeof params == "string") {
        $(".overlay-resources", this.widget).css("display", "none");
        $(".overlay-previous", this.widget).css("display", "none");
        $(".overlay-next", this.widget).css("display", "none");
        first_resource = { mode: "image", url: params };
        this.resources = [first_resource];
    }
    else if (isinstance(params, "array")) {
        this.resources = params;
        this.current_index = 0;
        if (params.start_index && params.start_index > 0 && params.start_index < params.length)
            this.current_index = params.start_index;
        if (params.length > 1) {
            $(".overlay-resources", this.widget).html((this.current_index + 1) + " / " + params.length);
            $(".overlay-resources", this.widget).css("display", "block");
            if (this.current_index > 0)
                $(".overlay-previous", this.widget).css("display", "block");
            else
                $(".overlay-previous", this.widget).css("display", "none");
            if (this.current_index < params.length - 1)
                $(".overlay-next", this.widget).css("display", "block");
            else
                $(".overlay-next", this.widget).css("display", "none");
        }
        else {
            $(".overlay-resources", this.widget).css("display", "none");
            $(".overlay-previous", this.widget).css("display", "none");
            $(".overlay-next", this.widget).css("display", "none");
        }
        if (typeof params[this.current_index] == "string")
            first_resource = { mode: "image", url: params[this.current_index] };
        else
            first_resource = params[this.current_index];
    }
    else {
        $(".overlay-resources", this.widget).css("display", "none");
        $(".overlay-previous", this.widget).css("display", "none");
        $(".overlay-next", this.widget).css("display", "none");
        first_resource = params;
        this.resources = [first_resource];
    }
    return first_resource;
};

OverlayDisplayer.prototype._load_resource = function (resource, callback) {
    var obj = this;
    if (resource.mode == "image") {
        // image mode
        // resource must contain: url
        obj._load_image(resource, function (success) { obj.current_resource = resource; callback(success); });
    }
    else if (resource.mode == "iframe") {
        // iframe mode
        // resource must contain: url
        obj._load_iframe(resource, function (success) { obj.current_resource = resource; callback(success); });
    }
    else if (resource.mode == "html") {
        // html mode
        // resource must contain: html
        obj._load_html(resource, function (success) { obj.current_resource = resource; callback(success); });
    }
    else {
        this.current_resource = resource;
        callback(false);
    }
};

OverlayDisplayer.prototype.change = function (params) {
    if (this.changing) {
        this.next_command = { fct: "change", params: params };
    }
    else {
        if (!this.displayed)
            return;
        
        this.changing = true;
        
        var first_resource = this._set_resources(params);
        
        this._check_bars_display(first_resource);
        this._show_loading();
        
        var obj = this;
        if (this.display_mode != first_resource.mode) {
            if (obj.enable_effects) {
                $(".overlay-element-layer", obj.widget).fadeOut("fast", function () {
                    obj._execute_on_hide_callback();
                    obj._load_resource(first_resource, function (success) {
                        obj._hide_loading();
                        if (success)
                            $(".overlay-element-layer", obj.widget).fadeIn("fast");
                        obj.changing = false;
                        obj._check_next_command();
                    });
                });
            }
            else {
                $(".overlay-element-layer", obj.widget).css("display", "none");
                obj._execute_on_hide_callback();
                obj._load_resource(first_resource, function (success) {
                    obj._hide_loading();
                    if (success)
                        $(".overlay-element-layer", obj.widget).css("display", "block");
                    obj.changing = false;
                    obj._check_next_command();
                });
            }
        }
        else {
            obj._execute_on_hide_callback();
            obj._load_resource(first_resource, function (success) {
                obj._hide_loading();
                if (success && $(".overlay-element-layer", obj.widget).css("display") == "none") {
                    if (obj.enable_effects)
                        $(".overlay-element-layer", obj.widget).fadeIn("fast");
                    else
                        $(".overlay-element-layer", obj.widget).css("display", "block");
                }
                obj.changing = false;
                obj._check_next_command();
            });
        }
    }
};

OverlayDisplayer.prototype.show = function (params) {
    if (this.changing) {
        this.next_command = { fct: "show", params: params };
    }
    else {
        if (this.displayed) {
            if (params)
                this.change(params);
            return;
        }
        
        this.changing = true;
        
        var first_resource;
        if (params)
            first_resource = this._set_resources(params);
        else if (!this.resources || this.resources.length < 1)
            return;
        else
            first_resource = this.resources[0];
        
        this._check_bars_display(first_resource);
        this._show_loading();
        
        var obj = this;
        var element_layer_hidden = !this.displayed;
        if (this.display_mode != first_resource.mode) {
            $(".overlay-element-layer", obj.widget).css("display", "none");
            element_layer_hidden = true;
        }
        
        this._show(function () {
            obj._load_resource(first_resource, function (success) {
                obj._hide_loading();
                if (element_layer_hidden && success)
                    if (obj.enable_effects)
                        $(".overlay-element-layer", obj.widget).fadeIn("fast");
                    else
                        $(".overlay-element-layer", obj.widget).css("display", "block");
                // focus first button
                obj._focus_button();
                obj.changing = false;
                obj._check_next_command();
            });
        });
    }
};

OverlayDisplayer.prototype.hide = function () {
    if (!this.displayed)
        return;
    
    var obj = this;
    this._hide(function () {
        obj._execute_on_hide_callback();
    });
};

OverlayDisplayer.prototype._show = function (callback) {
    if (this.displayed) {
        if (callback)
            callback();
        return;
    }
    
    $(".overlay-error", this.widget).css("display", "none");
    
    if (this.no_fixed) {
        //alert("ios " + $(document).width() + " " + $(document).height() + " " + $(document).scrollTop());
        this.widget.css("width", $(document).width()+"px");
        this.widget.css("height", $(document).height()+"px");
        $(".overlay-table", this.widget).css("height", "auto");
        $(".overlay-block", this.widget).css("margin-top", ($(document).scrollTop()+10)+"px");
    }
    
    var obj = this;
    if (this.enable_effects) {
        obj.widget.fadeIn("fast", function () {
            obj.displayed = true;
            if (callback)
                callback();
        });
    }
    else {
        obj.widget.css("display", "block");
        obj.displayed = true;
        if (callback)
            callback();
    }
};
OverlayDisplayer.prototype._hide = function (callback) {
    if (!this.displayed)
        return callback();
    
    var obj = this;
    if (this.enable_effects) {
        obj.widget.fadeOut("fast", function () {
            $(".overlay-element-layer", obj.widget).css("display", "none");
            obj.displayed = false;
            callback();
        });
    }
    else {
        obj.widget.css("display", "none");
        $(".overlay-element-layer", obj.widget).css("display", "none");
        obj.displayed = false;
        callback();
    }
};

OverlayDisplayer.prototype._execute_on_hide_callback = function () {
    if (this.current_resource === null || !this.current_resource.on_hide)
        return;
    
    try {
        this.current_resource.on_hide();
    }
    catch (e) {
        //alert(e);
    }
};

