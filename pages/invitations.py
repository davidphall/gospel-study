import dash
from dash import html, callback, Output, Input, State, no_update, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from components.filters import create_filter_row
from db.queries import search_talks_regex

dash.register_page(__name__, path="/invitations", name="Invitations")

INVITATION_PHRASES = (
    "I invite you|I encourage you|I recommend|I plead with you|"
    "I challenge you|I ask you to|I encourage everyone|I urge you"
)

layout = html.Div([
    html.Br(),
    html.H2("Invitations"),
    html.Hr(),
    create_filter_row("invitations"),
    dbc.Button("Find Invitations", id="invitations-btn", color="secondary",
               style={"width": "200px"}),
    html.Br(), html.Br(),
    html.Div(id="invitations-results"),
])


@callback(
    Output("invitations-results", "children"),
    Input("invitations-btn", "n_clicks"),
    State("invitations-conference-filter", "value"),
    State("invitations-speaker-filter", "value"),
    State("invitations-year-slider", "value"),
    prevent_initial_call=True,
)
def find_invitations(n_clicks, conferences, speakers, year_range):
    results = search_talks_regex(
        INVITATION_PHRASES,
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
