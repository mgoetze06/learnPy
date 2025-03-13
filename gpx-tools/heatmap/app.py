from flask import Flask, render_template, send_file, abort
import os

app = Flask(__name__)

@app.route('/')
def render_the_map():
    heatmap_filename = os.path.join("templates","heatmap.html")

    if os.path.exists(heatmap_filename):

        return render_template("heatmap.html")
    normalmap_filename = os.path.join("templates","map.html")

    if os.path.exists(normalmap_filename):

        return render_template("map.html")
    
    abort(404)


@app.route('/heatmap')
def render_map_as_image():
    if os.path.exists("heatmap.png"):
        filename = 'heatmap.png'
        return send_file(filename, mimetype='image/png')
    

    abort(404)
if __name__ == '__main__':
    app.run("0.0.0.0",debug=True)