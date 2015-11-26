/*******************************************
* File browser                             *
* Copyright: UbiCast, all rights reserved  *
* Author: Stephane Diemer                  *
*******************************************/

function FileBrowser(options) {
    // params
    this.base_url = "";
    this.dirs_url = "";
    this.content_url = "";
    this.preview_url = "";
    this.action_url = "";
    this.csrf_token = "";
    this.language = "en";
    
    // vars
    this.$tree = null;
    this.$buttons = null;
    this.$place = null;
    this.$total_size = null;
    this.$total_nb_dirs = null;
    this.$total_nb_files = null;
    this.$drop_zone = null;
    this.overlay = null;
    this.drag_entered = false;
    this.path = "";
    this.flat_tree = [];
    this.ordering = "name-asc";
    this.files = {};
    this.opened = [];
    this.menu_elements = {};
    this.images_extenstions = { png: true, gif: true, bmp: true, tiff: true, jpg: true, jpeg: true };
    
    utils.setup_class(this, options, [
        // allowed options
        "base_url",
        "dirs_url",
        "content_url",
        "preview_url",
        "action_url"
    ]);
    this.overlay = new OverlayDisplayManager({ language: this.language });
    
    var obj = this;
    $(document).ready(function () {
        obj.init();
    });
}

FileBrowser.prototype.init = function () {
    this.csrf_token = utils.get_cookie("csrftoken");
    // get elements
    this.$tree = $("#path_bar");
    this.$buttons = $(".buttons-bar");
    this.$menu = $(".menu-place .content-container");
    this.$menu_root = $(".menu-place #fm_root");
    this.$place = $("#fm_files_list");
    this.$total_size = $("#fm_total_size");
    this.$total_nb_dirs = $("#fm_total_nb_dirs");
    this.$total_nb_files = $("#fm_total_nb_files");
    this.$drop_zone = $("#fm_drop_zone");
    // load folder content
    this.ordering = utils.get_cookie("browser-ordering", this.ordering);
    if (this.ordering != "name-asc")
        $("#fm_files_ordering").val(this.ordering);
    this.load_dirs();
    // bind events
    $("#fm_btn_add_folder", this.$buttons).click({ obj: this }, function (evt) {
        evt.data.obj.add_folder();
    });
    $("#fm_btn_add_file", this.$buttons).click({ obj: this }, function (evt) {
        evt.data.obj.add_file();
    });
    $("#fm_btn_search").click({ obj: this }, function (evt) {
        evt.data.obj.search();
    });
    $("#fm_btn_refresh").click({ obj: this }, function (evt) {
        evt.data.obj.refresh();
    });
    $("#fm_files_ordering").change({ obj: this }, function (evt) {
        evt.data.obj.change_ordering($(this).val());
    });
    $(".content-place").bind("dragenter", { obj: this }, function (evt) {
        evt.preventDefault();
        if (evt.data.obj.contains_files(evt.originalEvent)) {
            evt.data.obj.drag_entered = true;
            setTimeout(function () { evt.data.drag_entered = false; }, 0);
            evt.data.obj.$drop_zone.attr("class", "hovered");
        }
    });
    $(".content-place").bind("dragover", { obj: this }, function (evt) {
        evt.preventDefault();
    });
    $(".content-place").bind("dragleave", { obj: this }, function (evt) {
        if (!evt.data.obj.drag_entered) {
            evt.data.obj.$drop_zone.attr("class", "");
        }
        evt.data.obj.drag_entered = false;
    });
    $(document.body).bind("drop", { obj: this }, function (evt) {
        evt.preventDefault();
        if (evt.data.obj.contains_files(evt.originalEvent)) {
            evt.data.obj.$drop_zone.attr("class", "uploading");
            evt.data.obj.on_files_drop(evt.originalEvent);
            return false;
        }
    });
    var obj = this;
    $(window).bind("hashchange", function () {
        obj.load_content();
    });
};

FileBrowser.prototype.contains_files = function (evt) {
    if (evt.dataTransfer.types) {
        for (var i = 0; i < evt.dataTransfer.types.length; i++) {
            if (evt.dataTransfer.types[i] == "Files")
                return true;
        }
    }
    return false;
};

FileBrowser.prototype.load_dirs = function () {
    var obj = this;
    $.ajax({
        type: "GET",
        url: this.dirs_url,
        dataType: "json",
        cache: false,
        success: function (response) {
            obj.parse_dirs_response(response);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            obj.parse_dirs_response({
                success: false,
                message: textStatus+" ("+(errorThrown ? errorThrown : obj.translate("server unreachable"))+")"
            });
        }
    });
};
FileBrowser.prototype.parse_dirs_response = function (response) {
    if (!response.success) {
        this.$place.html("<div class=\"message-error\">"+response.message+"</div>");
        return;
    }
    
    var flat_tree = [];
    if (response.dirs) {
        var $menu = $("<ul></ul>");
        this.get_tree_dirs(response.dirs, $menu, flat_tree, "", 1);
        $("#fm_dirs_tree", this.$menu).html($menu);
    }
    this.flat_tree = flat_tree; // used for move function
    // open trees
    var stored = utils.get_cookie("browser-tree");
    if (stored)
        this.opened = stored.split("'''");
    for (var i=0; i < this.opened.length; i++) {
        if (this.menu_elements[this.opened[i]])
            this.menu_elements[this.opened[i]].removeClass("closed");
    }
    // load dir content (only after init)
    if (!this.content_loaded) {
        this.load_content();
        this.content_loaded = true;
    }
    else {
        if (this.path) {
            if (this.menu_elements[this.path])
                this.menu_elements[this.path].addClass("active");
        }
    }
    // open all sub menu
    var splitted = this.path.split("/");
    var p = "";
    for (var i=0; i < splitted.length; i++) {
        p += splitted[i]+"/";
        if (splitted[i] && p != this.path)
            this.open_tree(p);
    }
};
FileBrowser.prototype.get_tree_dirs = function (dirs, $container, flat_tree, relative_path, level) {
    for (var i=0; i < dirs.length; i++) {
        var dir_relative_path = relative_path+dirs[i].dir_name+"/";
        flat_tree.push({ path: dir_relative_path, name: dirs[i].dir_name, level: level });
        var $li = $("<li class=\"closed\"></li>");
        var $span;
        if (dirs[i].sub_dirs.length > 0) {
            $span = $("<span class=\"list-entry\"></span>");
            $span.click({ obj: this, dir_name: dirs[i].dir_name, relative_path: dir_relative_path }, function (evt) {
                evt.data.obj.toggle(evt.data.relative_path);
            });
        }
        else
            $span = $("<span class=\"list-none\"></span>");
        $li.append($span);
        $li.append("<a href=\"#"+dir_relative_path+"\">"+dirs[i].dir_name+"</a>");
        if (dirs[i].sub_dirs.length > 0) {
            var $sub_cont = $("<ul class=\"sub-menu\"></ul>");
            this.get_tree_dirs(dirs[i].sub_dirs, $sub_cont, flat_tree, dir_relative_path, level+1);
            $li.append($sub_cont);
        }
        this.menu_elements[dir_relative_path] = $li;
        $container.append($li);
    }
};

FileBrowser.prototype.load_content = function () {
    var hash = window.location.hash.toString();
    var path = hash;
    if (hash && hash[0] == "#")
        path = hash.substring(1);
    if (path && path[path.length - 1] != "/")
        path += "/";
    this.path = path;
    if (path)
        this.open_tree(path);
    //console.log("New path: "+path);
    
    $(".active", this.$menu).removeClass("active");
    if (path) {
        if (this.menu_elements[path])
            this.menu_elements[path].addClass("active");
    }
    else {
        this.$menu_root.addClass("active");
    }
    
    var obj = this;
    $.ajax({
        type: "GET",
        url: this.content_url,
        data: { path: path, order: this.ordering },
        dataType: "json",
        cache: false,
        success: function (response) {
            obj.parse_content_response(response);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            obj.parse_content_response({
                success: false,
                message: textStatus+" ("+(errorThrown ? errorThrown : obj.translate("server unreachable"))+")"
            });
        }
    });
};
FileBrowser.prototype.parse_content_response = function (response) {
    if (!response.success) {
        this.$place.html("<div class=\"message-error\">"+response.message+"</div>");
        return;
    }
    
    if (response.files.length == 0) {
        this.$place.html("<div class=\"message-info\">"+this.translate("The folder is empty.")+"</div>");
    }
    else {
        // display files
        this.files = response.files;
        this.$place.html("");
        for (var i=0; i < this.files.length; i++) {
            var file = this.files[i];
            var fclass;
            var target = "";
            if (file.isprevious) {
                fclass = "previous";
                file.url = "#";
            }
            else if (file.isdir) {
                fclass = "folder";
                file.url = "#"+this.path+file.name+"/";
            }
            else {
                fclass = "file-"+file.ext;
                file.url = this.base_url+this.path+file.name;
                target = "target=\"_blank\"";
            }
            var html = "<div class=\"file-block "+fclass+"\">";
            html += "<a class=\"file-link\" "+target+" href=\""+file.url+"\">";
            html +=     "<span class=\"file-icon\"";
            if (file.preview)
                html +=     " style=\"background-image: url('"+this.preview_url+"?path="+this.path+file.name+"');\"";
            html +=     "></span>";
            html +=     "<span class=\"file-name\">"+file.name+"</span>";
            if (!file.isprevious) {
                html += "<span class=\"file-info\">";
                html +=     "<span class=\"file-size\">"+this.translate("Size:")+" "+file.sizeh+"</span>";
                if (!file.isdir)
                    html += "<span class=\"file-mdate\">"+this.translate("Last modification:")+"<br/>"+(file.mdate ? file.mdate : "?")+"</span>";
                else {
                    html += "<span class=\"file-nb-files\">"+this.translate("Files:")+" "+file.nb_files+"</span>";
                    html += "<span class=\"file-nb-dirs\">"+this.translate("Folders:")+" "+file.nb_dirs+"</span>";
                }
                html += "</span>";
            }
            html += "</a>";
            if (!file.isprevious) {
                html += "<span class=\"file-delete\" title=\""+this.translate("Delete")+"\"></span>";
                html += "<span class=\"file-rename\" title=\""+this.translate("Rename")+"\"></span>";
                html += "<span class=\"file-move\" title=\""+this.translate("Move")+"\"></span>";
            }
            html += "</div>";
            var $entry = $(html);
            file.$entry = $entry;
            $(".file-link", $entry).click({ obj: this, file: file }, function (evt) {
                return evt.data.obj.on_file_click(evt.data.file, evt);
            });
            $(".file-delete", $entry).click({ obj: this, file: file }, function (evt) {
                if (!evt.data.file.selected)
                    evt.data.obj.on_file_click(evt.data.file, evt);
                evt.data.obj.delete_files();
            });
            $(".file-rename", $entry).click({ obj: this, file: file }, function (evt) {
                if (!evt.data.file.selected)
                    evt.data.obj.on_file_click(evt.data.file, evt);
                evt.data.obj.rename_files();
            });
            $(".file-move", $entry).click({ obj: this, file: file }, function (evt) {
                if (!evt.data.file.selected)
                    evt.data.obj.on_file_click(evt.data.file, evt);
                evt.data.obj.move_files();
            });
            this.$place.append($entry);
        }
    }
    // create path tree
    var full_path = "#";
    var html_path = "<a href=\""+full_path+"\">"+this.translate("root")+"</a> <span>/</span> ";
    if (response.path) {
        var splitted = response.path.split("/");
        for (var i=0; i < splitted.length; i++) {
            if (splitted[i]) {
                full_path += splitted[i]+"/";
                html_path += "<a href=\""+full_path+"\">"+splitted[i]+"</a> <span>/</span> ";
            }
        }
    }
    this.$tree.html(html_path);
    this.$total_size.html(response.total_size);
    this.$total_nb_dirs.html(response.total_nb_dirs);
    this.$total_nb_files.html(response.total_nb_files);
};

FileBrowser.prototype.refresh = function () {
    this.load_content();
};
FileBrowser.prototype.change_ordering = function (order) {
    this.ordering = order;
    this.load_content();
    utils.set_cookie("browser-ordering", this.ordering);
};
FileBrowser.prototype.on_file_click = function (file, evt) {
    // file or dir
    if (file.clicked) {
        // open
        if (file.isprevious) {
            if (!this.path)
                return false;
            var splitted = this.path.split("/");
            if (splitted[splitted.length - 1] == "")
                splitted.pop();
            var new_path = "";
            if (splitted.length > 1) {
                splitted.pop();
                new_path = splitted.join("/")+"/";
            }
            window.location.hash = "#"+new_path;
        }
        else if (file.isdir) {
            return true; // use url in link
        }
        else {
            if (file.ext in this.images_extenstions)
                this.overlay.show(file.url);
            else
                return true; // use url in link
        }
    }
    else {
        // mark as clicked
        file.clicked = true;
        if (file.timeout_id)
            clearTimeout(file.timeout_id);
        file.timeout_id = setTimeout(function () {
            file.clicked = false;
            delete file.timeout_id;
        }, 500);
        // select
        if (!file.isprevious) { 
            if (!evt.ctrlKey) {
                // deselect all other files when Ctrl is not pressed
                for (var i=0; i < this.files.length; i++) {
                    var f = this.files[i];
                    if (f != file && f.selected) {
                        f.selected = false;
                        f.$entry.removeClass("selected");
                    }
                }
                // select file
                if (!file.selected) {
                    file.selected = true;
                    file.$entry.addClass("selected");
                }
                else {
                    file.selected = false;
                    file.$entry.removeClass("selected");
                }
            }
            else {
                // toggle selection
                if (file.selected) {
                    file.selected = false;
                    file.$entry.removeClass("selected");
                }
                else {
                    file.selected = true;
                    file.$entry.addClass("selected");
                }
            }
        }
    }
    return false;
};


/* actions */
FileBrowser.prototype.execute_action = function (data, cb) {
    // show loading overlay
    this.overlay.show({
        title: " ",
        html: "<div class=\"file-browser-overlay message-loading\">"+this.translate("Loading")+"...</div>"
    });
    // execute request
    data.csrfmiddlewaretoken = this.csrf_token;
    var obj = this;
    $.ajax({
        type: "POST",
        url: this.action_url,
        data: data,
        dataType: "json",
        cache: false,
        success: function (response) {
            if (!response.success || response.message)
                obj.on_action_executed(response);
            if (cb)
                cb(response);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            obj.on_action_executed({
                success: false,
                message: textStatus+" ("+(errorThrown ? errorThrown : obj.translate("server unreachable"))+")"
            });
        }
    });
};
FileBrowser.prototype.on_action_executed = function (response) {
    this.overlay.show({
        title: " ",
        html: "<div class=\"file-browser-overlay message-"+(response.success ? "success" : "error")+"\">"+response.message+"</div>",
        buttons: [
            { label: this.translate("Ok"), close: true }
        ]
    });
    if (response.success)
        this.refresh();
};

FileBrowser.prototype.get_selected_files = function () {
    var selected = [];
    for (var i=0; i < this.files.length; i++) {
        if (this.files[i].selected)
            selected.push(this.files[i]);
    }
    return selected;
};

FileBrowser.prototype.on_files_drop = function (evt) {
    var files = evt.dataTransfer.files;
    var form_data = new FormData();
    form_data.append("action", "upload");
    form_data.append("path", this.path);
    form_data.append("csrfmiddlewaretoken", this.csrf_token);
    for (var i=0; i < files.length; i++) {
        form_data.append("file_"+i, files[i]);
    }
    $("progress", this.$drop_zone).attr("value", 0).html("0 %");
    var obj = this;
    $.ajax({
        url: this.action_url,
        type: "POST",
        data: form_data,
        // options to tell JQuery not to process data or worry about content-type
        cache: false,
        contentType: false,
        processData: false,
        xhr: function () {  // custom xhr
            var myXhr = $.ajaxSettings.xhr();
            if (myXhr.upload) { // check if upload property exists
                myXhr.upload.addEventListener("progress", function (evt) {
                    if (evt.lengthComputable) {
                        var progress = 0;
                        if (evt.total)
                            progress = parseInt(100 * evt.loaded / evt.total, 10);
                        $("progress", obj.$drop_zone).attr("value", progress).html(progress+" %");
                    }
                }, false); // for handling the progress of the upload
            }
            return myXhr;
        },
        success: function (response) {
            obj.$drop_zone.attr("class", "");
            obj.on_action_executed(response);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            obj.$drop_zone.attr("class", "");
            obj.on_action_executed({
                success: false,
                message: textStatus+" ("+(errorThrown ? errorThrown : obj.translate("server unreachable"))+")"
            });
        }
    });
};
FileBrowser.prototype.add_folder = function () {
    if (!this.folder_form) {
        var html = "<form class=\"file-browser-overlay\" action=\".\" method=\"post\" enctype=\"multipart/form-data\">";
        html += "<input type=\"hidden\" name=\"csrfmiddlewaretoken\" value=\""+this.csrf_token+"\"/>";
        html += "<label for=\"new_folder_name\">"+this.translate("New folder name:")+"</label>";
        html += " <input id=\"new_folder_name\" type=\"text\" value=\"\"/>";
        html += "</form>";
        this.folder_form = $(html);
        this.folder_form.submit({obj: this}, function (evt) { evt.data.obj._add_folder(); return false; });
    }
    this.folder_form.attr("action", this.action_url+"#"+this.path);
    
    var obj = this;
    this.overlay.show({
        title: this.translate("Add a folder in")+" \""+this.translate("root")+"/"+this.path+"\"",
        html: this.folder_form,
        no_button_focus: true,
        buttons: [
            { label: this.translate("Add"), callback: function () {
                obj._add_folder();
            } },
            { label: this.translate("Cancel"), close: true }
        ]
    });
    setTimeout(function () {$("#new_folder_name").focus();}, 20);
};
FileBrowser.prototype._add_folder = function () {
    var data = {
        action: "add_folder",
        path: this.path,
        name: $("#new_folder_name", this.folder_form).val()
    };
    this.folder_form.detach();
    this.execute_action(data);
};
FileBrowser.prototype.add_file = function () {
    if (!this.upload_form) {
        var html = "<form class=\"file-browser-overlay\" action=\".\" method=\"post\" enctype=\"multipart/form-data\">";
        html += "<input type=\"hidden\" name=\"csrfmiddlewaretoken\" value=\""+this.csrf_token+"\"/>";
        html += "<input type=\"hidden\" name=\"action\" value=\"upload-old\"/>";
        html += "<input id=\"file_to_add_path\" type=\"hidden\" name=\"path\" value=\"\"/>";
        html += "<label for=\"file_to_add\">"+this.translate("File to add:")+"</label>";
        html += " <input id=\"file_to_add\" type=\"file\" name=\"file\"/>";
        html += "</form>";
        this.upload_form = $(html);
    }
    this.upload_form.attr("action", this.action_url+"#"+this.path);
    $("#file_to_add_path", this.upload_form).val(this.path);
    
    var obj = this;
    this.overlay.show({
        title: this.translate("Add a file in")+" \""+this.translate("root")+"/"+this.path+"\"",
        html: this.upload_form,
        no_button_focus: true,
        buttons: [
            { label: this.translate("Add"), callback: function () {
                obj.upload_form.submit();
            } },
            { label: this.translate("Cancel"), close: true }
        ]
    });
    setTimeout(function () {$("#file_to_add").focus();}, 20);
};
FileBrowser.prototype.rename_files = function () {
    var html;
    if (!this.rename_form) {
        html = "<form class=\"file-browser-overlay\" action=\""+this.action_url+"\" method=\"post\">";
        html += "<input type=\"hidden\" name=\"csrfmiddlewaretoken\" value=\""+this.csrf_token+"\"/>";
        html += "<div>";
        html += "<label for=\"rename_new_name\">"+this.translate("New name:")+"</label>";
        html += " <input id=\"rename_new_name\" type=\"text\" value=\"\"/>";
        html += "</div>";
        html += "<p>"+this.translate("Selected file(s):")+"</p>";
        html += "<ul></ul>";
        html += "</form>";
        this.rename_form = $(html);
        this.rename_form.submit({ obj: this }, function (evt) {
            var obj = evt.data.obj;
            var data = {
                action: "rename",
                path: obj.path,
                new_name: $("#rename_new_name", obj.rename_form).val()
            };
            var selected = evt.data.obj.get_selected_files();
            for (var i=0; i < selected.length; i++) {
                data["name_"+i] = selected[i].name;
            }
            obj.rename_form.detach();
            obj.execute_action(data);
            return false;
        });
    }

    var selected = this.get_selected_files();
    if (selected.length < 1)
        return;
    
    var title = this.translate("Rename")+" \""+selected[0].name+"\"";
    $("#rename_new_name", this.rename_form).val(selected[0].name);
    
    html = "";
    for (var i=0; i < selected.length; i++) {
        html += "<li>"+selected[i].name+"</li>";
    }
    $("ul", this.rename_form).html(html);
    
    var obj = this;
    this.overlay.show({
        title: title,
        html: this.rename_form,
        no_button_focus: true,
        buttons: [
            { label: this.translate("Rename"), callback: function () {
                obj.rename_form.submit();
            } },
            { label: this.translate("Cancel"), close: true }
        ]
    });
    setTimeout(function () {$("#rename_new_name").focus();}, 20);
};
FileBrowser.prototype.move_files = function () {
    var selected = this.get_selected_files();
    if (selected.length < 1)
        return;
    
    var title = this.translate("Move");
    if (selected.length == 1)
        title += " \""+selected[0].name+"\"";
    else
        title += " "+selected.length+" "+this.translate("files");
    
    var banned = [];
    for (var i=0; i < selected.length; i++) {
        var s = selected[i];
        if (s.isdir)
            banned.push(this.path+s.name+"/");
    }
    
    var html = "<div class=\"file-browser-overlay\">";
    html +=     "<label for=\"move_select\">"+this.translate("Move to:")+"</label>";
    html +=     " <select id=\"move_select\">";
    html +=         "<option value=\"#\" "+(this.path ? "" : "disabled=\"disabled\"")+">"+this.translate("root")+"</option>";
    for (var i=0; i < this.flat_tree.length; i++) {
        var t = this.flat_tree[i];
        var disabled = "";
        if (this.path == t.path)
            disabled = "disabled=\"disabled\"";
        else {
            // disallow a dir to be move in himself
            for (var j=0; j < banned.length; j++) {
                if (t.path.indexOf(banned[j]) == 0) {
                    disabled = "disabled=\"disabled\"";
                    break;
                }
            }
        }
        html +=     "<option value=\""+t.path+"\" style=\"padding-left: "+(t.level * 10)+"px;\" "+disabled+">"+t.name+"</option>";
    }
    html +=     "</select>";
    html +=     "<p>"+this.translate("Selected file(s):")+"</p>";
    html +=     "<ul>";
    for (var i=0; i < selected.length; i++) {
        html +=     "<li>"+selected[i].name+"</li>";
    }
    html +=     "</ul>";
    html += "</div>";
    var form = $(html);
    
    var obj = this;
    this.overlay.show({
        title: title,
        html: form,
        no_button_focus: true,
        buttons: [
            { label: this.translate("Move"), callback: function () {
                var data = {
                    action: "move",
                    path: obj.path,
                    new_path: $("#move_select", form).val()
                };
                for (var i=0; i < selected.length; i++) {
                    data["name_"+i] = selected[i].name;
                }
                obj.execute_action(data, function () {
                    // refresh dirs tree if a dir has been moved
                    if (banned.length > 0)
                        obj.load_dirs();
                });
            } },
            { label: this.translate("Cancel"), close: true }
        ]
    });
    setTimeout(function () {$("#move_select").focus();}, 20);
};
FileBrowser.prototype.delete_files = function () {
    var selected = this.get_selected_files();
    if (selected.length < 1)
        return;
    
    var title = this.translate("Delete");
    if (selected.length == 1)
        title = " "+this.translate("one file");
    else
        title += " "+selected.length+" "+this.translate("files");
    
    var html = "<div class=\"file-browser-overlay\">";
    html +=     "<div><b>"+this.translate("Are you sure to delete the selected file(s) ?")+"</b></div>";
    html +=     "<p>"+this.translate("Selected file(s):")+"</p>";
    html +=     "<ul>";
    for (var i=0; i < selected.length; i++) {
        html +=     "<li>"+selected[i].name+"</li>";
    }
    html +=     "</ul>";
    html += "</div>";
    
    var obj = this;
    this.overlay.show({
        title: title,
        html: html,
        no_button_focus: true,
        buttons: [
            { label: this.translate("Delete"), callback: function () {
                var data = {
                    action: "delete",
                    path: obj.path
                };
                for (var i=0; i < selected.length; i++) {
                    data["name_"+i] = selected[i].name;
                }
                obj.execute_action(data);
            } },
            { label: this.translate("Cancel"), close: true }
        ]
    });
};
FileBrowser.prototype.search = function () {
    if (!this.search_form) {
        // prepare search form
        var html = "<form class=\"file-browser-overlay\" action=\""+this.action_url+"\" method=\"post\">";
        html += "<input type=\"hidden\" name=\"csrfmiddlewaretoken\" value=\""+this.csrf_token+"\"/>";
        html += "<div>";
        html += "<input id=\"search\" type=\"text\" value=\"\"/>";
        html += " <label for=\"search_in_current\">"+this.translate("Search only in current dir")+"</label>";
        html += " <input id=\"search_in_current\" type=\"checkbox\"/>";
        html += "</div>";
        html += "<div id=\"search_results\"></div>";
        html += "</form>";
        this.search_form = $(html);
        this.search_form.submit({ obj: this }, function (evt) {
            var obj = evt.data.obj;
            var data = {
                action: "search",
                search: $("#search", obj.search_form).val()
            };
            if ($("#search_in_current", obj.search_form).is(":checked"))
                data.path = obj.path;
            obj.search_form.detach();
            obj.execute_action(data, function (response) {
                // display search results
                var html = "<p><b>"+response.msg+"</b></p>";
                if (response.dirs && response.dirs.length > 0) {
                    html += "<div class=\"search-results\">";
                    for (var i=0; i < response.dirs.length; i++) {
                        var dir = response.dirs[i];
                        html += "<p><a class=\"dir-link\" href=\"#"+dir.url+"\">"+obj.translate("root")+"/"+dir.url+"</a></p>";
                        html += "<ul>";
                        for (var j=0; j < dir.files.length; j++) {
                            html += "<li><a href=\""+obj.base_url+dir.url+dir.files[j]+"\">"+dir.url+dir.files[j]+"</a></li>";
                        }
                        html += "</ul>";
                    }
                    html += "</div>";
                }
                $("#search_results", obj.search_form).html(html);
                $("#search_results a.dir-link", obj.search_form).click({ obj: obj }, function(evt) {
                    evt.data.obj.overlay.hide();
                });
                obj.open_search_form();
            });
            return false;
        });
    }
    this.open_search_form();
};
FileBrowser.prototype.open_search_form = function () {
    var obj = this;
    this.overlay.show({
        title: this.translate("Search"),
        html: this.search_form,
        no_button_focus: true,
        buttons: [
            { label: this.translate("Search"), callback: function () {
                obj.search_form.submit();
            } },
            { label: this.translate("Cancel"), close: true }
        ]
    });
    setTimeout(function () {$("#search").focus();}, 20);
};


/* tree */
FileBrowser.prototype.toggle = function (path) {
    if (!this.menu_elements[path]) {
        console.log("Error: no menu element for path: "+path);
        return;
    }
    var $sub = this.menu_elements[path];
    if ($sub.hasClass("closed"))
        this.open_tree(path);
    else
        this.close_tree(path);
};
FileBrowser.prototype.open_tree = function (path) {
    if (!this.menu_elements[path]) {
        console.log("Error: no menu element for path: "+path);
        return;
    }
    var $sub = this.menu_elements[path];
    if (!$sub.hasClass("closed"))
        return;
    $sub.removeClass("closed");
    this.opened.push(path);
    utils.set_cookie("browser-tree", this.opened.join("'''"));
};
FileBrowser.prototype.close_tree = function (path) {
    if (!this.menu_elements[path]) {
        console.log("Error: no menu element for path: "+path);
        return;
    }
    var $sub = this.menu_elements[path];
    if ($sub.hasClass("closed"))
        return;
    $sub.addClass("closed");
    for (var i=0; i < this.opened.length; i++) {
        if (this.opened[i] == path) {
            if (i == this.opened.length - 1) {
                this.opened.pop();
            }
            else {
                var tmp = this.opened.pop();
                this.opened[i] = tmp;
            }
            utils.set_cookie("browser-tree", this.opened.join("'''"));
            break;
        }
    }
};


FileBrowser.prototype.hide_messages = function () {
    $(".messages-list").fadeOut("fast");
    $(".messages-container").addClass("hidden");
};
FileBrowser.prototype.show_messages = function () {
    $(".messages-list").fadeIn("fast");
    $(".messages-container").removeClass("hidden");
};
