/*******************************************
* File browser                             *
* Author: Stephane Diemer                  *
*******************************************/
/* global jsu */
/* global OverlayDisplayManager */

function FileBrowser (options) {
    // params
    this.baseURL = '';
    this.dirsURL = '';
    this.contentURL = '';
    this.previewURL = '';
    this.actionURL = '';

    // vars
    this.csrfToken = '';
    this.placeElement = null;
    this.sizeElement = null;
    this.dirsCountElement = null;
    this.filesCountElement = null;
    this.dropZoneElement = null;
    this.overlay = null;
    this.dragEntered = false;
    this.path = '';
    this.flatTree = [];
    this.ordering = 'name-asc';
    this.files = {};
    this.opened = [];
    this.menuElements = {};
    this.imagesExtenstions = ['png', 'gif', 'bmp', 'tiff', 'jpg', 'jpeg'];

    jsu.setObjectAttributes(this, options, [
        // allowed options
        'baseURL',
        'dirsURL',
        'contentURL',
        'previewURL',
        'actionURL'
    ]);
    this.overlay = new OverlayDisplayManager();

    jsu.onDOMLoad(this.init.bind(this));
}

FileBrowser.prototype.init = function () {
    this.csrfToken = jsu.getCookie('csrftoken');
    // get elements
    this.menuTreeElement = document.getElementById('fm_dirs_tree');
    this.menuRootElement = document.getElementById('fm_root');
    this.placeElement = document.getElementById('fm_files_list');
    this.sizeElement = document.getElementById('fm_total_size');
    this.dirsCountElement = document.getElementById('fm_total_nb_dirs');
    this.filesCountElement = document.getElementById('fm_total_nb_files');
    this.dropZoneElement = document.getElementById('fm_drop_zone');
    // load folder content
    this.ordering = jsu.getCookie('browser-ordering', this.ordering);
    if (this.ordering != 'name-asc') {
        document.getElementById('fm_files_ordering').val(this.ordering);
    }
    this.loadDirs();
    // bind events
    const obj = this;
    document.getElementById('fm_btn_add_folder').addEventListener('click', function () {
        obj.addFolder();
    });
    document.getElementById('fm_btn_add_file').addEventListener('click', function () {
        obj.addFile();
    });
    document.getElementById('fm_btn_search').addEventListener('click', function () {
        obj.search();
    });
    document.getElementById('fm_btn_refresh').addEventListener('click', function () {
        obj.refresh();
    });
    document.getElementById('fm_files_ordering').addEventListener('change', function () {
        obj.changeOrdering($(this).val());
    });
    document.getElementById('fm_content_place').addEventListener('dragenter', function (evt) {
        evt.preventDefault();
        if (obj.containsFiles(evt.originalEvent)) {
            obj.dragEntered = true;
            obj.dropZoneElement.setAttribute('class', 'hovered');
        }
    });
    document.getElementById('fm_content_place').addEventListener('dragover', function (evt) {
        evt.preventDefault();
    });
    document.getElementById('fm_content_place').addEventListener('dragleave', function () {
        if (!obj.dragEntered) {
            obj.dropZoneElement.setAttribute('class', '');
        }
        obj.dragEntered = false;
    });
    document.body.addEventListener('drop', function (evt) {
        evt.preventDefault();
        if (obj.containsFiles(evt.originalEvent)) {
            obj.dropZoneElement.setAttribute('class', 'uploading');
            obj.onFilesDrop(evt.originalEvent);
            return false;
        }
    });
    window.addEventListener('hashchange', function () {
        obj.loadContent();
    });
};

FileBrowser.prototype.containsFiles = function (evt) {
    if (evt.dataTransfer.types) {
        for (let i = 0; i < evt.dataTransfer.types.length; i++) {
            if (evt.dataTransfer.types[i] == 'Files') {
                return true;
            }
        }
    }
    return false;
};

FileBrowser.prototype.httpRequest = function (args) {
    const params = args.params ? args.params : {};
    if (args.cache === undefined || args.cache) {
        params._ = (new Date()).getTime();
    }
    let url = args.url;
    const urlParams = [];
    let param;
    for (param in params) {
        urlParams.push(encodeURIComponent(param) + '=' + encodeURIComponent(params[param]));
    }
    if (urlParams.length > 0) {
        url += '?' + urlParams.join('&');
    }
    // const data = args.data ? args.data : {};
    const req = new XMLHttpRequest();
    if (args.callback) {
        req.onreadystatechange = function () {
            if (this.readyState !== XMLHttpRequest.DONE) {
                return;
            }
            let jsonResponse;
            try {
                jsonResponse = JSON.parse(this.responseText);
            } catch (e) {
                jsonResponse = {
                    error: 'Failed to parse load dirs response (status: ' + this.status + '): ' + e
                };
            }
            if (this.status === 200) {
                // success
                args.callback(jsonResponse);
            } else {
                // fail
                args.callback({
                    success: false,
                    message: jsonResponse.error
                });
            }
        };
    }
    req.open(args.method ? args.method : 'GET', url, true);
    req.send();
};

FileBrowser.prototype.loadDirs = function () {
    const obj = this;
    this.httpRequest({
        method: 'GET',
        url: this.dirsURL,
        callback: function (response) {
            obj.parseDirsResponse(response);
        }
    });
};
FileBrowser.prototype.parseDirsResponse = function (response) {
    if (!response.success) {
        this.placeElement.innerHTML = '<div class="message-error">' + response.message + '</div>';
        return;
    }

    const flatTree = [];
    if (response.dirs) {
        const menuEle = document.createElement('ul');
        this.getTreeDirs(response.dirs, menuEle, flatTree, '', 1);
        this.menuTreeElement.appendChild(menuEle);
    }
    this.flatTree = flatTree; // used for move function
    // open trees
    const stored = jsu.getCookie('browser-tree');
    if (stored) {
        this.opened = stored.split('/');
    }
    for (let i = 0; i < this.opened.length; i++) {
        if (this.menuElements[this.opened[i]]) {
            this.menuElements[this.opened[i]].classList.remove('closed');
        }
    }
    // load dir content (only after init)
    if (!this.contentLoaded) {
        this.loadContent();
        this.contentLoaded = true;
    } else if (this.path && this.menuElements[this.path]) {
        this.menuElements[this.path].classList.add('active');
    }
    // open all sub menu
    const splitted = this.path.split('/');
    let p = '';
    for (let i = 0; i < splitted.length; i++) {
        p += splitted[i] + '/';
        if (splitted[i] && p != this.path) {
            this.openTree(p);
        }
    }
};
FileBrowser.prototype.getTreeDirs = function (dirs, menuEle, flatTree, relativePath, level) {
    for (let i = 0; i < dirs.length; i++) {
        const dirRelativePath = relativePath + dirs[i].dirName + '/';
        flatTree.push({ path: dirRelativePath, name: dirs[i].dirName, level: level });
        const liEle = document.createElement('li');
        liEle.setAttribute('class', 'closed');
        let btnEle;
        if (dirs[i].sub_dirs.length > 0) {
            btnEle = document.createElement('button');
            btnEle.setAttribute('type', 'button');
            btnEle.setAttribute('class', 'list-entry');
            btnEle.addEventListener('click', { obj: this, dirName: dirs[i].dirName, relativePath: dirRelativePath }, function (evt) {
                evt.data.obj.toggle(evt.data.relativePath);
            });
        } else {
            btnEle = $('<button type="button" class="list-none"></button>');
        }
        liEle.appendChild(btnEle);
        liEle.appendChild('<a href="#' + dirRelativePath + '">' + dirs[i].dirName + '</a>');
        if (dirs[i].sub_dirs.length > 0) {
            const subEle = document.createElement('ul');
            subEle.setAttribute('class', 'sub-menu');
            this.getTreeDirs(dirs[i].sub_dirs, subEle, flatTree, dirRelativePath, level + 1);
            liEle.appendChild(subEle);
        }
        this.menuElements[dirRelativePath] = liEle;
        menuEle.appendChild(liEle);
    }
};

FileBrowser.prototype.loadContent = function () {
    const hash = window.location.hash.toString();
    let path = hash;
    if (hash && hash[0] == '#') {
        path = hash.substring(1);
    }
    if (path && path[path.length - 1] != '/') {
        path += '/';
    }
    this.path = path;
    if (path) {
        this.openTree(path);
    }
    //console.log('New path: ' + path);

    const activeEle = this.menuTreeElement.querySelector('.active');
    if (activeEle) {
        activeEle.classList.remove('active');
    }
    if (!path) {
        this.menuRootElement.classList.add('active');
    } else if (this.menuElements[path]) {
        this.menuElements[path].classList.add('active');
    }

    const obj = this;
    this.httpRequest({
        method: 'GET',
        url: this.contentURL,
        params: { path: path, order: this.ordering },
        callback: function (response) {
            obj.parseContentResponse(response);
        }
    });
};
FileBrowser.prototype.parseContentResponse = function (response) {
    if (!response.success) {
        this.placeElement.innerHTML = '<div class="message-error">' + response.message + '</div>';
        return;
    }

    if (response.files.length == 0) {
        this.placeElement.innerHTML = '<div class="message-info">' + jsu.translate('The folder is empty.') + '</div>';
    } else {
        // display files
        this.files = response.files;
        this.placeElement.innerHTML = '';
        const ovls = [];
        for (let i = 0; i < this.files.length; i++) {
            const file = this.files[i];
            let fclass;
            let target = '';
            if (file.isprevious) {
                fclass = 'previous';
                file.url = '#';
            } else if (file.isdir) {
                fclass = 'folder';
                file.url = '#' + this.path + file.name + '/';
            } else {
                fclass = 'file-' + file.ext;
                file.url = this.baseURL + this.path + file.name;
                target = 'target="_blank"';
            }
            let html = '<div class="file-block ' + fclass + '">';
            html += '<a class="file-link" ' + target + ' href="' + file.url + '">';
            html +=     '<span class="file-icon"';
            if (file.preview) {
                html +=     ' style="background-image: url(\'' + this.previewURL + '?path=' + this.path + file.name + '\');"';
            }
            html +=     '></span>';
            html +=     '<span class="file-name">' + file.name + '</span>';
            if (!file.isprevious) {
                html += '<span class="file-info">';
                html +=     '<span class="file-size">' + jsu.translate('Size:') + ' ' + file.sizeh + '</span>';
                if (!file.isdir) {
                    html += '<span class="file-mdate">' + jsu.translate('Last modification:') + '<br/>' + (file.mdate ? file.mdate : '?') + '</span>';
                } else {
                    html += '<span class="file-nb-files">' + jsu.translate('Files:') + ' ' + file.nb_files + '</span>';
                    html += '<span class="file-nb-dirs">' + jsu.translate('Folders:') + ' ' + file.nb_dirs + '</span>';
                }
                html += '</span>';
            }
            html += '</a>';
            if (!file.isprevious) {
                html += '<button type="button" class="file-delete" title="' + jsu.translate('Delete') + '"></button>';
                html += '<button type="button" class="file-rename" title="' + jsu.translate('Rename') + '"></button>';
                html += '<button type="button" class="file-move" title="' + jsu.translate('Move') + '"></button>';
            }
            html += '</div>';
            const $entry = $(html);
            file.$entry = $entry;
            $('.file-link', $entry).addEventListener('click', { obj: this, file: file }, function (evt) {
                return evt.data.obj.onFileClick(evt.data.file, evt);
            });
            $('.file-delete', $entry).addEventListener('click', { obj: this, file: file }, function (evt) {
                if (!evt.data.file.selected) {
                    evt.data.obj.onFileClick(evt.data.file, evt);
                }
                evt.data.obj.deleteFiles();
            });
            $('.file-rename', $entry).addEventListener('click', { obj: this, file: file }, function (evt) {
                if (!evt.data.file.selected) {
                    evt.data.obj.onFileClick(evt.data.file, evt);
                }
                evt.data.obj.renameFiles();
            });
            $('.file-move', $entry).addEventListener('click', { obj: this, file: file }, function (evt) {
                if (!evt.data.file.selected) {
                    evt.data.obj.onFileClick(evt.data.file, evt);
                }
                evt.data.obj.moveFiles();
            });
            this.placeElement.appendChild($entry);
            if (this.imagesExtenstions.indexOf(file.ext) != -1) {
                file.overlayIndex = ovls.length;
                ovls.push(file.url);
            }
        }
        if (ovls.length > 0) {
            this.overlay.addEventListener('change', ovls);
        }
    }
    // create path tree
    let fullPath = '#';
    let htmlPath = '<a href="' + fullPath + '">' + jsu.translate('root') + '</a> <span>/</span> ';
    if (response.path) {
        const splitted = response.path.split('/');
        for (let i = 0; i < splitted.length; i++) {
            if (splitted[i]) {
                fullPath += splitted[i] + '/';
                htmlPath += '<a href="' + fullPath + '">' + splitted[i] + '</a> <span>/</span> ';
            }
        }
    }
    document.getElementById('path_bar').innerHTML = htmlPath;
    this.sizeElement.innerHTML = response.total_size;
    this.dirsCountElement.innerHTML = response.total_nb_dirs;
    this.filesCountElement.innerHTML = response.total_nb_files;
};

FileBrowser.prototype.refresh = function () {
    this.loadContent();
};
FileBrowser.prototype.changeOrdering = function (order) {
    this.ordering = order;
    this.loadContent();
    jsu.setCookie('browser-ordering', this.ordering);
};
FileBrowser.prototype.onFileClick = function (file, evt) {
    // file or dir
    if (file.clicked) {
        // open
        if (file.isprevious) {
            if (!this.path) {
                return false;
            }
            const splitted = this.path.split('/');
            if (splitted[splitted.length - 1] == '') {
                splitted.pop();
            }
            let newPath = '';
            if (splitted.length > 1) {
                splitted.pop();
                newPath = splitted.join('/') + '/';
            }
            window.location.hash = '#' + newPath;
        } else if (file.isdir) {
            return true; // use url in link
        } else {
            if (!isNaN(file.overlayIndex)) {
                this.overlay.go_to_index(file.overlayIndex);
                this.overlay.show();
            } else {
                return true; // use url in link
            }
        }
    } else {
        // mark as clicked
        file.clicked = true;
        if (file.timeoutId) {
            clearTimeout(file.timeoutId);
        }
        file.timeoutId = setTimeout(function () {
            file.clicked = false;
            delete file.timeoutId;
        }, 500);
        // select
        if (!file.isprevious) { 
            if (!evt.ctrlKey) {
                // deselect all other files when Ctrl is not pressed
                for (let i = 0; i < this.files.length; i++) {
                    const f = this.files[i];
                    if (f != file && f.selected) {
                        f.selected = false;
                        f.$entry.classList.remove('selected');
                    }
                }
                // select file
                if (!file.selected) {
                    file.selected = true;
                    file.$entry.classList.add('selected');
                } else {
                    file.selected = false;
                    file.$entry.classList.remove('selected');
                }
            } else {
                // toggle selection
                if (file.selected) {
                    file.selected = false;
                    file.$entry.classList.remove('selected');
                } else {
                    file.selected = true;
                    file.$entry.classList.add('selected');
                }
            }
        }
    }
    return false;
};

/* actions */
FileBrowser.prototype.executeAction = function (data, method, cb) {
    // show loading overlay
    this.overlay.show({
        title: ' ',
        html: '<div class="file-browser-overlay message-loading">' + jsu.translate('Loading') + '...</div>'
    });
    // execute request
    if (method == 'post') {
        data.csrfmiddlewaretoken = this.csrfToken;
    }
    const obj = this;
    $.ajax({
        type: method,
        url: this.actionURL,
        data: data,
        dataType: 'json',
        cache: false,
        success: function (response) {
            if (!response.success || response.message) {
                obj.onActionExecuted(response);
            }
            if (cb) {
                cb(response);
            }
        },
        error: function (jqXHR, textStatus, thrownError) {
            obj.onActionExecuted({
                success: false,
                message: textStatus + ' (' + (thrownError ? thrownError : jsu.translate('server unreachable')) + ')'
            });
        }
    });
};
FileBrowser.prototype.onActionExecuted = function (response) {
    this.overlay.show({
        title: ' ',
        html: '<div class="file-browser-overlay message-' + (response.success ? 'success' : 'error') + '">' + response.message + '</div>',
        buttons: [
            { label: jsu.translate('Ok'), close: true }
        ]
    });
    if (response.success) {
        this.refresh();
    }
};

FileBrowser.prototype.getSelectedFiles = function () {
    const selected = [];
    for (let i = 0; i < this.files.length; i++) {
        if (this.files[i].selected) {
            selected.push(this.files[i]);
        }
    }
    return selected;
};

FileBrowser.prototype.onFilesDrop = function (evt) {
    const files = evt.dataTransfer.files;
    const formData = new FormData();
    formData.append('action', 'upload');
    formData.append('path', this.path);
    formData.append('csrfmiddlewaretoken', this.csrfToken);
    for (let i = 0; i < files.length; i++) {
        formData.append('file_' + i, files[i]);
    }
    $('progress', this.dropZoneElement).setAttribute('value', 0).innerHTML = '0 %';
    const obj = this;
    $.ajax({
        url: this.actionURL,
        type: 'POST',
        data: formData,
        // options to tell JQuery not to process data or worry about content-type
        cache: false,
        contentType: false,
        processData: false,
        xhr: function () {
            // custom xhr
            const myXhr = $.ajaxSettings.xhr();
            if (myXhr.upload) { // check if upload property exists
                myXhr.upload.addEventListener('progress', function (evt) {
                    if (evt.lengthComputable) {
                        let progress = 0;
                        if (evt.total) {
                            progress = parseInt(100 * evt.loaded / evt.total, 10);
                        }
                        $('progress', obj.dropZoneElement).setAttribute('value', progress).innerHTML = progress + ' %';
                    }
                }, false); // for handling the progress of the upload
            }
            return myXhr;
        },
        success: function (response) {
            obj.dropZoneElement.setAttribute('class', '');
            obj.onActionExecuted(response);
        },
        error: function (jqXHR, textStatus, thrownError) {
            obj.dropZoneElement.setAttribute('class', '');
            obj.onActionExecuted({
                success: false,
                message: textStatus + ' (' + (thrownError ? thrownError : jsu.translate('server unreachable')) + ')'
            });
        }
    });
};
FileBrowser.prototype.addFolder = function () {
    if (!this.folderForm) {
        let html = '<form class="file-browser-overlay" action="." method="post" enctype="multipart/form-data">';
        html += '<input type="hidden" name="csrfmiddlewaretoken" value="' + this.csrfToken + '"/>';
        html += '<label for="new_folder_name">' + jsu.translate('New folder name:') + '</label>';
        html += ' <input id="new_folder_name" type="text" value=""/>';
        html += '</form>';
        this.folderForm = $(html);
        this.folderForm.submit({obj: this}, function (evt) {
            evt.data.obj._addFolder();
            return false;
        });
    }
    this.folderForm.setAttribute('action', this.actionURL + '#' + this.path);

    const obj = this;
    this.overlay.show({
        title: jsu.translate('Add a folder in') + ' "' + jsu.translate('root') + '/' + this.path + '"',
        html: this.folderForm,
        buttons: [
            { label: jsu.translate('Add'), callback: function () {
                obj._addFolder();
            } },
            { label: jsu.translate('Cancel'), close: true }
        ]
    });
    setTimeout(function () {
        document.getElementById('new_folder_name').focus();
    }, 20);
};
FileBrowser.prototype._addFolder = function () {
    const data = {
        action: 'addFolder',
        path: this.path,
        name: document.getElementById('new_folder_name').val()
    };
    this.folderForm.detach();
    this.executeAction(data, 'post');
};
FileBrowser.prototype.addFile = function () {
    if (!this.uploadForm) {
        let html = '<form class="file-browser-overlay" action="." method="post" enctype="multipart/form-data">';
        html += '<input type="hidden" name="csrfmiddlewaretoken" value="' + this.csrfToken + '"/>';
        html += '<input type="hidden" name="action" value="upload-old"/>';
        html += '<input id="file_to_add_path" type="hidden" name="path" value=""/>';
        html += '<label for="file_to_add">' + jsu.translate('File to add:') + '</label>';
        html += ' <input id="file_to_add" type="file" name="file"/>';
        html += '</form>';
        this.uploadForm = $(html);
    }
    this.uploadForm.setAttribute('action', this.actionURL + '#' + this.path);
    this.uploadForm.querySelector('#file_to_add_path').val(this.path);

    const obj = this;
    this.overlay.show({
        title: jsu.translate('Add a file in') + ' "' + jsu.translate('root') + '/' + this.path + '"',
        html: this.uploadForm,
        buttons: [
            { label: jsu.translate('Add'), callback: function () {
                obj.uploadForm.submit();
            } },
            { label: jsu.translate('Cancel'), close: true }
        ]
    });
    setTimeout(function () {
        obj.uploadForm.querySelector('#file_to_add').focus();
    }, 20);
};
FileBrowser.prototype.renameFiles = function () {
    let html;
    if (!this.renameForm) {
        html = '<form class="file-browser-overlay" action="' + this.actionURL + '" method="post">';
        html += '<input type="hidden" name="csrfmiddlewaretoken" value="' + this.csrfToken + '"/>';
        html += '<div>';
        html += '<label for="rename_new_name">' + jsu.translate('New name:') + '</label>';
        html += ' <input id="rename_new_name" type="text" value=""/>';
        html += '</div>';
        html += '<p>' + jsu.translate('Selected file(s):') + '</p>';
        html += '<ul></ul>';
        html += '</form>';
        this.renameForm = $(html);
        const obj = this;
        this.renameForm.submit(function () {
            const data = {
                action: 'rename',
                path: obj.path,
                new_name: $('#rename_new_name', obj.renameForm).val()
            };
            const selected = obj.getSelectedFiles();
            for (let i = 0; i < selected.length; i++) {
                data['name_' + i] = selected[i].name;
            }
            obj.renameForm.detach();
            obj.executeAction(data, 'post');
            return false;
        });
    }

    const selected = this.getSelectedFiles();
    if (selected.length < 1) {
        return;
    }

    const title = jsu.translate('Rename') + ' "' + selected[0].name + '"';
    this.renameForm.querySelector('#rename_new_name').val(selected[0].name);

    html = '';
    for (let i = 0; i < selected.length; i++) {
        html += '<li>' + selected[i].name + '</li>';
    }
    $('ul', this.renameForm).innerHTML = html;

    const obj = this;
    this.overlay.show({
        title: title,
        html: this.renameForm,
        buttons: [
            { label: jsu.translate('Rename'), callback: function () {
                obj.renameForm.submit();
            } },
            { label: jsu.translate('Cancel'), close: true }
        ]
    });
    setTimeout(function () {
        obj.renameForm.querySelector('#rename_new_name').focus();
    }, 20);
};
FileBrowser.prototype.moveFiles = function () {
    const selected = this.getSelectedFiles();
    if (selected.length < 1) {
        return;
    }

    let title = jsu.translate('Move');
    if (selected.length == 1) {
        title += ' "' + selected[0].name + '"';
    } else {
        title += ' ' + selected.length + ' ' + jsu.translate('files');
    }

    const banned = [];
    for (let i = 0; i < selected.length; i++) {
        const s = selected[i];
        if (s.isdir) {
            banned.push(this.path + s.name + '/');
        }
    }

    let html = '<div class="file-browser-overlay">';
    html +=     '<label for="move_select">' + jsu.translate('Move to:') + '</label>';
    html +=     ' <select id="move_select">';
    html +=         '<option value="#" ' + (this.path ? '' : 'disabled="disabled"') + '>' + jsu.translate('root') + '</option>';
    for (let i=0; i < this.flatTree.length; i++) {
        let t = this.flatTree[i];
        let disabled = '';
        if (this.path == t.path) {
            disabled = 'disabled="disabled"';
        } else {
            // disallow a dir to be move in himself
            for (let j = 0; j < banned.length; j++) {
                if (t.path.indexOf(banned[j]) == 0) {
                    disabled = 'disabled="disabled"';
                    break;
                }
            }
        }
        html +=     '<option value="' + t.path + '" style="padding-left: ' + (t.level * 10) + 'px;" ' + disabled + '>' + t.name + '</option>';
    }
    html +=     '</select>';
    html +=     '<p>' + jsu.translate('Selected file(s):') + '</p>';
    html +=     '<ul>';
    for (let i=0; i < selected.length; i++) {
        html +=     '<li>' + selected[i].name + '</li>';
    }
    html +=     '</ul>';
    html += '</div>';
    const form = $(html);

    const obj = this;
    this.overlay.show({
        title: title,
        html: form,
        buttons: [
            { label: jsu.translate('Move'), callback: function () {
                const data = {
                    action: 'move',
                    path: obj.path,
                    newPath: form.querySelector('#move_select').val()
                };
                for (let i = 0; i < selected.length; i++) {
                    data['name_' + i] = selected[i].name;
                }
                obj.executeAction(data, 'post', function () {
                    // refresh dirs tree if a dir has been moved
                    if (banned.length > 0) {
                        obj.loadDirs();
                    }
                });
            } },
            { label: jsu.translate('Cancel'), close: true }
        ]
    });
    setTimeout(function () {
        form.querySelector('#move_select').focus();
    }, 20);
};
FileBrowser.prototype.deleteFiles = function () {
    const selected = this.getSelectedFiles();
    if (selected.length < 1) {
        return;
    }

    let title = jsu.translate('Delete');
    if (selected.length == 1) {
        title = ' ' + jsu.translate('one file');
    } else {
        title += ' ' + selected.length + ' ' + jsu.translate('files');
    }

    let html = '<div class="file-browser-overlay">';
    html +=     '<div><b>' + jsu.translate('Are you sure to delete the selected file(s) ?') + '</b></div>';
    html +=     '<p>' + jsu.translate('Selected file(s):') + '</p>';
    html +=     '<ul>';
    for (let i=0; i < selected.length; i++) {
        html +=     '<li>' + selected[i].name + '</li>';
    }
    html +=     '</ul>';
    html += '</div>';

    const obj = this;
    this.overlay.show({
        title: title,
        html: html,
        buttons: [
            { label: jsu.translate('Delete'), callback: function () {
                const data = {
                    action: 'delete',
                    path: obj.path
                };
                for (let i = 0; i < selected.length; i++) {
                    data['name_' + i] = selected[i].name;
                }
                obj.executeAction(data, 'post');
            } },
            { label: jsu.translate('Cancel'), close: true }
        ]
    });
};
FileBrowser.prototype.search = function () {
    if (!this.searchForm) {
        // prepare search form
        let html = '<form class="file-browser-overlay" action="' + this.actionURL + '" method="post">';
        html += '<input type="hidden" name="csrfmiddlewaretoken" value="' + this.csrfToken + '"/>';
        html += '<div>';
        html += '<input id="search" type="text" value=""/>';
        html += ' <label for="search_in_current">' + jsu.translate('Search only in current dir') + '</label>';
        html += ' <input id="search_in_current" type="checkbox"/>';
        html += '</div>';
        html += '<div id="search_results"></div>';
        html += '</form>';
        this.searchForm = $(html);
        const obj = this;
        this.searchForm.submit(function () {
            const data = {
                action: 'search',
                search: $('#search', obj.searchForm).val()
            };
            if ($('#search_in_current', obj.searchForm).is(':checked')) {
                data.path = obj.path;
            }
            obj.searchForm.detach();
            obj.executeAction(data, 'get', function (response) {
                // display search results
                let html = '<p><b>' + response.msg + '</b></p>';
                if (response.dirs && response.dirs.length > 0) {
                    html += '<div class="search-results">';
                    for (let i = 0; i < response.dirs.length; i++) {
                        const dir = response.dirs[i];
                        html += '<p><a class="dir-link" href="#' + dir.url + '">' + jsu.translate('root') + '/' + dir.url + '</a></p>';
                        html += '<ul>';
                        for (let j = 0; j < dir.files.length; j++) {
                            html += '<li><a href="' + obj.baseURL + dir.url + dir.files[j] + '">' + dir.url + dir.files[j] + '</a></li>';
                        }
                        html += '</ul>';
                    }
                    html += '</div>';
                }
                $('#search_results', obj.searchForm).innerHTML = html;
                $('#search_results a.dir-link', obj.searchForm).addEventListener('click', function () {
                    obj.overlay.hide();
                });
                obj.openSearchForm();
            });
            return false;
        });
    }
    this.openSearchForm();
};
FileBrowser.prototype.openSearchForm = function () {
    const obj = this;
    this.overlay.show({
        title: jsu.translate('Search'),
        html: this.searchForm,
        buttons: [
            { label: jsu.translate('Search'), callback: function () {
                obj.searchForm.submit();
            } },
            { label: jsu.translate('Cancel'), close: true }
        ]
    });
    setTimeout(function () {
        $('#search').focus();
    }, 20);
};

/* tree */
FileBrowser.prototype.toggle = function (path) {
    if (!this.menuElements[path]) {
        console.log('Error: no menu element for path: ' + path);
        return;
    }
    const $sub = this.menuElements[path];
    if ($sub.classList.contains('closed')) {
        this.openTree(path);
    } else {
        this.closeTree(path);
    }
};
FileBrowser.prototype.openTree = function (path) {
    if (!this.menuElements[path]) {
        console.log('Error: no menu element for path: ' + path);
        return;
    }
    const $sub = this.menuElements[path];
    if (!$sub.classList.contains('closed')) {
        return;
    }
    $sub.classList.remove('closed');
    this.opened.push(path);
    jsu.setCookie('browser-tree', this.opened.join('/'));
};
FileBrowser.prototype.closeTree = function (path) {
    if (!this.menuElements[path]) {
        console.log('Error: no menu element for path: ' + path);
        return;
    }
    const $sub = this.menuElements[path];
    if ($sub.classList.contains('closed')) {
        return;
    }
    $sub.classList.add('closed');
    for (let i = 0; i < this.opened.length; i++) {
        if (this.opened[i] == path) {
            if (i == this.opened.length - 1) {
                this.opened.pop();
            } else {
                const tmp = this.opened.pop();
                this.opened[i] = tmp;
            }
            jsu.setCookie('browser-tree', this.opened.join('/'));
            break;
        }
    }
};

FileBrowser.prototype.hideMessages = function () {
    $('.messages-list').fadeOut('fast');
    $('.messages-container').classList.add('hidden');
};
FileBrowser.prototype.showMessages = function () {
    $('.messages-list').fadeIn('fast');
    $('.messages-container').classList.remove('hidden');
};
