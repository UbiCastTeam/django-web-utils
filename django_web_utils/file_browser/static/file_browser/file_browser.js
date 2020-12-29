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
        $('#fm_files_ordering').val(this.ordering);
    }
    this.loadDirs();
    // bind events
    $('#fm_btn_addFolder').click({ obj: this }, function (evt) {
        evt.data.obj.addFolder();
    });
    $('#fm_btn_addFile').click({ obj: this }, function (evt) {
        evt.data.obj.addFile();
    });
    $('#fm_btn_search').click({ obj: this }, function (evt) {
        evt.data.obj.search();
    });
    $('#fm_btn_refresh').click({ obj: this }, function (evt) {
        evt.data.obj.refresh();
    });
    $('#fm_files_ordering').change({ obj: this }, function (evt) {
        evt.data.obj.changeOrdering($(this).val());
    });
    $('.content-place').bind('dragenter', { obj: this }, function (evt) {
        evt.preventDefault();
        if (evt.data.obj.containsFiles(evt.originalEvent)) {
            evt.data.obj.dragEntered = true;
            setTimeout(function () { evt.data.dragEntered = false; }, 0);
            evt.data.obj.dropZoneElement.attr('class', 'hovered');
        }
    });
    $('.content-place').bind('dragover', { obj: this }, function (evt) {
        evt.preventDefault();
    });
    $('.content-place').bind('dragleave', { obj: this }, function (evt) {
        if (!evt.data.obj.dragEntered) {
            evt.data.obj.dropZoneElement.attr('class', '');
        }
        evt.data.obj.dragEntered = false;
    });
    $(document.body).bind('drop', { obj: this }, function (evt) {
        evt.preventDefault();
        if (evt.data.obj.containsFiles(evt.originalEvent)) {
            evt.data.obj.dropZoneElement.attr('class', 'uploading');
            evt.data.obj.onFilesDrop(evt.originalEvent);
            return false;
        }
    });
    const obj = this;
    $(window).bind('hashchange', function () {
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

FileBrowser.prototype.loadDirs = function () {
    const obj = this;
    $.ajax({
        type: 'GET',
        url: this.dirsURL,
        dataType: 'json',
        cache: false,
        success: function (response) {
            obj.parseDirsResponse(response);
        },
        error: function (jqXHR, textStatus, thrownError) {
            obj.parseDirsResponse({
                success: false,
                message: textStatus+' ('+(thrownError ? thrownError : jsu.translate('server unreachable'))+')'
            });
        }
    });
};
FileBrowser.prototype.parseDirsResponse = function (response) {
    if (!response.success) {
        this.placeElement.html('<div class="message-error">'+response.message+'</div>');
        return;
    }

    let flatTree = [];
    if (response.dirs) {
        let $menu = $('<ul></ul>');
        this.getTreeDirs(response.dirs, $menu, flatTree, '', 1);
        this.menuTreeElement.html($menu);
    }
    this.flatTree = flatTree; // used for move function
    // open trees
    let stored = jsu.getCookie('browser-tree');
    if (stored) {
        this.opened = stored.split('/');
    }
    for (let i=0; i < this.opened.length; i++) {
        if (this.menuElements[this.opened[i]]) {
            this.menuElements[this.opened[i]].removeClass('closed');
        }
    }
    // load dir content (only after init)
    if (!this.content_loaded) {
        this.loadContent();
        this.content_loaded = true;
    } else if (this.path && this.menuElements[this.path]) {
        this.menuElements[this.path].addClass('active');
    }
    // open all sub menu
    let splitted = this.path.split('/');
    let p = '';
    for (let i=0; i < splitted.length; i++) {
        p += splitted[i]+'/';
        if (splitted[i] && p != this.path) {
            this.openTree(p);
        }
    }
};
FileBrowser.prototype.getTreeDirs = function (dirs, $container, flatTree, relative_path, level) {
    for (let i=0; i < dirs.length; i++) {
        let dir_relative_path = relative_path+dirs[i].dir_name+'/';
        flatTree.push({ path: dir_relative_path, name: dirs[i].dir_name, level: level });
        let $li = $('<li class="closed"></li>');
        let $btn;
        if (dirs[i].sub_dirs.length > 0) {
            $btn = $('<button type="button" class="list-entry"></button>');
            $btn.click({ obj: this, dir_name: dirs[i].dir_name, relative_path: dir_relative_path }, function (evt) {
                evt.data.obj.toggle(evt.data.relative_path);
            });
        } else {
            $btn = $('<button type="button" class="list-none"></button>');
        }
        $li.append($btn);
        $li.append('<a href="#'+dir_relative_path+'">'+dirs[i].dir_name+'</a>');
        if (dirs[i].sub_dirs.length > 0) {
            let $sub_cont = $('<ul class="sub-menu"></ul>');
            this.getTreeDirs(dirs[i].sub_dirs, $sub_cont, flatTree, dir_relative_path, level+1);
            $li.append($sub_cont);
        }
        this.menuElements[dir_relative_path] = $li;
        $container.append($li);
    }
};

FileBrowser.prototype.loadContent = function () {
    let hash = window.location.hash.toString();
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
    //console.log('New path: '+path);

    $('.active', this.menuTreeElement).removeClass('active');
    if (!path) {
        this.menuRootElement.addClass('active');
    } else if (this.menuElements[path]) {
        this.menuElements[path].addClass('active');
    }

    const obj = this;
    $.ajax({
        type: 'GET',
        url: this.contentURL,
        data: { path: path, order: this.ordering },
        dataType: 'json',
        cache: false,
        success: function (response) {
            obj.parseContentResponse(response);
        },
        error: function (jqXHR, textStatus, thrownError) {
            obj.parseContentResponse({
                success: false,
                message: textStatus+' ('+(thrownError ? thrownError : jsu.translate('server unreachable'))+')'
            });
        }
    });
};
FileBrowser.prototype.parseContentResponse = function (response) {
    if (!response.success) {
        this.placeElement.html('<div class="message-error">'+response.message+'</div>');
        return;
    }

    if (response.files.length == 0) {
        this.placeElement.html('<div class="message-info">'+jsu.translate('The folder is empty.')+'</div>');
    } else {
        // display files
        this.files = response.files;
        this.placeElement.html('');
        let ovls = [];
        for (let i=0; i < this.files.length; i++) {
            let file = this.files[i];
            let fclass;
            let target = '';
            if (file.isprevious) {
                fclass = 'previous';
                file.url = '#';
            } else if (file.isdir) {
                fclass = 'folder';
                file.url = '#'+this.path+file.name+'/';
            } else {
                fclass = 'file-'+file.ext;
                file.url = this.baseURL+this.path+file.name;
                target = 'target="_blank"';
            }
            let html = '<div class="file-block '+fclass+'">';
            html += '<a class="file-link" '+target+' href="'+file.url+'">';
            html +=     '<span class="file-icon"';
            if (file.preview) {
                html +=     ' style="background-image: url(\''+this.previewURL+'?path='+this.path+file.name+'\');"';
            }
            html +=     '></span>';
            html +=     '<span class="file-name">'+file.name+'</span>';
            if (!file.isprevious) {
                html += '<span class="file-info">';
                html +=     '<span class="file-size">'+jsu.translate('Size:')+' '+file.sizeh+'</span>';
                if (!file.isdir) {
                    html += '<span class="file-mdate">'+jsu.translate('Last modification:')+'<br/>'+(file.mdate ? file.mdate : '?')+'</span>';
                } else {
                    html += '<span class="file-nb-files">'+jsu.translate('Files:')+' '+file.nb_files+'</span>';
                    html += '<span class="file-nb-dirs">'+jsu.translate('Folders:')+' '+file.nb_dirs+'</span>';
                }
                html += '</span>';
            }
            html += '</a>';
            if (!file.isprevious) {
                html += '<button type="button" class="file-delete" title="'+jsu.translate('Delete')+'"></button>';
                html += '<button type="button" class="file-rename" title="'+jsu.translate('Rename')+'"></button>';
                html += '<button type="button" class="file-move" title="'+jsu.translate('Move')+'"></button>';
            }
            html += '</div>';
            let $entry = $(html);
            file.$entry = $entry;
            $('.file-link', $entry).click({ obj: this, file: file }, function (evt) {
                return evt.data.obj.onFileClick(evt.data.file, evt);
            });
            $('.file-delete', $entry).click({ obj: this, file: file }, function (evt) {
                if (!evt.data.file.selected)
                    evt.data.obj.onFileClick(evt.data.file, evt);
                evt.data.obj.deleteFiles();
            });
            $('.file-rename', $entry).click({ obj: this, file: file }, function (evt) {
                if (!evt.data.file.selected)
                    evt.data.obj.onFileClick(evt.data.file, evt);
                evt.data.obj.renameFiles();
            });
            $('.file-move', $entry).click({ obj: this, file: file }, function (evt) {
                if (!evt.data.file.selected)
                    evt.data.obj.onFileClick(evt.data.file, evt);
                evt.data.obj.moveFiles();
            });
            this.placeElement.append($entry);
            if (this.imagesExtenstions.indexOf(file.ext) != -1) {
                file.overlay_index = ovls.length;
                ovls.push(file.url);
            }
        }
        if (ovls.length > 0) {
            this.overlay.change(ovls);
        }
    }
    // create path tree
    let full_path = '#';
    let html_path = '<a href="'+full_path+'">'+jsu.translate('root')+'</a> <span>/</span> ';
    if (response.path) {
        let splitted = response.path.split('/');
        for (let i=0; i < splitted.length; i++) {
            if (splitted[i]) {
                full_path += splitted[i]+'/';
                html_path += '<a href="'+full_path+'">'+splitted[i]+'</a> <span>/</span> ';
            }
        }
    }
    $('#path_bar').html(html_path);
    this.sizeElement.html(response.total_size);
    this.dirsCountElement.html(response.total_nb_dirs);
    this.filesCountElement.html(response.total_nb_files);
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
            let splitted = this.path.split('/');
            if (splitted[splitted.length - 1] == '') {
                splitted.pop();
            }
            let new_path = '';
            if (splitted.length > 1) {
                splitted.pop();
                new_path = splitted.join('/')+'/';
            }
            window.location.hash = '#'+new_path;
        } else if (file.isdir) {
            return true; // use url in link
        } else {
            if (!isNaN(file.overlay_index)) {
                this.overlay.go_to_index(file.overlay_index);
                this.overlay.show();
            } else {
                return true; // use url in link
            }
        }
    } else {
        // mark as clicked
        file.clicked = true;
        if (file.timeout_id) {
            clearTimeout(file.timeout_id);
        }
        file.timeout_id = setTimeout(function () {
            file.clicked = false;
            delete file.timeout_id;
        }, 500);
        // select
        if (!file.isprevious) { 
            if (!evt.ctrlKey) {
                // deselect all other files when Ctrl is not pressed
                for (let i=0; i < this.files.length; i++) {
                    let f = this.files[i];
                    if (f != file && f.selected) {
                        f.selected = false;
                        f.$entry.removeClass('selected');
                    }
                }
                // select file
                if (!file.selected) {
                    file.selected = true;
                    file.$entry.addClass('selected');
                } else {
                    file.selected = false;
                    file.$entry.removeClass('selected');
                }
            } else {
                // toggle selection
                if (file.selected) {
                    file.selected = false;
                    file.$entry.removeClass('selected');
                } else {
                    file.selected = true;
                    file.$entry.addClass('selected');
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
        html: '<div class="file-browser-overlay message-loading">'+jsu.translate('Loading')+'...</div>'
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
                message: textStatus+' ('+(thrownError ? thrownError : jsu.translate('server unreachable'))+')'
            });
        }
    });
};
FileBrowser.prototype.onActionExecuted = function (response) {
    this.overlay.show({
        title: ' ',
        html: '<div class="file-browser-overlay message-'+(response.success ? 'success' : 'error')+'">'+response.message+'</div>',
        buttons: [
            { label: jsu.translate('Ok'), close: true }
        ]
    });
    if (response.success) {
        this.refresh();
    }
};

FileBrowser.prototype.getSelectedFiles = function () {
    let selected = [];
    for (let i=0; i < this.files.length; i++) {
        if (this.files[i].selected) {
            selected.push(this.files[i]);
        }
    }
    return selected;
};

FileBrowser.prototype.onFilesDrop = function (evt) {
    let files = evt.dataTransfer.files;
    let form_data = new FormData();
    form_data.append('action', 'upload');
    form_data.append('path', this.path);
    form_data.append('csrfmiddlewaretoken', this.csrfToken);
    for (let i=0; i < files.length; i++) {
        form_data.append('file_'+i, files[i]);
    }
    $('progress', this.dropZoneElement).attr('value', 0).html('0 %');
    const obj = this;
    $.ajax({
        url: this.actionURL,
        type: 'POST',
        data: form_data,
        // options to tell JQuery not to process data or worry about content-type
        cache: false,
        contentType: false,
        processData: false,
        xhr: function () {  // custom xhr
            let myXhr = $.ajaxSettings.xhr();
            if (myXhr.upload) { // check if upload property exists
                myXhr.upload.addEventListener('progress', function (evt) {
                    if (evt.lengthComputable) {
                        let progress = 0;
                        if (evt.total) {
                            progress = parseInt(100 * evt.loaded / evt.total, 10);
                        }
                        $('progress', obj.dropZoneElement).attr('value', progress).html(progress+' %');
                    }
                }, false); // for handling the progress of the upload
            }
            return myXhr;
        },
        success: function (response) {
            obj.dropZoneElement.attr('class', '');
            obj.onActionExecuted(response);
        },
        error: function (jqXHR, textStatus, thrownError) {
            obj.dropZoneElement.attr('class', '');
            obj.onActionExecuted({
                success: false,
                message: textStatus+' ('+(thrownError ? thrownError : jsu.translate('server unreachable'))+')'
            });
        }
    });
};
FileBrowser.prototype.addFolder = function () {
    if (!this.folderForm) {
        let html = '<form class="file-browser-overlay" action="." method="post" enctype="multipart/form-data">';
        html += '<input type="hidden" name="csrfmiddlewaretoken" value="'+this.csrfToken+'"/>';
        html += '<label for="new_folder_name">'+jsu.translate('New folder name:')+'</label>';
        html += ' <input id="new_folder_name" type="text" value=""/>';
        html += '</form>';
        this.folderForm = $(html);
        this.folderForm.submit({obj: this}, function (evt) { evt.data.obj._addFolder(); return false; });
    }
    this.folderForm.attr('action', this.actionURL+'#'+this.path);

    const obj = this;
    this.overlay.show({
        title: jsu.translate('Add a folder in')+' "'+jsu.translate('root')+'/'+this.path+'"',
        html: this.folderForm,
        buttons: [
            { label: jsu.translate('Add'), callback: function () {
                obj._addFolder();
            } },
            { label: jsu.translate('Cancel'), close: true }
        ]
    });
    setTimeout(function () {
        $('#new_folder_name').focus();
    }, 20);
};
FileBrowser.prototype._addFolder = function () {
    const data = {
        action: 'addFolder',
        path: this.path,
        name: $('#new_folder_name', this.folderForm).val()
    };
    this.folderForm.detach();
    this.executeAction(data, 'post');
};
FileBrowser.prototype.addFile = function () {
    if (!this.uploadForm) {
        let html = '<form class="file-browser-overlay" action="." method="post" enctype="multipart/form-data">';
        html += '<input type="hidden" name="csrfmiddlewaretoken" value="'+this.csrfToken+'"/>';
        html += '<input type="hidden" name="action" value="upload-old"/>';
        html += '<input id="file_to_add_path" type="hidden" name="path" value=""/>';
        html += '<label for="file_to_add">'+jsu.translate('File to add:')+'</label>';
        html += ' <input id="file_to_add" type="file" name="file"/>';
        html += '</form>';
        this.uploadForm = $(html);
    }
    this.uploadForm.attr('action', this.actionURL+'#'+this.path);
    $('#file_to_add_path', this.uploadForm).val(this.path);

    const obj = this;
    this.overlay.show({
        title: jsu.translate('Add a file in')+' "'+jsu.translate('root')+'/'+this.path+'"',
        html: this.uploadForm,
        buttons: [
            { label: jsu.translate('Add'), callback: function () {
                obj.uploadForm.submit();
            } },
            { label: jsu.translate('Cancel'), close: true }
        ]
    });
    setTimeout(function () {
        $('#file_to_add').focus();
    }, 20);
};
FileBrowser.prototype.renameFiles = function () {
    let html;
    if (!this.rename_form) {
        html = '<form class="file-browser-overlay" action="'+this.actionURL+'" method="post">';
        html += '<input type="hidden" name="csrfmiddlewaretoken" value="'+this.csrfToken+'"/>';
        html += '<div>';
        html += '<label for="rename_new_name">'+jsu.translate('New name:')+'</label>';
        html += ' <input id="rename_new_name" type="text" value=""/>';
        html += '</div>';
        html += '<p>'+jsu.translate('Selected file(s):')+'</p>';
        html += '<ul></ul>';
        html += '</form>';
        this.rename_form = $(html);
        this.rename_form.submit({ obj: this }, function (evt) {
            const obj = evt.data.obj;
            let data = {
                action: 'rename',
                path: obj.path,
                new_name: $('#rename_new_name', obj.rename_form).val()
            };
            let selected = evt.data.obj.getSelectedFiles();
            for (let i=0; i < selected.length; i++) {
                data['name_'+i] = selected[i].name;
            }
            obj.rename_form.detach();
            obj.executeAction(data, 'post');
            return false;
        });
    }

    let selected = this.getSelectedFiles();
    if (selected.length < 1) {
        return;
    }

    let title = jsu.translate('Rename')+' "'+selected[0].name+'"';
    $('#rename_new_name', this.rename_form).val(selected[0].name);

    html = '';
    for (let i=0; i < selected.length; i++) {
        html += '<li>'+selected[i].name+'</li>';
    }
    $('ul', this.rename_form).html(html);

    const obj = this;
    this.overlay.show({
        title: title,
        html: this.rename_form,
        buttons: [
            { label: jsu.translate('Rename'), callback: function () {
                obj.rename_form.submit();
            } },
            { label: jsu.translate('Cancel'), close: true }
        ]
    });
    setTimeout(function () {
        $('#rename_new_name').focus();
    }, 20);
};
FileBrowser.prototype.moveFiles = function () {
    let selected = this.getSelectedFiles();
    if (selected.length < 1) {
        return;
    }

    let title = jsu.translate('Move');
    if (selected.length == 1) {
        title += ' "'+selected[0].name+'"';
    } else {
        title += ' '+selected.length+' '+jsu.translate('files');
    }

    let banned = [];
    for (let i=0; i < selected.length; i++) {
        let s = selected[i];
        if (s.isdir) {
            banned.push(this.path+s.name+'/');
        }
    }

    let html = '<div class="file-browser-overlay">';
    html +=     '<label for="move_select">'+jsu.translate('Move to:')+'</label>';
    html +=     ' <select id="move_select">';
    html +=         '<option value="#" '+(this.path ? '' : 'disabled="disabled"')+'>'+jsu.translate('root')+'</option>';
    for (let i=0; i < this.flatTree.length; i++) {
        let t = this.flatTree[i];
        let disabled = '';
        if (this.path == t.path) {
            disabled = 'disabled="disabled"';
        } else {
            // disallow a dir to be move in himself
            for (let j=0; j < banned.length; j++) {
                if (t.path.indexOf(banned[j]) == 0) {
                    disabled = 'disabled="disabled"';
                    break;
                }
            }
        }
        html +=     '<option value="'+t.path+'" style="padding-left: '+(t.level * 10)+'px;" '+disabled+'>'+t.name+'</option>';
    }
    html +=     '</select>';
    html +=     '<p>'+jsu.translate('Selected file(s):')+'</p>';
    html +=     '<ul>';
    for (let i=0; i < selected.length; i++) {
        html +=     '<li>'+selected[i].name+'</li>';
    }
    html +=     '</ul>';
    html += '</div>';
    let form = $(html);

    const obj = this;
    this.overlay.show({
        title: title,
        html: form,
        buttons: [
            { label: jsu.translate('Move'), callback: function () {
                let data = {
                    action: 'move',
                    path: obj.path,
                    new_path: $('#move_select', form).val()
                };
                for (let i=0; i < selected.length; i++) {
                    data['name_'+i] = selected[i].name;
                }
                obj.executeAction(data, 'post', function () {
                    // refresh dirs tree if a dir has been moved
                    if (banned.length > 0)
                        obj.loadDirs();
                });
            } },
            { label: jsu.translate('Cancel'), close: true }
        ]
    });
    setTimeout(function () {
        $('#move_select').focus();
    }, 20);
};
FileBrowser.prototype.deleteFiles = function () {
    let selected = this.getSelectedFiles();
    if (selected.length < 1) {
        return;
    }

    let title = jsu.translate('Delete');
    if (selected.length == 1) {
        title = ' '+jsu.translate('one file');
    } else {
        title += ' '+selected.length+' '+jsu.translate('files');
    }

    let html = '<div class="file-browser-overlay">';
    html +=     '<div><b>'+jsu.translate('Are you sure to delete the selected file(s) ?')+'</b></div>';
    html +=     '<p>'+jsu.translate('Selected file(s):')+'</p>';
    html +=     '<ul>';
    for (let i=0; i < selected.length; i++) {
        html +=     '<li>'+selected[i].name+'</li>';
    }
    html +=     '</ul>';
    html += '</div>';

    const obj = this;
    this.overlay.show({
        title: title,
        html: html,
        buttons: [
            { label: jsu.translate('Delete'), callback: function () {
                let data = {
                    action: 'delete',
                    path: obj.path
                };
                for (let i=0; i < selected.length; i++) {
                    data['name_'+i] = selected[i].name;
                }
                obj.executeAction(data, 'post');
            } },
            { label: jsu.translate('Cancel'), close: true }
        ]
    });
};
FileBrowser.prototype.search = function () {
    if (!this.search_form) {
        // prepare search form
        let html = '<form class="file-browser-overlay" action="'+this.actionURL+'" method="post">';
        html += '<input type="hidden" name="csrfmiddlewaretoken" value="'+this.csrfToken+'"/>';
        html += '<div>';
        html += '<input id="search" type="text" value=""/>';
        html += ' <label for="search_in_current">'+jsu.translate('Search only in current dir')+'</label>';
        html += ' <input id="search_in_current" type="checkbox"/>';
        html += '</div>';
        html += '<div id="search_results"></div>';
        html += '</form>';
        this.search_form = $(html);
        this.search_form.submit({ obj: this }, function (evt) {
            const obj = evt.data.obj;
            let data = {
                action: 'search',
                search: $('#search', obj.search_form).val()
            };
            if ($('#search_in_current', obj.search_form).is(':checked')) {
                data.path = obj.path;
            }
            obj.search_form.detach();
            obj.executeAction(data, 'get', function (response) {
                // display search results
                let html = '<p><b>'+response.msg+'</b></p>';
                if (response.dirs && response.dirs.length > 0) {
                    html += '<div class="search-results">';
                    for (let i=0; i < response.dirs.length; i++) {
                        let dir = response.dirs[i];
                        html += '<p><a class="dir-link" href="#'+dir.url+'">'+jsu.translate('root')+'/'+dir.url+'</a></p>';
                        html += '<ul>';
                        for (let j=0; j < dir.files.length; j++) {
                            html += '<li><a href="'+obj.baseURL+dir.url+dir.files[j]+'">'+dir.url+dir.files[j]+'</a></li>';
                        }
                        html += '</ul>';
                    }
                    html += '</div>';
                }
                $('#search_results', obj.search_form).html(html);
                $('#search_results a.dir-link', obj.search_form).click({ obj: obj }, function(evt) {
                    evt.data.obj.overlay.hide();
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
        html: this.search_form,
        buttons: [
            { label: jsu.translate('Search'), callback: function () {
                obj.search_form.submit();
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
        console.log('Error: no menu element for path: '+path);
        return;
    }
    let $sub = this.menuElements[path];
    if ($sub.hasClass('closed')) {
        this.openTree(path);
    } else {
        this.closeTree(path);
    }
};
FileBrowser.prototype.openTree = function (path) {
    if (!this.menuElements[path]) {
        console.log('Error: no menu element for path: '+path);
        return;
    }
    let $sub = this.menuElements[path];
    if (!$sub.hasClass('closed')) {
        return;
    }
    $sub.removeClass('closed');
    this.opened.push(path);
    jsu.setCookie('browser-tree', this.opened.join('/'));
};
FileBrowser.prototype.closeTree = function (path) {
    if (!this.menuElements[path]) {
        console.log('Error: no menu element for path: '+path);
        return;
    }
    let $sub = this.menuElements[path];
    if ($sub.hasClass('closed')) {
        return;
    }
    $sub.addClass('closed');
    for (let i=0; i < this.opened.length; i++) {
        if (this.opened[i] == path) {
            if (i == this.opened.length - 1) {
                this.opened.pop();
            } else {
                let tmp = this.opened.pop();
                this.opened[i] = tmp;
            }
            jsu.setCookie('browser-tree', this.opened.join('/'));
            break;
        }
    }
};

FileBrowser.prototype.hideMessages = function () {
    $('.messages-list').fadeOut('fast');
    $('.messages-container').addClass('hidden');
};
FileBrowser.prototype.showMessages = function () {
    $('.messages-list').fadeIn('fast');
    $('.messages-container').removeClass('hidden');
};
