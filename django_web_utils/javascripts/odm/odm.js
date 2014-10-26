/**************************************************
* Overlay displayer manager                       *
* Author: Stephane Diemer                         *
* License: CC by SA v3                            *
* https://creativecommons.org/licenses/by-sa/3.0/ *
* Requires: jQuery                                *
**************************************************/

function OverlayDisplayerManager(options) {
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
    this.messages = {};
    this.$widget = null;
    this.max_width = 0;
    this.max_height = 0;
    this.image = null;
    this.displayed = false;
    this.top_bar_displayed = false;
    this.bottom_bar_displayed = false;
    this.display_mode = null;
    this.title = "";
    this.resources = [];
    this.current_index = 0;
    this.current_resource = null;
    this.no_fixed = false;
    
    if (options) {
        for (var attr in options)
            this[attr] = options[attr];
    }
    this.set_language(this.language);
    var obj = this;
    $(document).ready(function (event) {
        obj._init();
    });
    $(window).resize(function (event) {
        obj.on_resize();
    });
    $(window).keypress(function (event) {
        if (obj.hide_on_escape && event.keyCode == 27)
            obj.hide();
    });
}

OverlayDisplayerManager.prototype._init = function () {
    var extra_class = "";
    if (navigator.platform == "iPad" || navigator.platform == "iPhone" || navigator.platform == "iPod") {
        this.no_fixed = true;
        extra_class = "no-fixed";
    }
    var html = "";
    html += "<div class=\"odm-main "+extra_class+"\">";
    html +=     "<div class=\"odm-layer\">";
    html +=         "<table class=\"odm-table\"><tr class=\"odm-table\"><td class=\"odm-table\">";
    html +=             "<div class=\"odm-block\">";
    html +=                 "<div class=\"odm-top-bar\">";
    html +=                     "<div class=\"odm-resources\"></div>";
    html +=                     "<div class=\"odm-title\"></div>";
    html +=                 "</div>";
    html +=                 "<div class=\"odm-element-place\">";
    html +=                     "<div class=\"odm-element-content\">";
    html +=                         "<div class=\"odm-element odm-loading\">"+this.messages.loading+"</div>";
    html +=                     "</div>";
    html +=                     "<div class=\"odm-hover-loading\"><div>"+this.messages.loading+"</div></div>";
    html +=                 "</div>";
    html +=                 "<div class=\"odm-bottom-bar\">";
    html +=                     "<div class=\"odm-buttons\"></div>";
    html +=                 "</div>";
    html +=                 "<div class=\"odm-previous\"><div class=\"odm-btn-bg\">";
    html +=                     "<div class=\"odm-btn-icon\">"+this.messages.previous+"</div></div></div>";
    html +=                 "<div class=\"odm-next\"><div class=\"odm-btn-bg\">";
    html +=                     "<div class=\"odm-btn-icon\">"+this.messages.next+"</div></div></div>";
    html +=                 "<div class=\"odm-close\"><div></div></div>";
    html +=             "</div>";
    html +=         "</td></tr></table>";
    html +=     "</div>";
    html +=     "<div class=\"odm-closer\"></div>";
    html += "</div>";
    this.$widget = $(html);
    $("body").append(this.$widget);
    
    // bind events
    $(".odm-previous", this.$widget).click({ obj: this }, function (event) {
        event.data.obj.previous();
    });
    $(".odm-next", this.$widget).click({ obj: this }, function (event) {
        event.data.obj.next();
    });
    $(".odm-close", this.$widget).click({ obj: this }, function (event) {
        event.data.obj.hide();
    });
    $(".odm-closer", this.$widget).click({ obj: this }, function (event) {
        event.data.obj.hide();
    });
    $(".odm-element-content", this.$widget).click({ obj: this }, function (event) {
        if (event.data.obj.display_mode == "image" && event.data.obj.resources.length < 2)
            event.data.obj.hide();
    });
    this.on_resize();
};

OverlayDisplayerManager.prototype.set_language = function (lang) {
    if (lang == "fr") {
        this.language = "fr";
        this.messages = {
            loading: "Chargement...",
            not_found: "Image introuvable",
            unknown_resource: "Type de ressource inconnu",
            previous: "Pr&eacute;c&eacute;dent",
            next: "Suivant"
        };
    }
    else {
        this.language = "en";
        this.messages = {
            loading: "Loading...",
            not_found: "Image not found",
            unknown_resource: "Unknown resource type",
            previous: "Previous",
            next: "Next"
        };
    }
    if (this.$widget) {
        // replace messages
        $(".odm-loading", this.$widget).html(this.messages.loading);
        $(".odm-hover-loading", this.$widget).html(this.messages.loading);
        $(".odm-previous .odm-btn-icon", this.$widget).html(this.messages.previous);
        $(".odm-next .odm-btn-icon", this.$widget).html(this.messages.next);
    }
};

OverlayDisplayerManager.prototype.on_resize = function () {
    this.max_width = $(window).width() - this.margin;
    this.max_height = $(window).height() - this.margin;
    if (this.top_bar_displayed)
        this.max_height -= this.top_bar_height;
    if (this.bottom_bar_displayed)
        this.max_height -= this.bottom_bar_height;
    if (this.max_width > 0)
        $(".odm-element", this.$widget).css("max-width", this.max_width+"px");
    if (this.max_height > 0)
        $(".odm-element", this.$widget).css("max-height", this.max_height+"px");
};

OverlayDisplayerManager.prototype._set_resources = function (params) {
    // reset content
    if (!this.displayed && this.resources.length > 1) {
        var html = $("<div class=\"odm-element odm-loading\">"+this.messages.loading+"</div>");
        this._display_element(html);
        this.image = null;
    }
    // parse resources
    this.resources = [];
    if (typeof params != "string" && params.length !== undefined) {
        for (var i=0; i < params.length; i++) {
            this._add_resources(params[i]);
        }
    }
    else
        this._add_resources(params);
    // display require elements
    this.current_index = 0;
    if (this.resources.length < 1)
        return;
    if (this.resources.length > 1) {
        if (params.index && params.index > 0 && params.index < params.length)
            this.current_index = params.index;
        $(".odm-resources", this.$widget).html((this.current_index+1)+" / "+this.resources.length);
        if (!this.top_bar_displayed) {
            this.top_bar_displayed = true;
            this.$widget.addClass("odm-top-bar-displayed");
            this.on_resize();
        }
        if (this.current_index > 0)
            $(".odm-previous", this.$widget).css("display", "block");
        else
            $(".odm-previous", this.$widget).css("display", "none");
        if (this.current_index < this.resources.length - 1)
            $(".odm-next", this.$widget).css("display", "block");
        else
            $(".odm-next", this.$widget).css("display", "none");
    }
    else {
        if (this.top_bar_displayed && !this.title) {
            this.top_bar_displayed = false;
            this.$widget.removeClass("odm-top-bar-displayed");
            this.on_resize();
        }
        $(".odm-resources", this.$widget).html("");
        $(".odm-previous", this.$widget).css("display", "none");
        $(".odm-next", this.$widget).css("display", "none");
    }
    return this.resources[this.current_index];
};

OverlayDisplayerManager.prototype._add_resources = function (res) {
    if (typeof res == "string")
        this.resources.push({ image: res });
    else
        this.resources.push(res);
};

OverlayDisplayerManager.prototype._check_title_display = function (title) {
    if (this.title == title)
        return;
    
    $(".odm-title", this.$widget).html(title);
    this.title = title;
    var should_display = title || this.resources.length > 1;
    if (should_display && !this.top_bar_displayed) {
        this.top_bar_displayed = true;
        this.$widget.addClass("odm-top-bar-displayed");
        this.on_resize();
    }
    else if (!should_display && this.top_bar_displayed) {
        this.top_bar_displayed = false;
        this.$widget.removeClass("odm-top-bar-displayed");
        this.on_resize();
    }
};

OverlayDisplayerManager.prototype._check_buttons_display = function (buttons) {
    if (buttons) {
        // update buttons
        if (!buttons.loaded) {
            $(".odm-buttons", this.$widget).html("");
            for (var i=0; i < buttons.length; i++) {
                var btn = $("<button class=\""+this.default_buttons_class+"\"/>");
                if (buttons[i].id)
                    btn.attr("id", buttons[i].id);
                if (buttons[i].disabled)
                    btn.attr("disabled", "disabled");
                if (buttons[i].klass)
                    btn.attr("class", this.default_buttons_class+" "+buttons[i].klass);
                btn.html(buttons[i].label);
                if (buttons[i].callback)
                    btn.click(buttons[i].callback);
                $(".odm-buttons", this.$widget).append(btn);
            }
            buttons.loaded = true;
        }
        // show bottom bar
        if (!this.bottom_bar_displayed) {
            this.$widget.addClass("odm-bottom-bar-displayed");
            this.bottom_bar_displayed = true;
            this.on_resize();
        }
        // focus first button
        this._focus_button();
    }
    else if (this.bottom_bar_displayed) {
        // hide bottom bar and clear buttons
        this.$widget.removeClass("odm-bottom-bar-displayed");
        this.bottom_bar_displayed = false;
        $(".odm-buttons", this.$widget).html("");
        this.on_resize();
    }
};

OverlayDisplayerManager.prototype._focus_button = function () {
    // focus first button (this can crash on IE)
    try { $(".odm-bottom-bar button:first", this.$widget).focus(); }
    catch (e) { }
};


//---------------------------
// Resources list functions
//---------------------------
OverlayDisplayerManager.prototype.go_to_index = function (index) {
    if (index >= this.resources.length || index < 0)
        return;
    
    $(".odm-resources", this.$widget).html((index+1)+" / "+this.resources.length);
    if (index > 0)
        $(".odm-previous", this.$widget).css("display", "block");
    else
        $(".odm-previous", this.$widget).css("display", "none");
    if (index < this.resources.length - 1)
        $(".odm-next", this.$widget).css("display", "block");
    else
        $(".odm-next", this.$widget).css("display", "none");
    if (this.current_index != index) {
        this.current_index = index;
        this._load_resource(this.resources[this.current_index]);
    }
};
OverlayDisplayerManager.prototype.next = function () {
    if (this.resources.length > 0 && this.current_index + 1 < this.resources.length)
        this.go_to_index(this.current_index + 1);
};
OverlayDisplayerManager.prototype.previous = function () {
    if (this.resources.length > 0 && this.current_index - 1 >= 0)
        this.go_to_index(this.current_index - 1);
};


OverlayDisplayerManager.prototype._load_resource = function (resource) {
    this._show_loading();
    this._check_title_display(resource.title ? resource.title : "");
    this._check_buttons_display(resource.buttons);
    
    var obj = this;
    var callback = function (success) {
        obj.current_resource = resource;
        obj._hide_loading();
    };
    if (resource.image)
        // image mode
        this._load_image(resource, callback);
    else if (resource.iframe)
        // iframe mode
        this._load_iframe(resource, callback);
    else if (resource.html)
        // html mode
        this._load_html(resource, callback);
    else {
        this._display_error("unknown_resource");
        callback(false);
    }
};

OverlayDisplayerManager.prototype.change = function (params) {
    if (!this.$widget || !params)
        return;
    
    var resource = this._set_resources(params);
    if (this.displayed) {
        this._execute_on_hide_callback();
        this._load_resource(resource);
    }
};

OverlayDisplayerManager.prototype.show = function (params) {
    if (!this.$widget)
        return;
    if (this.displayed)
        return this.change(params);
    
    var resource;
    if (params)
        resource = this._set_resources(params);
    else if (this.resources.length < 1)
        return;
    
    if (resource) {
        // Change resource
        this._load_resource(resource);
        // focus first button
        this._focus_button();
    }
    if (this.no_fixed)
        $(".odm-table", this.$widget).css("margin-top", ($(document).scrollTop()+10)+"px");
    var obj = this;
    this.$widget.stop(true, false).fadeIn(250, function () {
        obj.displayed = true;
    });
};

OverlayDisplayerManager.prototype.hide = function () {
    if (!this.displayed)
        return;
    
    var obj = this;
    this.$widget.stop(true, false).fadeOut(250, function () {
        obj.displayed = false;
        obj._execute_on_hide_callback();
    });
};

OverlayDisplayerManager.prototype._execute_on_hide_callback = function () {
    if (!this.current_resource || !this.current_resource.on_hide)
        return;
    
    try {
        this.current_resource.on_hide();
    }
    catch (e) {
        if (window.console)
            window.console.log("Callback execution failed: "+e);
    }
};
OverlayDisplayerManager.prototype._display_element = function ($element) {
    var $previous = $(".odm-element-content .odm-element", this.$widget);
    $(".odm-element-content", this.$widget).append($element);
    if ($previous.length < 1)
        return;
    if ($previous.hasClass("odm-loading") || $previous.hasClass("odm-error")) {
        $previous.remove();
    }
    else if ($element.hasClass("odm-loading") || $element.hasClass("odm-error")) {
        $previous.detach();
    }
    else {
        $previous.css("opacity", "0").css("position", "absolute");
        setTimeout(function () {
            $previous.detach();
        }, 500);
    }
};

// Error and loading management
//---------------------------
OverlayDisplayerManager.prototype._display_error = function (msg) {
    var html = $("<div class=\"odm-element odm-error\">"+((msg in this.messages) ? this.messages[msg] : msg)+"</div>");
    this._display_element(html);
};
OverlayDisplayerManager.prototype._show_loading = function () {
    if (this.loading_displayed)
        return;
    this.loading_displayed = true;
    if (this.loading_timeout_id !== null) {
        clearTimeout(this.loading_timeout_id);
        this.loading_timeout_id = null;
    }
    var obj = this;
    this.loading_timeout_id = setTimeout(function () {
        obj.$widget.addClass("odm-hover-loading-displayed");
    }, 500);
};
OverlayDisplayerManager.prototype._hide_loading = function () {
    if (!this.loading_displayed)
        return;
    this.loading_displayed = false;
    if (this.loading_timeout_id !== null) {
        clearTimeout(this.loading_timeout_id);
        this.loading_timeout_id = null;
    }
    this.$widget.removeClass("odm-hover-loading-displayed");
};

// Image management
//---------------------------
OverlayDisplayerManager.prototype._load_image = function (resource, callback) {
    if (this.display_mode != "image")
        this.display_mode = "image";
    else if (this.image && this.image.ori_src == resource.image) {
        callback(this.image.loading_failed ? false : true);
        return;
    }
    
    this.image = new Image();
    this.image.ori_src = resource.image;
    this.image.src = resource.image;
    if (this.image.complete) {
        this._on_image_load(this.image, resource, callback);
    }
    else {
        var obj = this;
        this.image.onload = function () { obj._on_image_load(this, resource, callback); };
        this.image.onabort = function () { obj._on_image_load(this, resource, callback); };
        this.image.onerror = function () { obj._on_image_error(this, resource, callback); };
    }
};
OverlayDisplayerManager.prototype._on_image_load = function (img, resource, callback) {
    var $img = $("<img class=\"odm-element\" src=\""+img.src+"\" style=\"max-width: "+this.max_width+"px; max-height: "+this.max_height+"px;\"/>");
    this._display_element($img);
    callback(true);
};
OverlayDisplayerManager.prototype._on_image_error = function (img, resource, callback) {
    img.loading_failed = true;
    this._display_error("not_found");
    callback(false);
};

// Iframe management
//---------------------------
OverlayDisplayerManager.prototype._load_iframe = function (resource, callback) {
    if (this.display_mode != "iframe")
        this.display_mode = "iframe";
    var width = resource.width ? resource.width : this.max_width+"px";
    var height = resource.height ? resource.height : this.max_height+"px";
    var $iframe = $("<iframe class=\"odm-element\" src=\""+resource.iframe+"\" style=\"width: "+width+"; height: "+height+";\"></iframe>");
    this._display_element($iframe);
    callback(true);
};

// HTML management
//---------------------------
OverlayDisplayerManager.prototype._load_html = function (resource, callback) {
    if (this.display_mode != "html")
        this.display_mode = "html";
    var width = resource.width ? resource.width : "auto";
    var height = resource.height ? resource.height : "auto";
    var overflow = resource.overflow ? resource.overflow : "";
    var $html = $("<div class=\"odm-element\" style=\"max-width: "+this.max_width+"px; max-height: "+this.max_height+"px; width: "+width+"; height: "+height+"; overflow: "+overflow+";\"></div>");
    $html.append(resource.html);
    this._display_element($html);
    callback(true);
};

