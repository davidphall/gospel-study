import dash
from dash import html, dcc, callback, Output, Input, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from db.queries import search_scriptures, get_scripture_volumes
from services.text_analysis import top_ngrams_from_texts, top_window_words_from_texts

dash.register_page(__name__, path="/scripture-context", name="Words in Context")

volumes = get_scripture_volumes()

layout = html.Div([
    html.Br(),
    html.H2("Words in Context"),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.Label("Select Volume"),
            dcc.Dropdown(
                id="ctx-volume-picker",
                options=[{"label": v, "value": v} for v in volumes],
                multi=True, placeholder="Select volumes...",
            ),
            html.Br(),
            html.Label("Window width"),
            dbc.Input(id="ctx-window", type="number", value=3, min=1, step=1),
            html.Br(),
            html.Label("Window type"),
            dbc.Select(
                id="ctx-direction",
                options=[{"label": d, "value": d} for d in ["Both", "Before", "After"]],
                value="Both",
            ),
        ], width=3),
        dbc.Col([
            html.Label("Focal word/phrase"),
            dcc.Textarea(id="ctx-search-input", style={"width": "400px", "height": "35px"}),
        ], width=4),
        dbc.Col([
            dbc.Button("Search", id="ctx-search-btn", color="secondary",
                       style={"width": "100%"}),
        ], width=2, className="offset-2"),
    ]),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.P("Top phrases in verse", style={"fontSize": "20px", "fontWeight": "bold"}),
            dcc.Graph(id="ctx-verse-chart", figure=go.Figure(),
                      style={"height": "600px"}),
        ], width=6),
        dbc.Col([
            html.P("Top words in window", style={"fontSize": "20px", "fontWeight": "bold"}),
            dcc.Graph(id="ctx-window-chart", figure=go.Figure(),
                      style={"height": "600px"}),
        ], width=6),
    ]),
])


def make_horizontal_bar(data: list[dict], x_col: str = "count", y_col: str = "phrase") -> go.Figure:
    if not data:
        return go.Figure()
    phrases = [d[y_col] for d in reversed(data)]
    counts = [d[x_col] for d in reversed(data)]
    fig = go.Figure(go.Bar(x=counts, y=phrases, orientation="h"))
    fig.update_layout(
        yaxis_title="", xaxis_title="",
        template="plotly_white",
        margin=dict(l=200),
    )
    return fig


@callback(
    Output("ctx-verse-chart", "figure"),
    Output("ctx-window-chart", "figure"),
    Input("ctx-search-btn", "n_clicks"),
    State("ctx-search-input", "value"),
    State("ctx-volume-picker", "value"),
    State("ctx-window", "value"),
    State("ctx-direction", "value"),
    prevent_initial_call=True,
)
def search_context(n_clicks, search_term, selected_volumes, window, direction):
    if not search_term or not selected_volumes:
        return go.Figure(), go.Figure()

    verses = search_scriptures(search_term, volumes=selected_volumes)
    if not verses:
        return go.Figure(), go.Figure()

    texts = [v["text"] for v in verses]

    verse_ngrams = top_ngrams_from_texts(texts, ns=[2, 3], top_n=25)
    verse_chart = make_horizontal_bar(verse_ngrams)

    window_words = top_window_words_from_texts(
        texts, focal_word=search_term, window=int(window),
        direction=direction, top_n=25,
    )
    window_chart = make_horizontal_bar(window_words)

    return verse_chart, window_chart
