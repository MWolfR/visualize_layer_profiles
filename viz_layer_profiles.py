from reader import read, read_url
from grouper import RegionProfile
from color_maker import ColorMaker
from ipywidgets import widgets
import plotly.graph_objects as go

rec_url = "https://portal.bluebrain.epfl.ch/wp-content/uploads/2019/02/white_matter_FULL_RECIPE_v1p15.yaml_-3.zip"
rec_fn = "white_matter_FULL_RECIPE_v1p15.yaml"

data, layer_labels = read_url(rec_url, rec_fn)
default_target_region = "SSp-ll"
default_grouping = [("Without layers", "By hemisphere"),
                    ("With layers", "All together"),
                    ("Without layers", "By projection class"),
                    ("Without layers", "By region")]
cols = ColorMaker.factory()

current_state = {'r': RegionProfile(data[default_target_region], layer_labels, colors=cols),
                 'region': default_target_region,
                 'threshold': 0.0,
                 'grouping': default_grouping
                 }
valid_grouping = [dict([('label', _lbl), ('value', _lbl)])
                  for _lbl in current_state['r']._types_of_groups + ["None"]]
layer_handling = ["Without layers", "With layers"]

# r.set_up_groups(default_grouping)
# fig = r.plot()
ttl_dict = dict([("text", "Long-range innervation"), ("font_size", 12)])
fig = go.FigureWidget(data=[go.Sankey()], layout=go.Layout(title=ttl_dict))


def full_update():
    r = current_state['r']
    new_labels, offset, lbl_colors = r.get_plotly_labels()
    link_dict = r.get_plotly_links(offset, lbl_colors, threshold=current_state['threshold'])
    with fig.batch_update():
        fig.data[0].node.label = new_labels
        fig.data[0].node.color = lbl_colors
        fig.data[0].node.update()
        fig.data[0].link.update(link_dict)
    fig.update_layout()


def update_links():
    r = current_state['r']
    _, offset, lbl_colors = r.get_plotly_labels()
    link_dict = r.get_plotly_links(offset, lbl_colors, threshold=current_state['threshold'])
    with fig.batch_update():
        fig.data[0].link.update(link_dict)


import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

marks_dict = dict([(v, "{0}E-3".format(v)) for v in range(0, 110, 10)])
region_dict = [dict([('label', reg), ('value', reg)]) for reg in sorted(data.keys())]
thresh_selector = dcc.Slider(
        id='thresh-slider',
        min=0.0,
        max=100.0,
        value=0.0,
        step=1.0,
        marks=marks_dict
    )
region_selector = dcc.Dropdown(
        id='region-dropdown',
        options=region_dict,
        value=default_target_region)
inputs = [Input('thresh-slider', 'value'),
          Input('region-dropdown', 'value')]
grouping_selectors = [dcc.Dropdown(
    id='grouping-dropdown{0}'.format(i),
    options=valid_grouping,
    value=default_grouping[i][1])
    for i in range(len(current_state['grouping']))
]
adjectives = ['First', 'Second', 'Third', 'Fourth']
per_layer_check = dcc.Checklist(
    options=[dict([('label', '{0} grouping'.format(adj)),
                   ('value', i)])
             for i, adj in enumerate(adjectives)],
    value=[i for i, _grouping in enumerate(default_grouping)
           if _grouping[0] == layer_handling[1]],
    #style={'display': 'block'},
    id='per-layer-check'
)
inputs.append(Input('per-layer-check', 'value'))
inputs.extend([Input(dd.id, 'value') for dd in grouping_selectors])

app = dash.Dash(__name__, external_stylesheets=["https://codepen.io/chriddyp/pen/bWLwgP.css"])

grouping_div = html.Div([html.Div([html.Label("{0} grouping".format(adj)), grp])
                         for grp, adj in zip(grouping_selectors, adjectives)],
                        style={'columnCount': 4})
#layer_hndlng_div = html.Div([html.Label("Split by target layer"),
#                             per_layer_check])
remaining_div = html.Div([html.Div([html.Label("Split by target layer"),
                                    per_layer_check]),
                          html.Div([html.Label("Display threshold (synapses per um^3)"),
                                    thresh_selector]),
                          html.Div([html.Label("Target Region"),
                                    region_selector])],
                          style={'columnCount': 3})

app.layout = html.Div([
    grouping_div,
    remaining_div,
    dcc.Graph(id='main-graph', figure=fig)
])

@app.callback(
    Output('main-graph', 'figure'),
    inputs
)
def master_callback(new_thresh, new_region, per_layer_idx, *grps):
    new_thresh = new_thresh / 1000.0
    current_state['grouping'] = [(layer_handling[i in per_layer_idx], grp)
                                 for i, grp in enumerate(grps)
                                 if grp != "None"]
    if current_state['region'] != new_region:
        current_state['region'] = new_region
        current_state['r'] = RegionProfile(data[new_region], layer_labels, colors=cols)
    if new_thresh != current_state['threshold']:
        current_state['threshold'] = new_thresh
        update_links()
    else:
        current_state['r'].set_up_groups(current_state['grouping'])
        full_update()
    return fig


if __name__ == "__main__":
    app.run_server(debug=True, use_reloader=True)
 
