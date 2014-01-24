/*******************************************
* Utilities functions                      *
* Copyright: UbiCast, all rights reserved  *
* Author: Stephane Diemer                  *
*******************************************/

// add console log function for old browsers
if (!window.console)
    window.console = {};
if (!window.console.log)
    window.console.log = function () {
        //for (var i=0; i < arguments.length; i++) {
        //    $("body").append("<p>Argument-" + i + ": " + arguments[i] + "</p>");
        //}
    };


var utils = {};

// cookies
utils.get_cookie = function (c_name, c_default) {
    if (document.cookie.length > 0) {
        var c_start = document.cookie.indexOf(c_name + "=");
        if (c_start != -1) {
            c_start = c_start + c_name.length+1;
            var c_end = document.cookie.indexOf(";", c_start);
            if (c_end == -1) c_end = document.cookie.length;
            return unescape(document.cookie.substring(c_start, c_end));
        }
    }
    if (c_default !== undefined)
        return c_default;
    return "";
};
utils.set_cookie = function (c_name, value, expiredays) {
    var exdate = new Date();
    if (expiredays)
        exdate.setDate(exdate.getDate() + expiredays);
    else
        exdate.setDate(exdate.getDate() + 360);
    document.cookie = c_name+"="+escape(value)+"; expires="+exdate.toUTCString()+"; path=/";
};

// strip function
utils.strip = function (str, character) {
    var c = character;
    if (c === undefined)
        c = " ";
    if (!str)
        return str;
    var start = 0;
    while (start < str.length && str[start] == c) {
        start++;
    }
    var end = str.length - 1;
    while (end >= 0 && str[end] == c) {
        end--;
    }
    var result = str.substring(start, end+1);
    return result;
};

// isinstance
utils.isinstance = function (obj, type) {
    if (typeof obj == "object") {
        var matching = obj.constructor.toString().match(new RegExp(type, "i"));
        return (matching !== null);
    }
    return false;
};

// escape html
utils.escape_html = function (text) {
    if (!text)
        return text;
    var result = text.toString();
    result = result.replace(new RegExp("(\n)", "g"), "<br/>");
    result = result.replace(new RegExp("(<)", "g"), "&lt;");
    result = result.replace(new RegExp("(>)", "g"), "&gt;");
    result = result.replace(new RegExp("(\")", "g"), "&quot;");
    return result;
};

// escape attribute
utils.escape_attr = function (attr) {
    if (!attr)
        return attr;
    var result = attr.toString();
    result = result.replace(new RegExp("(\n)", "g"), " ");
    result = result.replace(new RegExp("(\")", "g"), "&quot;");
    return result;
};

// get click relative coordinates
utils.get_click_position = function (evt, dom) {
    var element = dom, x_offset = 0, y_offset = 0;
    // get canvas offset
    while (element !== null && element !== undefined) {
        x_offset += element.offsetLeft;
        y_offset += element.offsetTop;
        element = element.offsetParent;
    }
    return { x: evt.pageX - x_offset, y: evt.pageY - y_offset };
};

// user agent and platform related functions
utils.get_user_agent = function () {
    if (utils._user_agent)
        return utils._user_agent;
    if (window.navigator && window.navigator.userAgent)
        utils._user_agent = window.navigator.userAgent.toLowerCase();
    else
        utils._user_agent = "unknown";
    return utils._user_agent;
};
utils.get_os_name = function () {
    if (utils._os_name)
        return utils._os_name;
    if (window.navigator && window.navigator.platform) {
        var platform = window.navigator.platform.toLowerCase();
        if (platform.indexOf("ipad") != -1 || platform.indexOf("iphone") != -1 || platform.indexOf("ipod") != -1)
            utils._os_name = "ios";
    }
    if (!utils._os_name && window.navigator && window.navigator.appVersion) {
        var app_version = window.navigator.appVersion.toLowerCase();
        if (app_version.indexOf("win") != -1)
            utils._os_name = "windows";
        else if (app_version.indexOf("mac") != -1)
            utils._os_name = "macos";
        else if (app_version.indexOf("x11") != -1 || app_version.indexOf("linux") != -1)
            utils._os_name = "linux";
    }
    if (!utils._os_name)
        utils._os_name = "unknown";
    return utils._os_name;
};
utils.is_in_user_agent = function () {
    var ua = utils.get_user_agent();
    if (arguments.length == 1 && typeof arguments[0] == "string")
        return ua.indexOf(arguments[0]) != -1;
    for (var i=0; i < arguments.length; i++) {
        if (ua.indexOf(arguments[i]) != -1)
            return true;
    }
    return false;
};
utils.is_phone = function () {
    if (utils._is_phone !== undefined)
        return utils._is_phone;
    utils._is_phone = utils.is_in_user_agent("android", "ipad", "iphone", "opera mobi", "opera mini", "fennec", "symbianos", "bolt", "sonyericsson") && !utils.is_tablet();
    return utils._is_phone;
};
utils.is_tablet = function () {
    if (utils._is_tablet !== undefined)
        return utils._is_tablet;
    utils._is_tablet = window.navigator && window.navigator.platform == "iPad";
    return utils._is_tablet;
};
utils.is_tactile = function () {
    if (utils._is_tactile !== undefined)
        return utils._is_tactile;
    utils._is_tactile = utils.is_phone() || utils.is_tablet();
    return utils._is_tactile;
};

// Translations utils
utils._translations = { en: {} };
utils._current_lang = "en";
utils._current_catalog = utils._translations["en"];
utils.use_lang = function (lang) {
    utils._current_lang = lang;
    if (!utils._translations[lang])
        utils._translations[lang] = {};
    utils._current_catalog = utils._translations[lang];
};
utils.add_translations = function (translations, lang) {
    var catalog;
    if (lang) {
        if (!utils._translations[lang])
            utils._translations[lang] = {};
        catalog = utils._translations[lang];
    }
    else
        catalog = utils._current_catalog;
    for (var text in translations) {
        if (translations.hasOwnProperty(text))
            catalog[text] = translations[text];
    }
};
utils.translate = function (text) {
    if (text in utils._current_catalog)
        return utils._current_catalog[text];
    else if (utils._current_lang != "en" && text in utils._translations["en"])
        return utils._translations["en"][text];
    return text;
};
utils.get_date_display = function (d) {
    // date format %Y-%m-%d %H:%M:%S
    var date_split = d.split(" ");
    if (date_split.length < 2)
        return "";
    var ymd_split = date_split[0].split("-");
    var hms_split = date_split[1].split(":");
    if (ymd_split.length < 3 || hms_split.length < 3)
        return "";
    // year
    var year = ymd_split[0];
    // month
    var month = ymd_split[1];
    switch (ymd_split[1]) {
        case "01": month = utils.translate("January");   break;
        case "02": month = utils.translate("February");  break;
        case "03": month = utils.translate("March");     break;
        case "04": month = utils.translate("April");     break;
        case "05": month = utils.translate("May");       break;
        case "06": month = utils.translate("June");      break;
        case "07": month = utils.translate("July");      break;
        case "08": month = utils.translate("August");    break;
        case "09": month = utils.translate("September"); break;
        case "10": month = utils.translate("October");   break;
        case "11": month = utils.translate("November");  break;
        case "12": month = utils.translate("December");  break;
    }
    // day
    var day = ymd_split[2];
    try { day = parseInt(ymd_split[2], 10); } catch (e) { }
    // hour
    var hour = parseInt(hms_split[0], 10);
    // minute
    var minute = parseInt(hms_split[1], 10);
    if (minute < 10)
        minute = "0"+minute;
    // time
    var time;
    if (utils._current_lang == "fr") {
        // 24 hours time format
        if (hour < 10)
            hour = "0"+hour;
        time = hour+"h"+minute;
    }
    else {
        // 12 hours time format
        var moment = "PM";
        if (hour < 13) {
            moment = "AM";
            if (hour == 0)
                hour = 12;
        }
        else
            hour -= 12;
        time = hour+":"+minute+" "+moment;
    }
    return day+" "+month+" "+year+" "+utils.translate("at")+" "+time;
};


// JavaScript classes related functions
utils.setup_class = function (obj, options, allowed_options) {
    // listeners
    if (!obj._listeners)
        obj._listeners = {};
    if (!obj.constructor.prototype.add_listener)
        obj.constructor.prototype.add_listener = function (evtname, arg1, arg2, arg3) {
            // arguments: evtname, [receiver], [params], fct
            var listener = {};
            if (arg3 !== undefined) {
                listener.receiver = arg1;
                listener.params = arg2;
                listener.fct = arg3;
            }
            else if (arg2 !== undefined) {
                listener.receiver = arg1;
                listener.fct = arg2;
            }
            else if (arg1 !== undefined) {
                listener.fct = arg1;
            }
            else {
                throw("Invalid listener for event "+evtname+" (no function given to add_listener function).");
            }
            if (!this._listeners[evtname])
                this._listeners[evtname] = [listener];
            else
                this._listeners[evtname].push(listener);
        };
    if (!obj.constructor.prototype.call_listeners)
        obj.constructor.prototype.call_listeners = function (evtname, data) {
            if (!this._listeners[evtname])
                return;
            for (var i=0; i < this._listeners[evtname].length; i++) {
                var listener = this._listeners[evtname][i];
                try {
                    if (listener.receiver)
                        listener.fct(listener.receiver, data, listener.params);
                    else
                        listener.fct(data, listener.params);
                }
                catch (e) {
                    console.log("Error when calling listener for event "+evtname+" of object "+this.constructor.name+".\n    Error: "+e+"\n    Receiver: "+listener.receiver+"\n    Receiving function is: "+listener.fct.toString());
                }
            }
        };
    // translations
    if (!obj.constructor.prototype.add_translations)
        obj.constructor.prototype.add_translations = function (translations) {
            utils.add_translations(translations);
        };
    if (!obj.constructor.prototype.translate)
        obj.constructor.prototype.translate = function (text) {
            return utils.translate(text);
        };
    // options
    if (allowed_options)
        obj.allowed_options = allowed_options;
    if (!obj.constructor.prototype.set_options)
        obj.constructor.prototype.set_options = function (options) {
            if (options.translations) {
                this.add_translations(options.translations);
                delete options.translations;
            }
            if (this.allowed_options) {
                for (var i=0; i < this.allowed_options.length; i++) {
                    if (this.allowed_options[i] in options)
                        this[this.allowed_options[i]] = options[this.allowed_options[i]];
                }
            }
            else {
                for (var param in options) {
                    if (options.hasOwnProperty(param))
                        this[param] = options[param];
                }
            }
        };
    if (options)
        obj.set_options(options);
};

