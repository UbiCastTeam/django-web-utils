/*******************************************
* Daemons manager                          *
* Author: Stephane Diemer                  *
*******************************************/
/* global jsu */
/* global OverlayDisplayManager */
/* global PwdManager */

function DaemonsManager (options) {
    // params
    this.daemons = []; // list of dict with at least a name attr
    this.commandsURL = '';
    this.statusURL = '';
    this.pwdURL = '';
    // vars
    this.daemons = {};
    this.refreshDelay = 5000;

    jsu.setObjectAttributes(this, options, [
        // allowed options
        'daemons',
        'commandsURL',
        'statusURL',
        'pwdURL'
    ]);

    this.overlay = new OverlayDisplayManager();
    this.pwdMan = new PwdManager({ url: this.pwdURL });

    jsu.onDOMLoad(this.init.bind(this));
}

DaemonsManager.prototype.init = function () {
    for (let i = 0; i < this.daemons.length; i++) {
        let daemon = this.daemons[i];
        if (typeof daemon == 'string') {
            daemon = { name: daemon };
            this.daemons[i] = daemon;
        }
        const clearBtn = document.querySelector('.daemon-' + daemon.name + ' .daemon-log-clear');
        if (clearBtn) {
            clearBtn.addEventListener('click', this.sendDaemonCommand.bind(this, daemon, 'clear_log'));
        }
        const startBtn = document.querySelector('.daemon-' + daemon.name + ' .daemon-start');
        if (startBtn) {
            startBtn.addEventListener('click', this.sendDaemonCommand.bind(this, daemon, 'start'));
        }
        const stopBtn = document.querySelector('.daemon-' + daemon.name + ' .daemon-stop');
        if (stopBtn) {
            stopBtn.addEventListener('click', this.sendDaemonCommand.bind(this, daemon, 'stop'));
        }
        const restartBtn = document.querySelector('.daemon-' + daemon.name + ' .daemon-restart');
        if (restartBtn) {
            restartBtn.addEventListener('click', this.sendDaemonCommand.bind(this, daemon, 'restart'));
        }
    }
    this.refreshDaemonStatus();
};


DaemonsManager.prototype.sendDaemonCommand = function (daemon, cmd) {
    if (!daemon.name) {
        return console.log('Invalid daemon given to sendDaemonCommand function.');
    }
    if (daemon.isRoot) {
        this.pwdMan.check_password(function (success, data) {
            if (success) {
                data.obj._sendDaemonCommand(data.daemon, data.cmd);
            }
        }, { obj: this, daemon: daemon, cmd: cmd });
    } else {
        this._sendDaemonCommand(daemon, cmd);
    }
};
DaemonsManager.prototype._sendDaemonCommand = function (daemon, cmd) {
    const obj = this;
    jsu.httpRequest({
        method: 'POST',
        url: this.commandsURL,
        data: { daemon: daemon.name, cmd: cmd, csrfmiddlewaretoken: jsu.getCookie('csrftoken') },
        json: true,
        callback: function (req, response) {
            let msg;
            if (response.message) {
                msg = response.message;
            } else if (response.error) {
                msg = response.error;
            }
            if (!msg) {
                msg = jsu.translate('No messages have been returned.');
            }
            const level = req.status == 200 ? 'success' : 'error';
            const msgEle = document.createElement('div');
            msgEle.setAttribute('class', 'message ' + level);
            msgEle.innerHTML = msg;
            obj.overlay.show({
                title: jsu.translate('Command result'),
                html: msgEle,
                buttons: [
                    { label: jsu.translate('Close'), close: true }
                ]
            });
        }
    });
};

DaemonsManager.prototype.refreshDaemonStatus = function () {
    const obj = this;
    jsu.httpRequest({
        method: 'GET',
        url: this.statusURL,
        json: true,
        callback: function (req, response) {
            if (req.status != 200) {
                console.error('Failed to get daemons status.', req);
                return;
            }
            let daemonName;
            for (daemonName in response) {
                if (!(daemonName in obj.daemons)) {
                    obj.daemons[daemonName] = {};
                }
                const stored = obj.daemons[daemonName];
                const running = response[daemonName].running;
                if (running !== stored.running) {
                    stored.running = running;
                    const statusEle = document.querySelector('.daemon-' + daemonName + ' .daemon-status');
                    if (running === true) {
                        statusEle.innerHTML = '<span class=\'green\'>' + jsu.translate('running') + '</span>';
                    } else if (running === false) {
                        statusEle.innerHTML = '<span class=\'red\'>' + jsu.translate('not running') + '</span>';
                    } else {
                        statusEle.innerHTML = '<span class=\'yellow\'>? </span>';
                        const btnEle = document.createElement('button');
                        btnEle.setAttribute('type', 'button');
                        btnEle.setAttribute('title', jsu.translate('Click to enter password'));
                        btnEle.innerHTML = jsu.translate('need password');
                        btnEle.addEventListener('click', function () {
                            obj.pwdMan.check_password();
                        });
                        statusEle.appendChild(btnEle);
                    }
                }
                const logMTime = response[daemonName].log_mtime;
                if (logMTime !== stored.logMTime) {
                    stored.logMTime = logMTime;
                    const mTimeEle = document.querySelector('.daemon-' + daemonName + ' .daemon-log-mtime');
                    mTimeEle.innerHTML = logMTime ? logMTime : '-';
                }
                const logSize = response[daemonName].log_size;
                if (logSize !== stored.logSize) {
                    stored.logSize = logSize;
                    const sizeEle = document.querySelector('.daemon-' + daemonName + ' .daemon-log-size');
                    sizeEle.innerHTML = logSize ? logSize : '-';
                }
            }
        }
    });
    setTimeout(function () {
        obj.refreshDaemonStatus();
    }, this.refreshDelay);
};
