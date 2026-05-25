"""Main Dash application entry point."""
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc

from components.sidebar import create_sidebar

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css",
    ],
    suppress_callback_exceptions=True,
)

app.layout = html.Div([
    dcc.Location(id="url"),
    create_sidebar(),
    html.Div(
        dash.page_container,
        className="content",
    ),
])

server = app.server

if __name__ == "__main__":
    app.run(debug=True, port=8050)
