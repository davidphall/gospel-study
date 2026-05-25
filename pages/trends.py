import dash
from dash import html, dcc, callback, Output, Input, State, no_update, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from db.queries import search_talks_fts, search_talks_proximity, get_speakers

dash.register_page(__name__, path="/trends", name="Trends")

BLUES = ["#08306b", "#204479", "#395988", "#526e97", "#6a82a6",
         "#8397b5", "#9cacc3", "#b4c0d2", "#cdd5e1", "#e6eaf0"]

speakers = get_speakers()

layout = html.Div([
    html.Br(),
    html.H2("Trend Search"),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.H4("Keyword/phrase search"),
            html.P("Enter words and/or phrases, separated by a semicolon"),
            dcc.Textarea(id="search-input", value="", style={"width": "500px", "height": "75px"}),
            dbc.Row([
                dbc.Col([
                    dbc.RadioItems(
                        id="search-mode", value="Exact",
                        options=[{"label": "Exact", "value": "Exact"},
                                 {"label": "Fuzzy", "value": "Fuzzy"}],
                        inline=True,
                    ),
                    dbc.Button("Search", id="keyword-search-btn", color="secondary",
                               style={"width": "150px"}, className="mt-2"),
                ], width=5),
                dbc.Col([
                    html.P('e.g. when fuzzy searching, "faith" will also return "faithful"',
                           className="text-muted mt-2"),
                ], width=6),
            ]),
        ], width=6, style={"borderRight": "1px solid #ccc"}),
        dbc.Col([
            html.H4("Proximity search"),
            dbc.Row([
                dbc.Col([
                    html.Label("Word 1"),
                    dbc.Input(id="prox-word1", type="text", style={"width": "300px"}),
                    html.Label("Word 2", className="mt-2"),
                    dbc.Input(id="prox-word2", type="text", style={"width": "300px"}),
                    dbc.Button("Search", id="prox-search-btn", color="secondary",
                               style={"width": "150px"}, className="mt-2"),
                ], width=6),
                dbc.Col([
                    html.Label("Word window"),
                    dbc.Input(id="prox-window", type="number", value=5, min=1,
                              style={"width": "300px"}),
                    html.Label("Word order", className="mt-2"),
                    dbc.RadioItems(
                        id="prox-order", value="No order",
                        options=[{"label": "No order", "value": "No order"},
                                 {"label": "Ordered", "value": "Ordered"}],
                        inline=True,
                    ),
                ], width=6),
            ]),
        ], width=6),
    ]),
    html.Br(),
    html.H4("Trends"),
    dcc.Graph(id="trend-chart", figure=go.Figure()),
    html.Br(),
    html.H4("Correlations"),
    html.Div(id="correlation-table"),
    html.Br(),
    html.H4("Sentences"),
    html.Div(id="sentences-table"),
])


def build_trend_chart(results: list[dict], terms: list[str]) -> go.Figure:
    if not results:
        return go.Figure()

    df = pd.DataFrame(results)
    fig = go.Figure()

    for i, term in enumerate(terms):
        term_df = df[df["_term"] == term] if "_term" in df.columns else df
        year_counts = term_df.groupby("year").size().reset_index(name="count")
        fig.add_trace(go.Scatter(
            x=year_counts["year"], y=year_counts["count"],
            mode="lines+markers", name=term,
            line=dict(color=BLUES[i % len(BLUES)]),
        ))

    fig.update_layout(
        xaxis_title="", yaxis_title="",
        template="plotly_white", height=400,
    )
    return fig


def build_sentences_table(results: list[dict]) -> dash_table.DataTable:
    if not results:
        return html.P("No results found.")

    df = pd.DataFrame(results)
    display_df = df[["year", "speaker", "title", "paragraph"]].copy()
    display_df.columns = ["Year", "Speaker", "Title", "Sentence"]

    return dash_table.DataTable(
        data=display_df.to_dict("records"),
        columns=[
            {"name": "Year", "id": "Year"},
            {"name": "Speaker", "id": "Speaker"},
            {"name": "Title", "id": "Title", "presentation": "markdown"},
            {"name": "Sentence", "id": "Sentence"},
        ],
        page_size=5,
        filter_action="native",
        sort_action="native",
        style_cell={"textAlign": "left", "padding": "8px", "fontFamily": "Calibri, sans-serif"},
        style_header={"fontWeight": "bold"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"},
        ],
    )


@callback(
    Output("trend-chart", "figure"),
    Output("correlation-table", "children"),
    Output("sentences-table", "children"),
    Input("keyword-search-btn", "n_clicks"),
    State("search-input", "value"),
    State("search-mode", "value"),
    prevent_initial_call=True,
)
def do_keyword_search(n_clicks, search_input, mode):
    if not search_input or not search_input.strip():
        return go.Figure(), "", ""

    terms = [t.strip() for t in search_input.split(";") if t.strip()]
    all_results = []

    for term in terms:
        fts_mode = "exact" if mode == "Exact" else "fuzzy"
        results = search_talks_fts(term, mode=fts_mode)
        for r in results:
            r["_term"] = term
        all_results.extend(results)

    if not all_results:
        return go.Figure(), "", html.P("No results found.")

    fig = build_trend_chart(all_results, terms)

    corr_div = ""
    if len(terms) > 1:
        df = pd.DataFrame(all_results)
        pivot = df.groupby(["year", "_term"]).size().unstack(fill_value=0)
        if len(pivot.columns) > 1:
            corr = np.corrcoef(pivot.values.T)
            corr_df = pd.DataFrame(corr, index=pivot.columns, columns=pivot.columns)
            corr_div = dash_table.DataTable(
                data=corr_df.reset_index().to_dict("records"),
                columns=[{"name": c, "id": c} for c in ["index"] + list(pivot.columns)],
                style_cell={"textAlign": "center", "padding": "5px"},
            )

    table = build_sentences_table(all_results)
    return fig, corr_div, table


@callback(
    Output("trend-chart", "figure", allow_duplicate=True),
    Output("correlation-table", "children", allow_duplicate=True),
    Output("sentences-table", "children", allow_duplicate=True),
    Input("prox-search-btn", "n_clicks"),
    State("prox-word1", "value"),
    State("prox-word2", "value"),
    State("prox-window", "value"),
    State("prox-order", "value"),
    prevent_initial_call=True,
)
def do_proximity_search(n_clicks, word1, word2, window, order):
    if not word1 or not word2:
        return go.Figure(), "", ""

    ordered = order == "Ordered"
    results = search_talks_proximity(word1, word2, window=int(window), ordered=ordered)

    if not results:
        return go.Figure(), "", html.P("No results found.")

    label = f'"{word1}" near "{word2}"'
    for r in results:
        r["_term"] = label

    fig = build_trend_chart(results, [label])
    fig.update_layout(title=label)
    table = build_sentences_table(results)
    return fig, "", table
