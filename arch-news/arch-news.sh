#!/bin/bash

arch-news-browser() {
	elinks -dump -dump-color-mode 1 -dump-width $1 -no-numbering -no-references
}

arch-news-get() {
    curl -s "https://www.archlinux.org/news/" | pup "#article-list"
}

arch-news-list() {
	COLS=$(tput cols)
    arch-news-get | \
    pup "tbody" | \
    arch-news-browser $COLS | \
    sed 's|\( \)*$||' | \
    head -n${1:-10} | \
    awk '{printf("%2d%s\n",NR,$0);}'
}

arch-news-read() {
	COLS=$(tput cols)
	LIST=$(arch-news-get)
	for i in $@; do
		echo $LIST | \
		pup "a attr{href}" | \
		sed -n $i"p" | \
		sed "s|^|https://www.archlinux.org/|" | \
		xargs curl -s | \
		pup ".news-article" | \
		sed "1i<hr/>" | \
		arch-news-browser $COLS
	done
}

arch-news-recent() {
    curl -s https://www.archlinux.org/  | pup "#news > :not(.newslist)" | arch-news-browser
}
