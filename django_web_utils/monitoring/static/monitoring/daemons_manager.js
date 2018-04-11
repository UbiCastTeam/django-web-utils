/*******************************************
* Daemons manager                          *
* Copyright: UbiCast, all rights reserved  *
* Author: Stephane Diemer                  *
*******************************************/

function DaemonsManager(options) {
    // params
    this.daemons = [];  // list of dict with at least a name attr
    this.commands_url = "";
    this.status_url = "";
    this.pwd_url = "";
    // vars
    this.data = {};
    this.refresh_delay = 5000;

    utils.setup_class(this, options, [
        // allowed options
        "daemons",
        "commands_url",
        "status_url",
        "pwd_url"
    ]);

    this.overlay = new OverlayDisplayManager();
    this.pwd_man = new PwdManager({ url: this.pwd_url });
    
    var obj = this;
    $(document).ready(function () {
        obj.init();
    });
}

DaemonsManager.prototype.init = function () {
    var obj = this;
    for (var i = 0; i < this.daemons.length; i++) {
        var daemon = this.daemons[i];
        if (typeof daemon == "string") {
            daemon = { name: daemon };
            this.daemons[i] = daemon;
        }
        $(".daemon-"+daemon.name+" .daemon-log-clear").click({daemon: daemon}, function (event) {
            obj.send_daemon_command(event.data.daemon, "clear_log");
        });
        $(".daemon-"+daemon.name+" .daemon-start").click({daemon: daemon}, function (event) {
            obj.send_daemon_command(event.data.daemon, "start");
        });
        $(".daemon-"+daemon.name+" .daemon-stop").click({daemon: daemon}, function (event) {
            obj.send_daemon_command(event.data.daemon, "stop");
        });
        $(".daemon-"+daemon.name+" .daemon-restart").click({daemon: daemon}, function (event) {
            obj.send_daemon_command(event.data.daemon, "restart");
        });
    }
    
    this.refresh_daemon_status();
};


DaemonsManager.prototype.send_daemon_command = function (daemon, cmd) {
    if (!daemon.name)
        return console.log("Invalid daemon given to send_daemon_command function.");
    if (daemon.is_root) {
        this.pwd_man.check_password(function (success, data) {
            if (success)
                data.obj._send_daemon_command(data.daemon, data.cmd);
        }, { obj: this, daemon: daemon, cmd: cmd });
    }
    else
        this._send_daemon_command(daemon, cmd);
};
DaemonsManager.prototype._send_daemon_command = function (daemon, cmd) {
    var obj = this;
    var callback = function (response) {
        var msg;
        if (response.message)
            msg = response.message;
        if (response.error)
            msg = response.error;
        if (!msg)
            msg = obj.translate("No messages have been returned.");
        obj.overlay.show({
            title: obj.translate("Command result"),
            html: msg,
            buttons: [
                { klass: "std-btn", label: obj.translate("Close"), close: true }
            ]
        });
    };
    $.ajax({
        type: "POST",
        url: this.commands_url,
        data: { daemon: daemon.name, cmd: cmd, csrfmiddlewaretoken: utils.get_cookie("csrftoken") },
        dataType: "json",
        cache: false,
        success: function (response) {
            callback(response);
        },
        error: function (jqXHR, textStatus, thrownError) {
            callback({
                success: false,
                message: textStatus+" ("+(thrownError ? thrownError : obj.translate("server unreachable"))+")"
            });
        }
    });
};

DaemonsManager.prototype.refresh_daemon_status = function () {
    var obj = this;
    $.ajax({
        url: this.status_url,
        dataType: "json",
        cache: false,
        success: function (response) {
            for (var daemon_name in response) {
                if (!(daemon_name in obj.data))
                    obj.data[daemon_name] = {};
                var stored = obj.data[daemon_name];
                if (response[daemon_name].running !== stored.running) {
                    stored.running = response[daemon_name].running;
                    if (response[daemon_name].running === true)
                        $(".daemon-"+daemon_name+" .daemon-status").html("<span class=\"green\">"+obj.translate("running")+"</span>");
                    else if (response[daemon_name].running === false)
                        $(".daemon-"+daemon_name+" .daemon-status").html("<span class=\"red\">"+obj.translate("not running")+"</span>");
                    else {
                        var $link = $("<span class=\"yellow clickable\" title=\""+obj.translate("Click to enter password")+"\">? ("+obj.translate("need password")+")</span>");
                        $link.click({ obj: obj }, function (event) {
                            event.data.obj.pwd_man.check_password();
                        })
                        $(".daemon-"+daemon_name+" .daemon-status").empty().append($link);
                    }
                }
                if (response[daemon_name].log_mtime !== stored.log_mtime) {
                    stored.log_mtime = response[daemon_name].log_mtime;
                    if (response[daemon_name].log_mtime)
                        $(".daemon-"+daemon_name+" .daemon-log-mtime").html(response[daemon_name].log_mtime);
                    else
                        $(".daemon-"+daemon_name+" .daemon-log-mtime").html("-");
                }
                if (response[daemon_name].log_size !== stored.log_size) {
                    stored.log_size = response[daemon_name].log_size;
                    if (response[daemon_name].log_size)
                        $(".daemon-"+daemon_name+" .daemon-log-size").html(response[daemon_name].log_size);
                    else
                        $(".daemon-"+daemon_name+" .daemon-log-size").html("-");
                }
            }
        }
    });
    setTimeout(function () {
        obj.refresh_daemon_status();
    }, this.refresh_delay);
};
