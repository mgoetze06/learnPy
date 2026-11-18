import pydeck as pdk
import os

def handleInputFile(filename):
    if not filename:
        filename = "hexagon_layer.html"
    if not filename.endswith(".html"):
        filename += ".html"
    return filename

def extract_gpx_points(gpx_file: str, year_filter: set[str] | None = None) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    current_point: tuple[float, float] | None = None

    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    text = None

    for encoding in encodings:
        try:
            with open(gpx_file, 'r', encoding=encoding) as file:
                text = file.read()
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        print('Skipping {} because it could not be decoded'.format(gpx_file))
        return points

    for line in text.splitlines():
        if '<trkpt' in line:
            parts = line.split('"')
            if len(parts) >= 4:
                try:
                    lat = float(parts[1])
                    lon = float(parts[3])
                    current_point = (lat, lon)
                except ValueError:
                    current_point = None
            else:
                current_point = None
        elif current_point is not None and '<time' in line:
            if year_filter is None:
                points.append(current_point)
            else:
                year = line.split('>')[1][:4]
                if year in year_filter:
                    points.append(current_point)
            current_point = None

    return points

def convertGPXtoCSV(gpx):
        #lng,lat
        #-0.198465,51.505538
        #-0.178838,51.491836
        #-0.205590,51.514910
        #-0.208327,51.514952
        #-0.206022,51.496572
        #-0.193610,51.500788
    csv = "lng,lat\n"
    for gpx_file in gpx:
        gpx_data = extract_gpx_points(gpx_file)
        for lat, lon in gpx_data:
            csv += f"{lon},{lat}\n"
    return csv

def createHexagonMap(folder_gpx,filename):
    """Create a hexagon map using pydeck."""


    filename = handleInputFile(filename)
    listOfGPXFiles = [f for f in os.listdir(folder_gpx) if f.endswith(".gpx")]
    csvData = convertGPXtoCSV(listOfGPXFiles)

    #DATA_URL = (
    #    "https://raw.githubusercontent.com/visgl/deck.gl-data/master/"
    #    "examples/3d-heatmap/heatmap-data.csv"
    #)

    layer = pdk.Layer(
        "HexagonLayer",
        csvData,
        get_position=["lng", "lat"],
        radius=1000,
        elevation_scale=50,
        elevation_range=[0, 3000],
        extruded=True,
        coverage=1,
        pickable=True,
        auto_highlight=True,
    )

    view_state = pdk.ViewState(
        longitude=-1.415,
        latitude=52.2323,
        zoom=6,
        min_zoom=5,
        max_zoom=15,
        pitch=40.5,
        bearing=-27.36,
    )

    r = pdk.Deck(layers=[layer], initial_view_state=view_state)
    r.to_html(filename)

if __name__ == "__main__":
    createHexagonMap("c:\\projects\\learnPy\\gpx-tools\\hexagons\\gpx", "c:\\projects\\learnPy\\gpx-tools\\hexagons\\hexagon_layer.html")