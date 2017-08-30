#!/bin/bash

# needed for 'pass' clip command
X_SELECTION="clipboard"
CLIP_TIME=45
LS="ls"
CP="-c"
SH="show"
_RADIUS_PYTHON="/mods-config/python/"
_CONF="/.config/epiphyte/env"

function get-config()
{
    source $HOME/$_CONF
    cat ${NETCONF}network.json
}


function load-all-users()
{
    get-config | grep "[a-z][a-z][a-z][a-z]\." | grep -v "=" | sed "s/\"//g;s/ //g" | cut -d ":" -f 1
}

# from 'pass' -> minus kde
function clip()
{
	local sleep_argv0="sleep on display $DISPLAY"
	pkill -f "^$sleep_argv0" 2>/dev/null && sleep 0.5
	local before="$(xclip -o -selection "X_SELECTION" 2>/dev/null | base64)"
	echo -n "$1" | xclip -selection "$X_SELECTION" || die "Error: Could not copy data to the clipboard"
	(
		( exec -a "$sleep_argv0" sleep "$CLIP_TIME" )
		local now="$(xclip -o -selection "$X_SELECTION" | base64)"
		[[ $now != $(echo -n "$1" | base64) ]] && before="$now"
		echo "$before" | base64 -d | xclip -selection "$X_SELECTION"
	) 2>/dev/null & disown
	echo "Copied $2 to clipboard. Will clear in $CLIP_TIME seconds."
}

function load-users()
{
    load-all-users | sort | uniq
}

function get-val()
{
    if [ -z "$1" ]; then
        echo "value required"
        exit -1
    fi
    load-users | grep -q "$1"
    if [ $? -eq 0 ]; then
        # NOTE: if JSON ever gets really long this GREP will fail so...let's not have a user name start that far down...
        source $HOME/$_CONF
        val=$(get-config | grep -A1000 "$1" | grep "\"pass\"" | head -n 1 | cut -d ":" -f 2 | sed "s/\"//g;s/,//g;s/ //g")
        val=$(PYTHONPATH="$PYTHONPATH:$FREERADIUS_REPO$_RADIUS_PYTHON" python $FREERADIUS_REPO${_RADIUS_PYTHON}utils/keying.py --oldkey $TEA_KEY --newkey "0:"$(pwgen 256 1) --password "$val" | grep "decrypted" | cut -d ":" -f 2)
        if [ -z $2 ]; then
            echo $val
        else
            clip $val $1
        fi
    else
        echo "invalid request for $1"
        exit -1
    fi

}

function get-users()
{
    for u in $(load-users); do
        echo $u
    done
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [ -z $1 ]; then
        echo "a subset of the 'pass' implentation ($CP $LS $SH)"
        exit -1
    fi

    case $1 in
        $LS)
            get-users
            ;;
        $SH | $CP)
            is_clip=""
            if [ "$1" == $CP ]; then
                is_clip=1
            fi
            get-val $2 $is_clip
    esac
fi
