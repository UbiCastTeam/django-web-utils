/*******************************************
* Password request manager                 *
* Author: Stephane Diemer                  *
*******************************************/
/* global jsu */
/* global OverlayDisplayManager */

function PwdManager (options) {
    // params
    this.url = '';
    // vars
    this.overlay = null;
    this.formEle = null;
    this.msgEle = null;
    this.inProgress = false;
    this.cb = null;
    this.cbData = {};
    this.pwdOk = false;

    jsu.setObjectAttributes(this, options, [
        // allowed options
        'url'
    ]);
}

PwdManager.prototype.build = function () {
    this.overlay = new OverlayDisplayManager();

    this.formEle = document.createElement('form');
    this.formEle.setAttribute('method', 'get');
    this.formEle.setAttribute('action', this.url);
    this.formEle.innerHTML = '<div class="messages" style="display: none; margin-bottom: 16px;"></div>' +
        '<input type="hidden" name="csrfmiddlewaretoken" value="' + jsu.getCookie('csrftoken') + '"/>' +
        '<label for="id_data">' + jsu.translate('Password:') + '</label> ' +
        '<input type="password" id="id_data" name="data" value="" style="width: 250px;"/> ' +
        '<button type="submit">' + jsu.translate('Send') + '</button>';
    this.msgEle = this.formEle.querySelector('.messages');

    // events
    const obj = this;
    this.formEle.addEventListener('submit', function (event) {
        event.preventDefault();
        obj.displayMessage('loading', jsu.translate('Authenticating') + '...');
        obj.sendRequest(true);
        return false;
    });
};

PwdManager.prototype.onSubmit = function (form, event) {
    if (this.pwdOk) {
        return true;
    }
    if (event) {
        event.preventDefault();
    }
    this.checkPassword(function (success, data) {
        if (success) {
            data.form.submit();
        }
    }, { form: form });
    return false;
};


PwdManager.prototype.checkPassword = function (cb, cbData) {
    this.cb = cb ? cb : null;
    this.cbData = cbData ? cbData : {};
    if (this.pwdOk) {
        if (this.cb) {
            this.cb(true, this.cbData);
        }
        return;
    }
    this.sendRequest(false);
};

PwdManager.prototype.sendRequest = function (post) {
    if (this.inProgress) {
        return;
    }
    this.inProgress = true;
    const obj = this;
    jsu.httpRequest({
        method: post ? 'POST' : 'GET',
        url: this.url,
        data: post ? new FormData(this.formEle) : null,
        json: true,
        callback: function (req, response) {
            if (!req.status) {
                obj.displayMessage('error', 'Network error');
            } if (req.status != 200) {
                obj.displayMessage('error', response.error);
            } else {
                if (!response.pwd_ok) {
                    obj.openPasswordForm();
                } else {
                    obj.pwdOk = true;
                    if (obj.cb) {
                        obj.cb(true, obj.cbData);
                    }
                    if (post) {
                        obj.msgEle.style.setProperty('display', '');
                        obj.success = true;
                        obj.overlay.hide();
                    }
                }
            }
            obj.inProgress = false;
        }
    });
};

PwdManager.prototype.displayMessage = function (type, text) {
    const html = '<div class="message ' + type + '">' + (type == 'loading' ? '<i class="fa fa-spin fa-spinner"></i> ' : '') + jsu.escapeHTML(text) + '</div>';
    if (this.msgTimeout) {
        clearTimeout(this.msgTimeout);
        this.msgTimeout = null;
    }
    this.msgEle.innerHTML = html;
    this.msgEle.style.setProperty('display', '');
    if (type != 'loading') {
        const obj = this;
        this.msgTimeout = setTimeout(function () {
            obj.msgEle.style.setProperty('display', 'none');
            obj.msgTimeout = null;
        }, 8000);
    }
};

PwdManager.prototype.openPasswordForm = function () {
    if (!this.overlay) {
        this.build();
    }
    const obj = this;
    this.success = false;
    this.overlay.show({
        html: this.formEle,
        title: jsu.translate('Enter password for commands'),
        onHide: function () {
            if (!obj.success && obj.cb) {
                obj.cb(false, obj.cbData); // user cancelled or closed menu
            }
        }
    });
};
