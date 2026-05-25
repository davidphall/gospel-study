import dash
from dash import html, callback, Output, Input, State, no_update, dcc
import dash_bootstrap_components as dbc
from db.queries import get_corpus_stats, get_missing_conferences
from services.scraper import scrape_and_insert_conference

dash.register_page(__name__, path="/", name="Home")


layout = html.Div([
    html.Br(),
    dbc.Row([
        dbc.Col([
            html.Img(src="/assets/Jesus_color.jpg",
                     style={"width": "100%", "maxWidth": "500px"}),
        ], width=5),
        dbc.Col([
            html.Div([
                html.Hr(style={"borderTop": "1px solid #b1b3b1"}),
                html.P(
                    '"Therefore, dearly beloved brethren, let us cheerfully do all '
                    'things that lie in our power; and then may we stand still, with '
                    'the utmost assurance, to see the salvation of God, and for his '
                    'arm to be revealed."',
                    className="home-quote",
                ),
                html.P("D&C 123:17", className="home-quote"),
                html.Hr(style={"borderTop": "1px solid #b1b3b1"}),
            ], style={"paddingTop": "80px", "maxWidth": "400px"}),
        ], width=5),
    ], align="start"),
    html.Br(),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.P("This app contains the standard works of The Church of Jesus Christ "
                   "of Latter-day Saints, and talks from General Conferences, covering"),
            html.Div(id="corpus-stats"),
            html.Br(),
            dbc.Button("Update database", id="update-db-btn", color="secondary",
                       style={"width": "200px"}),
        ], width=5),
    ]),
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id="update-modal-title")),
        dbc.ModalBody(id="update-modal-body"),
        dbc.ModalFooter([
            dbc.Button("Import", id="import-btn", color="primary",
                       style={"display": "none"}),
            dbc.Button("OK", id="close-modal-btn"),
        ]),
    ], id="update-modal", is_open=False),
    dcc.Store(id="missing-conferences-store"),
])


@callback(
    Output("corpus-stats", "children"),
    Input("url", "pathname"),
)
def load_stats(pathname):
    if pathname != "/":
        return no_update
    stats = get_corpus_stats()
    return html.Ul([
        html.Li(f"{stats['conference_count']:,} General Conferences"),
        html.Li(f"{stats['year_count']:,} Years"),
        html.Li(f"{stats['speaker_count']:,} Speakers"),
        html.Li(f"{stats['talk_count']:,} Talks"),
    ])


@callback(
    Output("update-modal", "is_open"),
    Output("update-modal-title", "children"),
    Output("update-modal-body", "children"),
    Output("import-btn", "style"),
    Output("missing-conferences-store", "data"),
    Input("update-db-btn", "n_clicks"),
    Input("close-modal-btn", "n_clicks"),
    Input("import-btn", "n_clicks"),
    State("update-modal", "is_open"),
    State("missing-conferences-store", "data"),
    prevent_initial_call=True,
)
def handle_update_modal(update_clicks, close_clicks, import_clicks,
                        is_open, missing_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update, no_update, no_update

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "close-modal-btn":
        return False, "", "", {"display": "none"}, None

    if trigger == "update-db-btn":
        missing = get_missing_conferences()
        if not missing:
            return True, "", "The database is up to date!", {"display": "none"}, None

        items = html.Ul([html.Li(m["name"]) for m in missing])
        body = html.Div([
            html.P("Would you like to load the following conferences?"),
            items,
        ])
        return (True, "Missing conferences found", body,
                {"display": "inline-block"}, missing)

    if trigger == "import-btn" and missing_data:
        try:
            count = 0
            for conf in missing_data:
                added = scrape_and_insert_conference(conf["year"], conf["month"])
                count += added
            body = f"Added {count} talks."
        except Exception as e:
            body = f"Error during import: {str(e)}"
        return True, "Import Complete", body, {"display": "none"}, None

    return no_update, no_update, no_update, no_update, no_update
