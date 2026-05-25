"""Collapsible sidebar with grouped menu sections."""
import dash_bootstrap_components as dbc
from dash import html, callback, Output, Input, State


def create_sidebar():
    return html.Div(
        [
            html.Div(
                [
                    html.Button(
                        html.I(className="fas fa-bars"),
                        id="sidebar-toggle",
                        className="sidebar-toggle-btn",
                    ),
                    html.H4("Gospel Study", className="sidebar-title",
                             id="sidebar-title-text"),
                ],
                className="sidebar-header",
            ),
            dbc.Nav(
                [
                    dbc.NavLink(
                        [html.I(className="fas fa-home me-2"), "Home"],
                        href="/", active="exact",
                    ),
                    html.Hr(className="sidebar-divider"),
                    html.Button(
                        [html.I(className="fas fa-microphone me-2"),
                         "Conference",
                         html.I(className="fas fa-chevron-right ms-auto sidebar-chevron",
                                id="conference-chevron")],
                        id="conference-toggle",
                        className="sidebar-section-toggle",
                    ),
                    dbc.Collapse(
                        dbc.Nav(
                            [
                                dbc.NavLink(
                                    [html.I(className="fas fa-chart-line me-2"), "Trends"],
                                    href="/trends", active="exact",
                                ),
                                dbc.NavLink(
                                    [html.I(className="fas fa-place-of-worship me-2"), "Promises"],
                                    href="/promises", active="exact",
                                ),
                                dbc.NavLink(
                                    [html.I(className="fas fa-check-circle me-2"), "Invitations"],
                                    href="/invitations", active="exact",
                                ),
                                dbc.NavLink(
                                    [html.I(className="fas fa-question-circle me-2"), "Questions"],
                                    href="/questions", active="exact",
                                ),
                            ],
                            vertical=True, pills=True,
                            className="sidebar-subnav",
                        ),
                        id="conference-collapse",
                        is_open=False,
                    ),
                    html.Hr(className="sidebar-divider"),
                    html.Button(
                        [html.I(className="fas fa-book-bible me-2"),
                         "Scriptures",
                         html.I(className="fas fa-chevron-right ms-auto sidebar-chevron",
                                id="scriptures-chevron")],
                        id="scriptures-toggle",
                        className="sidebar-section-toggle",
                    ),
                    dbc.Collapse(
                        dbc.Nav(
                            [
                                dbc.NavLink(
                                    [html.I(className="fas fa-chart-simple me-2"), "Frequency"],
                                    href="/scripture-frequency", active="exact",
                                ),
                                dbc.NavLink(
                                    [html.I(className="fas fa-book me-2"), "Words in Context"],
                                    href="/scripture-context", active="exact",
                                ),
                            ],
                            vertical=True, pills=True,
                            className="sidebar-subnav",
                        ),
                        id="scriptures-collapse",
                        is_open=False,
                    ),
                    html.Hr(className="sidebar-divider"),
                    dbc.NavLink(
                        [html.I(className="fas fa-comments me-2"), "Chat"],
                        href="/chat", active="exact",
                    ),
                ],
                vertical=True, pills=True,
            ),
        ],
        className="sidebar",
    )


@callback(
    Output("conference-collapse", "is_open"),
    Output("conference-chevron", "className"),
    Input("conference-toggle", "n_clicks"),
    State("conference-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_conference(n_clicks, is_open):
    new_state = not is_open
    chevron = "fas fa-chevron-down ms-auto sidebar-chevron" if new_state else "fas fa-chevron-right ms-auto sidebar-chevron"
    return new_state, chevron


@callback(
    Output("scriptures-collapse", "is_open"),
    Output("scriptures-chevron", "className"),
    Input("scriptures-toggle", "n_clicks"),
    State("scriptures-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_scriptures(n_clicks, is_open):
    new_state = not is_open
    chevron = "fas fa-chevron-down ms-auto sidebar-chevron" if new_state else "fas fa-chevron-right ms-auto sidebar-chevron"
    return new_state, chevron
