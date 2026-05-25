import dash
from dash import html, dcc, callback, Output, Input, State, no_update, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
from db.queries import get_scripture_volumes, get_scripture_frequency, search_scriptures

dash.register_page(__name__, path="/scripture-frequency", name="Scripture Frequency")

volumes = get_scripture_volumes()

layout = html.Div([
    html.Br(),
    html.H2("Word Frequencies"),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.Label("Select Volume"),
            dcc.Dropdown(
                id="freq-volume-picker",
                options=[{"label": v, "value": v} for v in volumes],
                multi=True, placeholder="Select volumes...",
            ),
            html.Br(),
            dbc.RadioItems(
                id="freq-sort", value="Values",
                options=[{"label": "Values", "value": "Values"},
                         {"label": "Book order", "value": "Book order"}],
                inline=True,
            ),
            html.Label("Sort chart by", className="text-muted"),
            html.Br(),
            dbc.RadioItems(
                id="freq-normalize", value="Raw counts",
                options=[{"label": "Raw counts", "value": "Raw counts"},
                         {"label": "Per 1000 words", "value": "Per 1000 words"}],
                inline=True,
            ),
            html.Label("Normalize counts", className="text-muted"),
        ], width=3),
        dbc.Col([
            html.Label("Focal word/phrase"),
            dcc.Textarea(id="freq-search-input", style={"width": "400px", "height": "35px"}),
        ], width=4),
        dbc.Col([
            dbc.Button("Search", id="freq-search-btn", color="secondary",
                       style={"width": "100%"}),
        ], width=2, className="offset-2"),
    ]),
    html.Hr(),
    dcc.Graph(id="freq-chart", figure=go.Figure()),
    html.Div(id="freq-verses-table"),
])


@callback(
    Output("freq-chart", "figure"),
    Output("freq-verses-table", "children"),
    Input("freq-search-btn", "n_clicks"),
    State("freq-search-input", "value"),
    State("freq-volume-picker", "value"),
    State("freq-normalize", "value"),
    State("freq-sort", "value"),
    prevent_initial_call=True,
)
def search_scripture_frequency(n_clicks, search_term, selected_volumes, normalize, sort_by):
    if not search_term or not selected_volumes:
        return go.Figure(), ""

    norm = normalize == "Per 1000 words"
    freq = get_scripture_frequency(search_term, volumes=selected_volumes, normalize=norm)

    if not freq:
        return go.Figure(), html.P("No results found.")

    df = pd.DataFrame(freq)

    if sort_by == "Values":
        df = df.sort_values("count", ascending=False)
    else:
        df = df.sort_values("book_id")

    fig = go.Figure(go.Bar(x=df["book"], y=df["count"]))
    fig.update_layout(
        xaxis_title="", yaxis_title="",
        template="plotly_white",
        xaxis={"categoryorder": "array", "categoryarray": df["book"].tolist()},
    )

    verses = search_scriptures(search_term, volumes=selected_volumes)
    if verses:
        vdf = pd.DataFrame(verses)
        table = dash_table.DataTable(
            data=vdf[["verse_ref", "text"]].to_dict("records"),
            columns=[
                {"name": "Reference", "id": "verse_ref"},
                {"name": "Text", "id": "text"},
            ],
            page_size=20,
            filter_action="native",
            sort_action="native",
            style_cell={"textAlign": "left", "padding": "8px",
                         "fontFamily": "Calibri, sans-serif"},
            style_header={"fontWeight": "bold"},
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"},
            ],
        )
    else:
        table = ""

    return fig, table
