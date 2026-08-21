import sys, os

content = open('templates/index.html', 'r', encoding='utf-8').read()
content = content.replace('src="/static/app.js"', 'src="/static/app.js?v=' + str(os.urandom(4).hex()) + '"')
open('templates/index.html', 'w', encoding='utf-8').write(content)
print("Cache busted")
