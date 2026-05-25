"""Main Dash application entry point."""
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Output, Input, State

from components.sidebar import create_sidebar

dash_app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css",
    ],
    suppress_callback_exceptions=True,
)

dash_app.layout = html.Div([
    dcc.Location(id="url"),
    html.Div(
        create_sidebar(),
        id="sidebar-container",
        className="sidebar-open",
    ),
    html.Button(
        html.I(className="fas fa-bars"),
        id="sidebar-toggle",
        className="sidebar-toggle-btn",
    ),
    html.Div(
        dash.page_container,
        id="content-container",
        className="content",
    ),
])


@callback(
    Output("sidebar-container", "className"),
    Output("content-container", "className"),
    Output("sidebar-toggle", "className"),
    Input("sidebar-toggle", "n_clicks"),
    State("sidebar-container", "className"),
    prevent_initial_call=True,
)
def toggle_sidebar(n_clicks, current_class):
    if current_class == "sidebar-open":
        return "sidebar-closed", "content content-expanded", "sidebar-toggle-btn toggle-shifted"
    return "sidebar-open", "content", "sidebar-toggle-btn"


app = dash_app.server

if __name__ == "__main__":
    dash_app.run(debug=True, port=8050)
