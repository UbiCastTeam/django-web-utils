#!/bin/bash

if [[ $# > 0 ]]
then
    cd $1
fi

langs="en fr"
if [[ $# > 1 ]]
then
    langs="$langs $2"
fi


function maketranslations {
    for j in $langs; do
        echo -e "Generating messages: $j"
        django-admin.py makemessages -l $j -e html,txt,xml
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
        echo -e "Generating translations for path: $dir"
        cd $dir
        maketranslations
        cd ..
        echo ""
        found=true
    fi
done
if [[ $found == false ]]; then
    maketranslations
fi

