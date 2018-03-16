import json
import base64
from io import BytesIO

from matplotlib.image import imsave

from .colors import color_ramps
import geojson
from colour import Color


def row_to_geojson(row, lon, lat):
    """Convert a pandas dataframe row to a geojson format object.  Converts all datetimes to epoch seconds.
    """

    # Let pandas handle json serialization
    row_json = json.loads(row.to_json(date_format='epoch', date_unit='s'))
    return geojson.Feature(geometry=geojson.Point((row_json[lon], row_json[lat])),
                           properties={key: row_json[key] for key in row_json.keys() if key not in [lon, lat]})


def df_to_geojson(df, properties=None, lat='lat', lon='lon', precision=None, filename=None):
    """Serialize a Pandas dataframe to a geojson format Python dictionary
    """
    if precision:
        df[lon] = df[lon].round(precision)
        df[lat] = df[lat].round(precision)

    if not properties:
        # if no properties are selected, use all properties in dataframe
        properties = [c for c in df.columns if c not in [lon, lat]]

    for prop in properties:
        # Check if list of properties exists in dataframe columns
        if prop not in list(df.columns):
            raise ValueError(
                'properties must be a valid list of column names from dataframe')
        if prop in [lon, lat]:
            raise ValueError(
                'properties cannot be the geometry longitude or latitude column')

    if filename:
        with open(filename, 'w+') as f:
            # Overwrite file if it already exists
            pass

        with open(filename, 'a+') as f:
            features = []
            df[[lon, lat] + properties].apply(lambda x: features.append(
                row_to_geojson(x, lon, lat)), axis=1)

            f.write('{"type": "FeatureCollection", "features": [\n')
            for idx, feat in enumerate(features):
                if idx == 0:
                    f.write(geojson.dumps(feat) + '\n')
                else:
                    f.write(',' + geojson.dumps(feat) + '\n')
            f.write(']}')

            return {
                "type": "file",
                "filename": filename,
                "feature_count": len(features)
            }
    else:
        features = []
        df[[lon, lat] + properties].apply(lambda x: features.append(
            row_to_geojson(x, lon, lat)), axis=1)
        return geojson.FeatureCollection(features)


def scale_between(minval, maxval, numStops):
    """ Scale a min and max value to equal interval domain with
        numStops discrete values
    """

    scale = []

    if numStops < 2:
        return [minval, maxval]
    elif maxval < minval:
        raise ValueError()
    else:
        domain = maxval - minval
        interval = float(domain) / float(numStops)
        for i in range(numStops):
            scale.append(round(minval + interval * i, 2))
        return scale


def create_radius_stops(breaks, min_radius, max_radius):
    """Convert a data breaks into a radius ramp
    """
    num_breaks = len(breaks)
    radius_breaks = scale_between(min_radius, max_radius, num_breaks)
    stops = []

    for i, b in enumerate(breaks):
        stops.append([b, radius_breaks[i]])
    return stops


def create_weight_stops(breaks):
    """Convert data breaks into a heatmap-weight ramp
    """
    num_breaks = len(breaks)
    weight_breaks = scale_between(0, 1, num_breaks)
    stops = []

    for i, b in enumerate(breaks):
        stops.append([b, weight_breaks[i]])
    return stops


def create_color_stops(breaks, colors='RdYlGn', color_ramps=color_ramps):
    """Convert a list of breaks into color stops using colors from colorBrewer
    or a custom list of color values in RGB, RGBA, HSL, CSS text, or HEX format.
    See www.colorbrewer2.org for a list of color options to pass
    """

    num_breaks = len(breaks)
    stops = []

    if isinstance(colors, list):
        # Check if colors contain a list of color values
        if len(colors) == 0 or len(colors) != num_breaks:
            raise ValueError(
                'custom color list must be of same length as breaks list')

        for color in colors:
            # Check if color is valid string
            try:
                Color(color)
            except:
                raise ValueError(
                    'The color code {color} is in the wrong format'.format(color=color))

        for i, b in enumerate(breaks):
            stops.append([b, colors[i]])

    else:
        if colors not in color_ramps.keys():
            raise ValueError('color does not exist in colorBrewer!')
        else:

            try:
                ramp = color_ramps[colors][num_breaks]
            except KeyError:
                raise ValueError("Color ramp {} does not have a {} breaks".format(
                    colors, num_breaks))

            for i, b in enumerate(breaks):
                stops.append([b, ramp[i]])

    return stops


def img_encode(arr, **kwargs):
    """Encode ndarray to base64 string image data

    Parameters
    ----------
    arr: ndarray (rows, cols, depth)
    kwargs: passed directly to matplotlib.image.imsave
    """
    sio = BytesIO()
    imsave(sio, arr, **kwargs)
    sio.seek(0)
    img_format = kwargs['format'] if kwargs.get('format') else 'png'
    img_str = base64.b64encode(sio.getvalue()).decode()

    return 'data:image/{};base64,{}'.format(img_format, img_str)
