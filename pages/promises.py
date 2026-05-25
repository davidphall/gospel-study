import dash
from dash import html, callback, Output, Input, State, no_update, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from components.filters import create_filter_row
from db.queries import search_talks_regex

dash.register_page(__name__, path="/promises", name="Promises")

PROMISE_PHRASES = (
    "I promise you|I promise that|I leave you a promise|I leave with you a promise|"
    "I leave you this promise|I can promise you|I can promise that|if you will"
)

layout = html.Div([
    html.Br(),
    html.H2("Promises"),
    html.Hr(),
    create_filter_row("promises"),
    dbc.Button("Find Promises", id="promises-btn", color="secondary",
               style={"width": "200px"}),
    html.Br(), html.Br(),
    html.Div(id="promises-results"),
])


@callback(
    Output("promises-results", "children"),
    Input("promises-btn", "n_clicks"),
    State("promises-conference-filter", "value"),
    State("promises-speaker-filter", "value"),
    State("promises-year-slider", "value"),
    prevent_initial_call=True,
)
def find_promises(n_clicks, conferences, speakers, year_range):
    results = search_talks_regex(
        PROMISE_PHRASES,
        speakers=speakers or None,
        conferences=conferences or None,
        year_min=year_range[0] if year_range else 1971,
        year_max=year_range[1] if year_range else 2100,
    )

    if not results:
        return html.P("No results found.")

    df = pd.DataFrame(results)
    df["title"] = df.apply(
        lambda r: f"[{r['title']}]({r['link']})" if r.get("link") else r["title"],
        axis=1,
    )
    display = df[["year", "speaker", "title", "paragraph"]].copy()
    display.columns = ["Year", "Speaker", "Title", "Sentence"]

    return dash_table.DataTable(
        data=display.to_dict("records"),
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
