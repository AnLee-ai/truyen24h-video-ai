import sys

content = open('templates/app.js', 'r', encoding='utf-8').read()

old_audio_link = "const audioContent = c.audio_url ? `<a href=\"${c.audio_url}\" target=\"_blank\" style=\"text-decoration:none; color:inherit;\">${audioText} ↗</a>` : audioText;"
new_audio_link = "const isAudioLink = c.audio_url && (c.audio_url.startsWith('http') || c.audio_url.startsWith('/'));\n                    const audioContent = isAudioLink ? `<a href=\"${c.audio_url}\" target=\"_blank\" style=\"text-decoration:none; color:inherit;\">${audioText} ↗</a>` : audioText;"

old_video_link = "const videoContent = c.video_url ? `<a href=\"${c.video_url}\" target=\"_blank\" style=\"text-decoration:none; color:inherit;\">${videoText} ↗</a>` : videoText;"
new_video_link = "const isVideoLink = c.video_url && (c.video_url.startsWith('http') || c.video_url.startsWith('/'));\n                    const videoContent = isVideoLink ? `<a href=\"${c.video_url}\" target=\"_blank\" style=\"text-decoration:none; color:inherit;\">${videoText} ↗</a>` : videoText;"

content = content.replace(old_audio_link, new_audio_link)
content = content.replace(old_video_link, new_video_link)

# To force cache invalidation, let's also bust cache again?
# The user uses Render, so they'll need to push anyway.

open('templates/app.js', 'w', encoding='utf-8').write(content)
print('Patched templates/app.js')
