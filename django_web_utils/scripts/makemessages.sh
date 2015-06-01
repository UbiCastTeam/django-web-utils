#!/bin/bash

if [[ $# > 0 ]]; then
    cd $1
fi

langs="en fr"
if [[ $# > 1 ]]; then
    if [[ $2 == "en" || $2 == "fr" ]]; then
        langs="$2"
    else
        langs="$langs $2"
    fi
fi


function maketranslations {
    for j in $langs; do
        echo -e "Generating messages: $j"
        django-admin.py makemessages -l $j -e py,html,xml
        retcode=$?
        if [[ $retcode != 0 ]]; then
            echo -e "Command exited with code $retcode."
            exit $retcode
        fi
        #echo -e "Generating messages for javascript"
        #django-admin.py makemessages -d djangojs -l $j
    done
}


found=false
for i in *; do
    dir=${i}
    locale="$dir/locale"
    if [ -d $locale ]; then
        echo -e "\033[94mGenerating translations for path: $dir\033[0m"
        cd $dir
        maketranslations
        cd -
        echo ""
        found=true
    fi
done
if [[ $found == false ]]; then
    maketranslations
fi

