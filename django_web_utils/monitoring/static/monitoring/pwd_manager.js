/*******************************************
* MediaServer list manager                 *
* Copyright: UbiCast, all rights reserved  *
* Author: Stephane Diemer                  *
*******************************************/

function PwdManager(options) {
    // params
    this.url = "";
    // vars
    this.overlay = null;
    this.$form = null;
    this.in_progress = false;
    this.cb = null;
    this.cb_data = {};
    this.pwd_ok = false;
    
    utils.setup_class(this, options, [
        // allowed options
        "url"
    ]);
}

PwdManager.prototype.build = function () {
    this.overlay = new OverlayDisplayManager();
    
    var html = "<form class=\"margin-8\">";
    html += "<div class=\"messages\" style=\"display: none; margin-bottom: 16px;\"></div>";
    html += "<label for=\"id_data\">"+this.translate("Password:")+"</label> ";
    html += "<input type=\"password\" id=\"id_data\" name=\"data\" value=\"\" style=\"width: 250px;\"/>";
    html += "</form>";
    this.$form = $(html);
    this.$msg = $(".messages", this.$form);
    
    // events
    var obj = this;
    this.$form.submit(function () {
        obj.display_message("loading", obj.translate("Authenticating")+"...");
        obj.send_request(true);
        return false;
    });
};

PwdManager.prototype.on_submit = function (form) {
    if (this.pwd_ok)
        return true;
    this.check_password(function (success, data) {
        if (success)
            $(data.form).submit();
    }, { form: form });
    return false;
};


PwdManager.prototype.check_password = function (cb, cb_data) {
    this.cb = (cb) ? cb : null;
    this.cb_data = (cb_data) ? cb_data : {};
    if (this.pwd_ok) {
        if (this.cb)
            this.cb(true, this.cb_data);
        return;
    }
    this.send_request(false);
};

PwdManager.prototype.send_request = function (post) {
    if (this.in_progress)
        return;
    this.in_progress = true;
    var obj = this;
    var callback = function (result) {
        if (result.success) {
            obj.pwd_ok = true;
            if (obj.cb)
                obj.cb(true, obj.cb_data);
            if (post) {
                obj.$msg.slideUp("fast");
                obj.success = true;
                obj.overlay.hide();
            }
        }
        else {
            if (post) {
                obj.display_message("error", result.message);
            }
            else {
                if (result.error && result.error == "wpwd")
                    obj.display_message("error", result.message);
                obj.open_pwd_form();
            }
        }
        obj.in_progress = false;
    };
    $.ajax({
        url: this.url,
        type: (post) ? "POST" : "GET",
        data: (post) ? { data: $("input", obj.$form).val() } : {},
        dataType: "json",
        cache: false,
        success: function (response) {
            if ("success" in response)
                callback(response);
            else
                callback({ success: false, message: obj.translate("Unknown error"), data: response });
        },
        error: function (xhr, textStatus, thrownError) {
            callback({ success: false, message: thrownError+": "+textStatus });
        }
    });
};

PwdManager.prototype.display_message = function (type, text) {
    var html = "<div class=\"message "+type+"\">"+(type == "loading" ? "<i class=\"fa fa-spin fa-spinner\"></i> " : "")+utils.escape_html(text)+"</div>";
    if (this.msg_timeout) {
        clearTimeout(this.msg_timeout);
        this.msg_timeout = null;
        this.$msg.html(html);
    }
    else {
        this.$msg.html(html);
        this.$msg.slideDown("fast");
    }
    if (type != "loading") {
        var obj = this;
        this.msg_timeout = setTimeout(function () {
            obj.$msg.slideUp("fast");
            obj.msg_timeout = null;
        }, 8000);
    }
};

PwdManager.prototype.open_pwd_form = function () {
    if (!this.overlay)
        this.build();
    var obj = this;
    this.success = false;
    this.overlay.show({
        html: this.$form,
        title: this.translate("Enter password for commands"),
        buttons: [
            {
                klass: "std-btn",
                label: this.translate("Cancel"),
                close: true
            },
            {
                klass: "std-btn main",
                label: this.translate("Send password"),
                callback: function (btn_dom) {
                    obj.$form.submit();
                }
            }
        ],
        on_hide: function () {
            if (!obj.success && obj.cb)
                obj.cb(false, obj.cb_data); // user cancelled or closed menu
        }
    });
};
