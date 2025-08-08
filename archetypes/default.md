---
title: "{{ replace .Name "-" " " | title }}"
date: {{ .Date }}
draft: false
layout: "{{ replace .Name "s" ""}}"
header_img: 'img/{{.Name}}.jpg'
---