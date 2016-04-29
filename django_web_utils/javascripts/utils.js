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
            if (c_end == -1)
                c_end = document.cookie.length;
            return unescape(document.cookie.substring(c_start, c_end));
        }
    }
    return c_default !== undefined ? c_default : "";
};
utils.set_cookie = function (c_name, value, expiredays) {
    var exdate = new Date();
    exdate.setDate(exdate.getDate() + (expiredays ? expiredays : 360));
    document.cookie = c_name+"="+escape(value)+"; expires="+exdate.toUTCString()+"; path=/";
};

// strip function
utils.strip = function (str, character) {
    if (!str)
        return str;
    var c = character !== undefined ? character : " ";
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

// add indexOf method to Array (for IE8)
if (!Array.prototype.indexOf) {
    Array.prototype.indexOf = function(searchElement, fromIndex) {
        if (this == null)
            throw new TypeError("\"this\" is undefined or null.");
        var O = Object(this);
        var len = O.length >>> 0;
        if (len === 0)
            return -1;
        var n = +fromIndex || 0;
        if (Math.abs(n) === Infinity)
            n = 0;
        if (n >= len)
            return -1;
        var k = Math.max(n >= 0 ? n : len - Math.abs(n), 0);
        while (k < len) {
            if (k in O && O[k] === searchElement)
                return k;
            k++;
        }
        return -1;
    };
}

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
    result = result.replace(/(<)/g, "&lt;");
    result = result.replace(/(>)/g, "&gt;");
    result = result.replace(/(\n)/g, "<br/>");
    result = result.replace(/(\")/g, "&quot;");
    return result;
};

// escape attribute
utils.escape_attr = function (attr) {
    if (!attr)
        return attr;
    var result = attr.toString();
    result = result.replace(/(\n)/g, "&#13;&#10;");
    result = result.replace(/(\")/g, "&quot;");
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
utils._get_user_agent = function () {
    if (window.navigator && window.navigator.userAgent)
        utils.user_agent = window.navigator.userAgent.toLowerCase();
    else
        utils.user_agent = "unknown";
};
utils._get_user_agent();
utils._get_os_name = function () {
    var name = "";
    if (window.navigator && window.navigator.platform) {
        var platform = window.navigator.platform.toLowerCase();
        if (platform.indexOf("ipad") != -1 || platform.indexOf("iphone") != -1 || platform.indexOf("ipod") != -1)
            name = "ios";
    }
    if (!name && window.navigator && window.navigator.appVersion) {
        var app_version = window.navigator.appVersion.toLowerCase();
        if (app_version.indexOf("win") != -1)
            name = "windows";
        else if (app_version.indexOf("mac") != -1)
            name = "macos";
        else if (app_version.indexOf("x11") != -1 || app_version.indexOf("linux") != -1)
            name = "linux";
    }
    utils.os_name = name ? name : "unknown";
    utils["os_is_"+name] = true;
};
utils._get_os_name();
utils._extract_browser_version = function (ua, re) {
    var matches = ua.match(re);
    if (matches && !isNaN(parseFloat(matches[1])))
        return parseFloat(matches[1]);
    return 0.0;
};
utils._get_browser_info = function () {
    // get browser name and version
    var name = "unknown";
    var version = 0.0;
    var ua = utils.user_agent;
    if (ua.indexOf("firefox") != -1) {
        name = "firefox";
        version = utils._extract_browser_version(ua, /firefox\/(\d+\.\d+)/);
        if (!version)
            version = utils._extract_browser_version(ua, /rv:(\d+\.\d+)/);
    }
    else if (ua.indexOf("chromium") != -1) {
        name = "chromium";
        version = utils._extract_browser_version(ua, /chromium\/(\d+\.\d+)/);
    }
    else if (ua.indexOf("chrome") != -1) {
        name = "chrome";
        version = utils._extract_browser_version(ua, /chrome\/(\d+\.\d+)/);
    }
    else if (ua.indexOf("iemobile") != -1) {
        name = "iemobile";
        version = utils._extract_browser_version(ua, /iemobile\/(\d+\.\d+)/);
    }
    else if (ua.indexOf("msie") != -1) {
        name = "ie";
        version = utils._extract_browser_version(ua, /msie (\d+\.\d+)/);
        if (version < 7)
            utils.browser_is_ie6 = true;
        else if (version < 8)
            utils.browser_is_ie7 = true;
        else if (version < 9)
            utils.browser_is_ie8 = true;
        else
            utils.browser_is_ie9 = true;
    }
    else if (ua.indexOf("trident") != -1) {
        name = "ie";
        version = utils._extract_browser_version(ua, /rv:(\d+\.\d+)/);
        utils.browser_is_ie9 = true;
    }
    else if (ua.indexOf("opera") != -1) {
        name = "opera";
        version = utils._extract_browser_version(ua, /opera\/(\d+\.\d+)/);
    }
    else if (ua.indexOf("konqueror") != -1) {
        name = "konqueror";
        version = utils._extract_browser_version(ua, /konqueror\/(\d+\.\d+)/);
    }
    else if (ua.indexOf("mobile safari") != -1) {
        name = "mobile_safari";
        version = utils._extract_browser_version(ua, /mobile safari\/(\d+\.\d+)/);
    }
    else if (ua.indexOf("safari") != -1) {
        name = "safari";
        version = utils._extract_browser_version(ua, /safari\/(\d+\.\d+)/);
    }
    utils.browser_name = name;
    utils["browser_is_"+name] = true;
    utils.browser_version = version;
    
    // detect type of device
    utils.is_phone = ua.indexOf("iphone") != -1 || ua.indexOf("ipod") != -1 || ua.indexOf("android") != -1 || ua.indexOf("iemobile") != -1 || ua.indexOf("opera mobi") != -1 || ua.indexOf("opera mini") != -1 || ua.indexOf("windows ce") != -1 || ua.indexOf("fennec") != -1 || ua.indexOf("series60") != -1 || ua.indexOf("symbian") != -1 || ua.indexOf("blackberry") != -1 || window.orientation !== undefined;
    utils.is_tablet = window.navigator && window.navigator.platform == "iPad";
    utils.is_mobile = utils.is_phone || utils.is_tablet;
    utils.is_tactile = document.documentElement && "ontouchstart" in document.documentElement;
};
utils._get_browser_info();

// Translations utils
utils._translations = { en: {} };
utils._current_lang = "en";
utils._current_catalog = utils._translations.en;
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
    else if (utils._current_lang != "en" && text in utils._translations.en)
        return utils._translations.en[text];
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

// Versions comparison
utils.compare_versions = function (v1, comparator, v2) {
    "use strict";
    comparator = comparator == "=" ? "==" : comparator;
    var v1parts = v1.split("."), v2parts = v2.split(".");
    var maxLen = Math.max(v1parts.length, v2parts.length);
    var part1, part2;
    var cmp = 0;
    for (var i=0; i < maxLen && !cmp; i++) {
        part1 = parseInt(v1parts[i], 10) || 0;
        part2 = parseInt(v2parts[i], 10) || 0;
        if (part1 < part2)
            cmp = 1;
        if (part1 > part2)
            cmp = -1;
    }
    return eval("0" + comparator + cmp);
};

// JavaScript classes related functions
utils.setup_class = function (obj, options, allowed_options) {
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

// MD5 sum computation (requires the SparkMD5 library)
utils.compute_md5 = function (file, callback) {
    var blobSlice = File.prototype.slice || File.prototype.mozSlice || File.prototype.webkitSlice;
    var chunkSize = 2097152; // Read in chunks of 2MB
    var chunks = Math.ceil(file.size / chunkSize);
    var currentChunk = 0;
    var spark = new SparkMD5.ArrayBuffer();
    var fileReader = new FileReader();

    fileReader.onload = function (e) {
        spark.append(e.target.result); // Append array buffer
        ++currentChunk;

        if (currentChunk < chunks) {
            loadNext();
        } else {
            callback(spark.end());
        }
    };

    fileReader.onerror = function () {
        console.warn('MD5 computation failed');
    };

    function loadNext() {
        var start = currentChunk * chunkSize;
        var end = ((start + chunkSize) >= file.size) ? file.size : start + chunkSize;
        fileReader.readAsArrayBuffer(blobSlice.call(file, start, end));
    }

    loadNext();
};
