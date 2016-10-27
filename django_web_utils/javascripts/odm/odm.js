/**************************************************
* Overlay display manager                         *
* Author: Stephane Diemer                         *
* License: CC by SA v3                            *
* https://creativecommons.org/licenses/by-sa/3.0/ *
* Requires: jQuery                                *
**************************************************/

function OverlayDisplayManager(options) {
    // params
    this.language = "en";
    this.margin = 30;
    this.element_padding = 20;
    this.top_bar_height = 30;
    this.bottom_bar_height = 40;
    this.default_buttons_class = "";
    this.hide_on_escape = true;
    
    // vars
    this.pending_show_params = null;
    this.messages = {};
    this.$widget = null;
    this.max_width = 0;
    this.max_height = 0;
    this.image = null;
    this.displayed = false;
    this.element_padding_displayed = false;
    this.top_bar_displayed = false;
    this.bottom_bar_displayed = false;
    this.display_mode = null;
    this.title = "";
    this.resources = [];
    this.current_index = 0;
    this.current_resource = null;
    this.locked = false;
    this.no_fixed = false;
    
    if (window.utils && window.utils._current_lang)
        this.language = utils._current_lang;
    if (options) {
        for (var attr in options)
            this[attr] = options[attr];
    }
    this.set_language(this.language);
    var obj = this;
    $(document).ready(function () {
        obj._init();
    });
    $(window).resize(function () {
        obj.on_resize();
    });
    $(document).keydown(function (event) {
        if (!obj.displayed)
            return;
        switch (event.keyCode) {
            case 27:
                if (!obj.locked && obj.hide_on_escape)
                    obj.hide();
                break;
            case 37:
                obj.previous();
                break;
            case 39:
                obj.next();
                break;
        }
    });
}

OverlayDisplayManager.prototype._init = function () {
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
        if (!event.data.obj.locked)
            event.data.obj.hide();
    });
    $(".odm-closer", this.$widget).click({ obj: this }, function (event) {
        if (!event.data.obj.locked)
            event.data.obj.hide();
    });
    $(".odm-element-content", this.$widget).click({ obj: this }, function (event) {
        if (!event.data.obj.locked && event.data.obj.display_mode == "image" && event.data.obj.resources.length < 2 && event.data.obj.image && !event.data.obj.image.loading_failed)
            event.data.obj.hide();
    });
    this.on_resize();
    if (this.pending_show_params)
        this.show(this.pending_show_params);
};

OverlayDisplayManager.prototype.set_language = function (lang) {
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

OverlayDisplayManager.prototype.on_resize = function () {
    this.max_width = $(window).width() - this.margin;
    this.max_height = $(window).height() - this.margin;
    if (this.top_bar_displayed)
        this.max_height -= this.top_bar_height;
    if (this.bottom_bar_displayed)
        this.max_height -= this.bottom_bar_height;
    var padding = this.element_padding_displayed ? this.element_padding : 0;
    if (this.max_width > 0)
        $(".odm-element", this.$widget).css("max-width", (this.max_width-padding)+"px");
    if (this.max_height > 0)
        $(".odm-element", this.$widget).css("max-height", (this.max_height-padding)+"px");
};

OverlayDisplayManager.prototype._set_resources = function (params) {
    // reset content
    if (!this.displayed) {
        var html = $("<div class=\"odm-element odm-loading\">"+this.messages.loading+"</div>");
        this.loading_displayed = true;
        this._display_element(html);
        this.image = null;
        this.current_resource = null;
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

OverlayDisplayManager.prototype._add_resources = function (res) {
    if (typeof res == "string")
        this.resources.push({ image: res });
    else
        this.resources.push(res);
};

OverlayDisplayManager.prototype._check_title_display = function (title) {
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

OverlayDisplayManager.prototype._check_buttons_display = function (resource) {
    var btns = resource.buttons;
    if (btns) {
        // update buttons
        if (!btns.loaded) {
            $(".odm-buttons", this.$widget).html("");
            for (var i=0; i < btns.length; i++) {
                var btn = $("<button class=\""+this.default_buttons_class+"\"/>");
                btn.html(btns[i].label);
                if (btns[i].id)
                    btn.attr("id", btns[i].id);
                if (btns[i].disabled)
                    btn.attr("disabled", "disabled");
                if (btns[i].klass)
                    btn.attr("class", this.default_buttons_class+" "+btns[i].klass);
                if (btns[i].callback) {
                    var data = btns[i].data ? btns[i].data : {};
                    data.odm = this;
                    btn.click(data, btns[i].callback);
                }
                if (btns[i].close)
                    btn.click({ odm: this }, function (event) { event.data.odm.hide(); });
                $(".odm-buttons", this.$widget).append(btn);
            }
            btns.loaded = true;
        }
        // show bottom bar
        if (!this.bottom_bar_displayed) {
            this.$widget.addClass("odm-bottom-bar-displayed");
            this.bottom_bar_displayed = true;
            this.on_resize();
        }
        // focus first button
        if (this.displayed && !resource.no_button_focus)
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

OverlayDisplayManager.prototype._focus_button = function () {
    if ($(".odm-bottom-bar button", this.$widget).length < 1)
        return;
    // focus first button (this can crash on IE)
    try { $(".odm-bottom-bar button:first", this.$widget).focus(); }
    catch (e) { }
};

OverlayDisplayManager.prototype._set_locked = function (locked) {
    if (this.locked == locked)
        return;

    this.locked = locked;
    if (this.locked)
        $(".odm-close", this.$widget).css("display", "none");
    else
        $(".odm-close", this.$widget).css("display", "");
};


OverlayDisplayManager.prototype._on_resource_hide = function () {
    if (this.current_resource && this.current_resource.on_hide) {
        this.current_resource.on_hide();
        // Don't call on_hide twice
        delete this.current_resource.on_hide;
    }
};
OverlayDisplayManager.prototype._load_resource = function (resource) {
    this._show_loading();
    this._on_resource_hide();

    this._check_title_display(resource.title ? resource.title : "");
    this._check_buttons_display(resource);
    this._set_locked(resource.locked ? true : false);
    
    var obj = this;
    var callback = function (success) {
        obj._hide_loading();
    };
    this.current_resource = resource;
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

// Main functions
OverlayDisplayManager.prototype.change = function (params) {
    if (!this.$widget || !params)
        return;
    
    var resource = this._set_resources(params);
    if (this.displayed)
        this._load_resource(resource);
};
OverlayDisplayManager.prototype.show = function (params) {
    if (!this.$widget) {
        this.pending_show_params = params;
        return;
    }
    this.pending_show_params = null;
    if (this.displayed)
        return this.change(params);
    
    var resource;
    if (params)
        resource = this._set_resources(params);
    else if (this.resources.length < 1)
        return;
    else if (!this.current_resource)
        resource = this.resources[this.current_index];
    if (resource)
        this._load_resource(resource);
    if (this.no_fixed)
        $(".odm-table", this.$widget).css("margin-top", ($(document).scrollTop()+10)+"px");
    this.displayed = true;
    var obj = this;
    this.$widget.addClass("odm-no-transition").stop(true, false).fadeIn(250, function () {
        $(this).removeClass("odm-no-transition");
        if (obj.current_resource && !obj.current_resource.no_button_focus)
            obj._focus_button();
    });
};
OverlayDisplayManager.prototype.hide = function () {
    if (this.pending_show_params)
        this.pending_show_params = null;
    if (!this.displayed)
        return;
    
    this.displayed = false;
    var obj = this;
    this.$widget.addClass("odm-no-transition").stop(true, false).fadeOut(250, function () {
        $(this).removeClass("odm-no-transition");
        obj._on_resource_hide();
    });
};

// Resources list functions
OverlayDisplayManager.prototype.go_to_index = function (index) {
    if (index >= this.resources.length || index < 0)
        return;
    
    $(".odm-resources", this.$widget).html((index+1)+" / "+this.resources.length);
    if (index > 0)
        $(".odm-previous", this.$widget).css("display", "block");
    else
        $(".odm-previous", this.$widget).css("display", "");
    if (index < this.resources.length - 1)
        $(".odm-next", this.$widget).css("display", "block");
    else
        $(".odm-next", this.$widget).css("display", "");
    if (this.current_index != index) {
        this.current_index = index;
        this._load_resource(this.resources[this.current_index]);
    }
};
OverlayDisplayManager.prototype.next = function () {
    if (this.resources.length > 0 && this.current_index + 1 < this.resources.length)
        this.go_to_index(this.current_index + 1);
};
OverlayDisplayManager.prototype.previous = function () {
    if (this.resources.length > 0 && this.current_index - 1 >= 0)
        this.go_to_index(this.current_index - 1);
};

// Element display
OverlayDisplayManager.prototype._display_element = function ($element, padding) {
    this.element_padding_displayed = padding;
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
OverlayDisplayManager.prototype._display_error = function (msg) {
    var html = $("<div class=\"odm-element odm-error\">"+((msg in this.messages) ? this.messages[msg] : msg)+"</div>");
    this._display_element(html);
};
OverlayDisplayManager.prototype._show_loading = function () {
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
OverlayDisplayManager.prototype._hide_loading = function () {
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
OverlayDisplayManager.prototype._load_image = function (resource, callback) {
    if (this.display_mode != "image")
        this.display_mode = "image";
    else if (this.image && this.image.ori_src == resource.image) {
        callback(this.image.loading_failed ? false : true);
        return;
    }
    
    this.image = new Image();
    this.image.odm = this;
    this.image.odm_callback = callback;
    this.image.onload = function () {
        var $img = $("<img class=\"odm-element\" src=\""+this.src+"\" style=\"max-width: "+this.odm.max_width+"px; max-height: "+this.odm.max_height+"px;\"/>");
        this.odm._display_element($img);
        this.odm_callback(true);
    };
    this.image.onabort = this.image.onload;
    this.image.onerror = function () {
        this.loading_failed = true;
        this.odm._display_error("not_found");
        this.odm_callback(false);
    };
    this.image.ori_src = resource.image;
    this.image.src = resource.image;
};

// Iframe management
OverlayDisplayManager.prototype._load_iframe = function (resource, callback) {
    if (this.display_mode != "iframe")
        this.display_mode = "iframe";
    var width = resource.width ? resource.width : this.max_width+"px";
    var height = resource.height ? resource.height : this.max_height+"px";
    var $iframe = $("<iframe class=\"odm-element\" src=\""+resource.iframe+"\" style=\"width: "+width+"; height: "+height+";\"></iframe>");
    this._display_element($iframe);
    callback(true);
};

// HTML management
OverlayDisplayManager.prototype._load_html = function (resource, callback) {
    if (this.display_mode != "html")
        this.display_mode = "html";
    var $html = (typeof resource.html == "string") ? $("<div>"+resource.html+"</div>") : resource.html.detach();
    $html.addClass("odm-element").css("max-width", (this.max_width-this.element_padding)+"px").css("max-height", (this.max_height-this.element_padding)+"px").css("opacity", "").css("position", "");
    this._display_element($html, true);
    callback(true);
};

