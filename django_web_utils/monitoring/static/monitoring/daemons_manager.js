/*******************************************
* Daemons manager                          *
* Copyright: UbiCast, all rights reserved  *
* Author: Stephane Diemer                  *
*******************************************/

function DaemonsManager(options) {
    this.daemons = [];
    this.commands_url = "";
    this.status_url = "";
    this.data = {};
    
    /* translations
        "Command result": "Command result",
        "No messages returned.": "No messages returned.",
        "running": "running",
        "not running": "not running"
    */
    
    utils.setup_class(this, options);

    this.overlay = new OverlayDisplayManager();
    
    var obj = this;
    $(document).ready(function() {
        obj.init();
    });
}

DaemonsManager.prototype.init = function() {
    var obj = this;
    this.daemons.push("all");
    for (var i = 0; i < this.daemons.length; i++) {
        var daemon = this.daemons[i];
        $(".daemon-"+daemon+" .daemon-log-clear").click({daemon: daemon}, function(event) {
            obj.send_daemon_command(event.data.daemon, "clear_log");
        });
        $(".daemon-"+daemon+" .daemon-start").click({daemon: daemon}, function(event) {
            obj.send_daemon_command(event.data.daemon, "start");
        });
        $(".daemon-"+daemon+" .daemon-stop").click({daemon: daemon}, function(event) {
            obj.send_daemon_command(event.data.daemon, "stop");
        });
        $(".daemon-"+daemon+" .daemon-restart").click({daemon: daemon}, function(event) {
            obj.send_daemon_command(event.data.daemon, "restart");
        });
    }
    
    this.refresh_daemon_status();
};


DaemonsManager.prototype.send_daemon_command = function(daemon, cmd) {
    var obj = this;
    var callback = function (response) {
        var msg;
        if (response.message)
            msg = response.message;
        if (response.error)
            msg = response.error;
        if (!msg)
            msg = obj.translate("No messages returned.");
        obj.overlay.show({
            title: obj.translate("Command result"),
            html: msg,
            buttons: [
                { label: obj.translate("Close"), close: true }
            ]
        });
    };
    $.ajax({
        type: "POST",
        url: this.commands_url,
        data: { daemon: daemon, cmd: cmd, csrfmiddlewaretoken: utils.get_cookie("csrftoken") },
        dataType: "json",
        cache: false,
        success: function(response) {
            callback(response);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            callback({
                success: false,
                message: textStatus+" ("+(errorThrown ? errorThrown : obj.translate("server unreachable"))+")"
            });
        }
    });
};

DaemonsManager.prototype.refresh_daemon_status = function() {
    var obj = this;
    $.ajax({
        url: this.status_url,
        dataType: "json",
        cache: false,
        success: function(response) {
            if (typeof response == "object") {
                for (var daemon_name in response) {
                    if (!(daemon_name in obj.data))
                        obj.data[daemon_name] = {};
                    var stored = obj.data[daemon_name];
                    if (response[daemon_name].running !== stored.running) {
                        stored.running = response[daemon_name].running;
                        if (response[daemon_name].running)
                            $(".daemon-"+daemon_name+" .daemon-status").html("<span class=\"green\">"+obj.translate("running")+"</span>");
                        else
                            $(".daemon-"+daemon_name+" .daemon-status").html("<span class=\"red\">"+obj.translate("not running")+"</span>");
                    }
                    if (response[daemon_name].log_mtime !== stored.log_mtime) {
                        stored.log_mtime = response[daemon_name].log_mtime;
                        if (response[daemon_name].log_mtime)
                            $(".daemon-"+daemon_name+" .daemon-log-mtime").html(response[daemon_name].log_mtime);
                        else
                            $(".daemon-"+daemon_name+" .daemon-log-mtime").html(obj.translate("unknown"));
                    }
                    if (response[daemon_name].log_size !== stored.log_size) {
                        stored.log_size = response[daemon_name].log_size;
                        if (response[daemon_name].log_size)
                            $(".daemon-"+daemon_name+" .daemon-log-size").html(response[daemon_name].log_size);
                        else
                            $(".daemon-"+daemon_name+" .daemon-log-size").html("0");
                    }
                }
            }
        }
    });
    setTimeout(function() {
        obj.refresh_daemon_status();
    }, 5000);
};
