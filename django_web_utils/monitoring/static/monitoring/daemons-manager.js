/*******************************************
* Daemons manager                          *
* Author: Stephane Diemer                  *
*******************************************/
/* global gettext */
/* global jsu */
/* global OverlayDisplayManager */
/* global PollingManager */
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
    for (const daemon of this.daemons) {
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

    new PollingManager(this.refreshDaemons.bind(this), this.refreshDelay);
};

DaemonsManager.prototype.sendDaemonCommand = function (daemon, cmd) {
    if (!daemon.name) {
        return console.log('Invalid daemon given to sendDaemonCommand function.');
    }
    if (daemon.isRoot) {
        this.pwdMan.checkPassword(function (success, data) {
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
            const msgEle = document.createElement('div');
            if (req.status != 200) {
                msgEle.setAttribute('class', 'message error');
                msgEle.textContent = response.error || response;
            } else if (!response.messages) {
                msgEle.setAttribute('class', 'message warning');
                msgEle.textContent = gettext('No messages have been returned.');
            } else {
                for (let i = 0; i < response.messages.length; i++) {
                    const msg = response.messages[i];
                    const entryEle = document.createElement('div');
                    entryEle.setAttribute('class', 'message ' + msg.level);
                    entryEle.innerHTML = jsu.escapeHTML(msg.text);
                    if (msg.out) {
                        entryEle.innerHTML += '\n<div>' + jsu.escapeHTML(gettext('Command output:')) + '<br/>\n';
                        entryEle.innerHTML += '<pre>' + jsu.escapeHTML(msg.out) + '</pre></div>';
                    }
                    msgEle.appendChild(entryEle);
                }
            }
            obj.overlay.show({
                title: gettext('Command result'),
                html: msgEle,
                buttons: [
                    { label: gettext('Close'), close: true }
                ]
            });
        }
    });
};

DaemonsManager.prototype.refreshDaemons = function (notifyEnd) {
    const obj = this;
    jsu.httpRequest({
        method: 'GET',
        url: this.statusURL,
        json: true,
        callback: function (req, response) {
            if (req.status != 200) {
                console.error('Failed to get daemons status.', req);
            } else {
                for (const name in response) {
                    obj.updateDaemonData(name, response[name]);
                }
            }
            notifyEnd();
        }
    });
};

DaemonsManager.prototype.updateDaemonData = function (name, data) {
    if (!(name in this.daemons)) {
        this.daemons[name] = {};
    }
    const stored = this.daemons[name];
    const running = data.running;
    if (running !== stored.running) {
        stored.running = running;
        const statusEle = document.querySelector('.daemon-' + name + ' .daemon-status');
        if (running === true) {
            statusEle.innerHTML = '<span class="green">' + jsu.escapeHTML(gettext('running')) + '</span>';
        } else if (running === false) {
            statusEle.innerHTML = '<span class="red">' + jsu.escapeHTML(gettext('not running')) + '</span>';
        } else {
            statusEle.innerHTML = '<span class="yellow"> ? </span>';
            const btnEle = document.createElement('button');
            btnEle.setAttribute('type', 'button');
            btnEle.setAttribute('title', gettext('Click to enter password'));
            btnEle.innerHTML = jsu.escapeHTML(gettext('need password'));
            btnEle.addEventListener('click', this.pwdMan.checkPassword);
            statusEle.appendChild(btnEle);
        }
    }
    const logMTime = data.log_mtime;
    if (logMTime !== stored.logMTime) {
        stored.logMTime = logMTime;
        const mTimeEle = document.querySelector('.daemon-' + name + ' .daemon-log-mtime');
        mTimeEle.textContent = logMTime ? logMTime : '-';
    }
    const logSize = data.log_size;
    if (logSize !== stored.logSize) {
        stored.logSize = logSize;
        const sizeEle = document.querySelector('.daemon-' + name + ' .daemon-log-size');
        sizeEle.textContent = logSize ? logSize : '-';
    }
};
