# import required module
import os
import vlc

# play sound
file = os.path.join("26","26.mp3")
print('playing sound using native player')
os.system("mpg123 " + file)


#song = AudioSegment.from_mp3(file)
#play(song)