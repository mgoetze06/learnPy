import glob,shutil,os
dest_dir = "/home/boris/projects/gpx-heatmap/heatmap/gpx"
src_dir = "/mnt/homeassistant/www/gpx/"
for file in glob.glob(src_dir+r'*.gpx'):
    print("copying file from homeassistant: ",file)

    newfile = file.split(src_dir)[1]

    newfile = os.path.join(dest_dir,newfile)

    shutil.copyfile(file, newfile)