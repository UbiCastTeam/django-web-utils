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
    let field;
    for (field in params) {
        urlParams.push(encodeURIComponent(field) + '=' + encodeURIComponent(params[field]));
    }
    if (urlParams.length > 0) {
        url += '?' + urlParams.join('&');
    }
    let formData;
    if (args.data instanceof FormData) {
        formData = args.data;
    } else if (args.data) {
        formData = new FormData();
        for (field in args.data) {
            formData.append(field, args.data[field]);
        }
    } else {
        formData = null;
    }
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
    req.send(formData);
    return req;
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
        const dirRelativePath = relativePath + dirs[i].dir_name + '/';
        flatTree.push({ path: dirRelativePath, name: dirs[i].dir_name, level: level });
        const liEle = document.createElement('li');
        liEle.setAttribute('class', 'closed');
        let btnEle;
        if (dirs[i].sub_dirs.length > 0) {
            btnEle = document.createElement('button');
            btnEle.setAttribute('type', 'button');
            btnEle.setAttribute('class', 'list-entry');
            btnEle.addEventListener('click', this.toggle.bind(this, dirRelativePath));
        } else {
            btnEle = document.createElement('button');
            btnEle.setAttribute('type', 'button');
            btnEle.setAttribute('class', 'list-none');
        }
        liEle.appendChild(btnEle);
        const linkEle = document.createElement('a');
        linkEle.setAttribute('href', '#' + dirRelativePath);
        linkEle.innerHTML = jsu.escapeHTML(dirs[i].dir_name);
        liEle.appendChild(linkEle);
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
            } else if (file.is_dir) {
                fclass = 'folder';
                file.url = '#' + this.path + file.name + '/';
            } else {
                fclass = 'file-' + file.ext;
                file.url = this.baseURL + this.path + file.name;
                target = 'target="_blank"';
            }
            const entryEle = document.createElement('div');
            entryEle.setAttribute('class', 'file-block ' + fclass);
            let html = '<a class="file-link" ' + target + ' href="' + file.url + '">';
            html += '<span class="file-icon"';
            if (file.preview) {
                html += ' style="background-image: url(\'' + this.previewURL + '?path=' + this.path + file.name + '\');"';
            }
            html += '></span>';
            html += '<span class="file-name">' + file.name + '</span>';
            if (!file.isprevious) {
                html += '<span class="file-info">';
                html += '<span class="file-size">' + jsu.translate('Size:') + ' ' + file.size_h + '</span>';
                if (!file.is_dir) {
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
            entryEle.innerHTML = html;
            file.entryEle = entryEle;
            entryEle.querySelector('.file-link').addEventListener('click', this.onFileClick.bind(this, file));
            entryEle.querySelector('.file-delete').addEventListener('click', this.deleteFiles.bind(this, file));
            entryEle.querySelector('.file-rename').addEventListener('click', this.renameFiles.bind(this, file));
            entryEle.querySelector('.file-move').addEventListener('click', this.moveFiles.bind(this, file));
            this.placeElement.appendChild(entryEle);
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
        } else if (file.is_dir) {
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
                        f.entryEle.classList.remove('selected');
                    }
                }
                // select file
                if (!file.selected) {
                    file.selected = true;
                    file.entryEle.classList.add('selected');
                } else {
                    file.selected = false;
                    file.entryEle.classList.remove('selected');
                }
            } else {
                // toggle selection
                if (file.selected) {
                    file.selected = false;
                    file.entryEle.classList.remove('selected');
                } else {
                    file.selected = true;
                    file.entryEle.classList.add('selected');
                }
            }
        }
    }
    return false;
};

/* actions */
FileBrowser.prototype.executeAction = function (method, params, data, cb) {
    // show loading overlay
    this.overlay.show({
        title: ' ',
        html: '<div class="file-browser-overlay message-loading">' + jsu.translate('Loading') + '...</div>'
    });
    // execute request
    const obj = this;
    this.httpRequest({
        method: method,
        url: this.actionURL,
        params: params,
        data: data,
        callback: function (response) {
            obj.onActionExecuted(response);
            if (cb) {
                cb(response);
            }
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
    formData.append('csrfmiddlewaretoken', this.csrfToken);
    formData.append('action', 'upload');
    formData.append('path', this.path);
    for (let i = 0; i < files.length; i++) {
        formData.append('file_' + i, files[i]);
    }
    $('progress', this.dropZoneElement).setAttribute('value', 0).innerHTML = '0 %';
    const obj = this;
    const req = this.httpRequest({
        method: 'POST',
        url: this.actionURL,
        data: formData,
        callback: function (response) {
            obj.dropZoneElement.setAttribute('class', '');
            obj.onActionExecuted(response);
        }
    });
    if (req.upload) { // check if upload property exists
        req.upload.addEventListener('progress', function (evt) {
            if (evt.lengthComputable) {
                let progress = 0;
                if (evt.total) {
                    progress = parseInt(100 * evt.loaded / evt.total, 10);
                }
                $('progress', obj.dropZoneElement).setAttribute('value', progress).innerHTML = progress + ' %';
            }
        }, false); // for handling the progress of the upload
    }
};
FileBrowser.prototype.addFolder = function () {
    if (!this.folderForm) {
        this.folderForm = document.createElement('form');
        this.folderForm.setAttribute('class', 'file-browser-overlay');
        this.folderForm.setAttribute('action', '.');
        this.folderForm.setAttribute('method', 'post');
        this.folderForm.setAttribute('enctype', 'multipart/form-data');
        this.folderForm.innerHTML = '<form class="file-browser-overlay" action="." method="post" enctype="multipart/form-data">' +
            '<input type="hidden" name="csrfmiddlewaretoken" value="' + this.csrfToken + '"/>' +
            '<label for="new_folder_name">' + jsu.translate('New folder name:') + '</label> ' +
            '<input id="new_folder_name" type="text" value=""/>';
        const obj = this;
        this.folderForm.addEventListener('submit', function (evt) {
            evt.preventDefault();
            const formData = new FormData(this);
            obj.folderForm.parentElement.removeChild(obj.folderForm);
            obj.executeAction('POST', null, formData);
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
                obj.folderForm.submit();
            } },
            { label: jsu.translate('Cancel'), close: true }
        ]
    });
    setTimeout(function () {
        document.getElementById('new_folder_name').focus();
    }, 20);
};
FileBrowser.prototype.addFile = function () {
    if (!this.uploadForm) {
        this.uploadForm = document.createElement('form');
        this.uploadForm.setAttribute('class', 'file-browser-overlay');
        this.uploadForm.setAttribute('action', '.');
        this.uploadForm.setAttribute('method', 'post');
        this.uploadForm.setAttribute('enctype', 'multipart/form-data');
        this.uploadForm.innerHTML = '<input type="hidden" name="csrfmiddlewaretoken" value="' + this.csrfToken + '"/>' +
            '<input type="hidden" name="action" value="upload-old"/>' +
            '<input id="file_to_add_path" type="hidden" name="path" value=""/>' +
            '<label for="file_to_add">' + jsu.translate('File to add:') + '</label> ' +
            '<input id="file_to_add" type="file" name="file"/>';
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
FileBrowser.prototype.renameFiles = function (file, evt) {
    if (file && !file.selected) {
        this.onFileClick(file, evt);
    }

    let html;
    if (!this.renameForm) {
        this.renameForm = document.createElement('form');
        this.renameForm.setAttribute('class', 'file-browser-overlay');
        this.renameForm.setAttribute('action', this.actionURL);
        this.renameForm.setAttribute('method', 'post');
        this.renameForm.setAttribute('enctype', 'multipart/form-data');
        this.renameForm.innerHTML = '<input type="hidden" name="csrfmiddlewaretoken" value="' + this.csrfToken + '"/>' +
            '<div>' +
            '<label for="rename_new_name">' + jsu.translate('New name:') + '</label>' +
            ' <input id="rename_new_name" type="text" value=""/>' +
            '</div>' +
            '<p>' + jsu.translate('Selected file(s):') + '</p>' +
            '<ul></ul>';
        const obj = this;
        this.renameForm.addEventListener('submit', function (evt) {
            evt.preventDefault();
            const formData = new FormData(this);
            const selected = obj.getSelectedFiles();
            for (let i = 0; i < selected.length; i++) {
                formData.append('name_' + i, selected[i].name);
            }
            obj.renameForm.parentElement.removeChild(obj.renameForm);
            obj.executeAction('POST', null, formData);
            return false;
        });
    }

    const selected = this.getSelectedFiles();
    if (selected.length < 1) {
        return;
    }

    const title = jsu.translate('Rename') + ' "' + selected[0].name + '"';
    this.renameForm.querySelector('#rename_new_name').value = selected[0].name;

    html = '';
    for (let i = 0; i < selected.length; i++) {
        html += '<li>' + selected[i].name + '</li>';
    }
    this.renameForm.querySelector('ul').innerHTML = html;

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
FileBrowser.prototype.moveFiles = function (file, evt) {
    if (file && !file.selected) {
        this.onFileClick(file, evt);
    }

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
        if (s.is_dir) {
            banned.push(this.path + s.name + '/');
        }
    }

    let html = '<div class="file-browser-overlay">';
    html += '<label for="move_select">' + jsu.translate('Move to:') + '</label>';
    html += ' <select id="move_select">';
    html += '<option value="#" ' + (this.path ? '' : 'disabled="disabled"') + '>' + jsu.translate('root') + '</option>';
    for (let i = 0; i < this.flatTree.length; i++) {
        const t = this.flatTree[i];
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
        html += '<option value="' + t.path + '" style="padding-left: ' + (t.level * 10) + 'px;" ' + disabled + '>' + t.name + '</option>';
    }
    html += '</select>';
    html += '<p>' + jsu.translate('Selected file(s):') + '</p>';
    html += '<ul>';
    for (let i = 0; i < selected.length; i++) {
        html += '<li>' + selected[i].name + '</li>';
    }
    html += '</ul>';
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
                obj.executeAction('POST', null, data, function (response) {
                    // refresh dirs tree if a dir has been moved
                    if (response.success && banned.length > 0) {
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
FileBrowser.prototype.deleteFiles = function (file, evt) {
    if (file && !file.selected) {
        this.onFileClick(file, evt);
    }

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
    html += '<div><b>' + jsu.translate('Are you sure to delete the selected file(s) ?') + '</b></div>';
    html += '<p>' + jsu.translate('Selected file(s):') + '</p>';
    html += '<ul>';
    for (let i = 0; i < selected.length; i++) {
        html += '<li>' + selected[i].name + '</li>';
    }
    html += '</ul>';
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
                obj.executeAction('POST', null, data);
            } },
            { label: jsu.translate('Cancel'), close: true }
        ]
    });
};
FileBrowser.prototype.search = function () {
    if (!this.searchForm) {
        // prepare search form
        this.searchForm = document.createElement('form');
        this.searchForm.setAttribute('class', 'file-browser-overlay');
        this.searchForm.setAttribute('action', this.actionURL);
        this.searchForm.setAttribute('method', 'get');
        this.searchForm.innerHTML = '<div>' +
            '<input id="search" type="text" value=""/>' +
            ' <label for="search_in_current">' + jsu.translate('Search only in current dir') + '</label>' +
            ' <input id="search_in_current" type="checkbox"/>' +
            '</div>' +
            '<div id="search_results"></div>';
        const obj = this;
        this.searchForm.addEventListener('submit', function (evt) {
            evt.preventDefault();
            const params = {
                action: 'search',
                search: $('#search', obj.searchForm).val()
            };
            if ($('#search_in_current', obj.searchForm).is(':checked')) {
                params.path = obj.path;
            }
            obj.searchForm.detach();
            obj.executeAction('GET', params, null, function (response) {
                if (!response.success) {
                    return;
                }
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
                $('#search_results a.dir-link', obj.searchForm).addEventListener('click', obj.overlay.hide);
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
        obj.searchForm.querySelector('#search').focus();
    }, 20);
};

/* tree */
FileBrowser.prototype.toggle = function (path) {
    if (!this.menuElements[path]) {
        console.log('Error: no menu element for path: ' + path);
        return;
    }
    const subEle = this.menuElements[path];
    if (subEle.classList.contains('closed')) {
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
    const subEle = this.menuElements[path];
    if (!subEle.classList.contains('closed')) {
        return;
    }
    subEle.classList.remove('closed');
    this.opened.push(path);
    jsu.setCookie('browser-tree', this.opened.join('/'));
};
FileBrowser.prototype.closeTree = function (path) {
    if (!this.menuElements[path]) {
        console.log('Error: no menu element for path: ' + path);
        return;
    }
    const subEle = this.menuElements[path];
    if (subEle.classList.contains('closed')) {
        return;
    }
    subEle.classList.add('closed');
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
