"""Collapsible sidebar matching shinydashboard layout."""
import dash_bootstrap_components as dbc
from dash import html


def create_sidebar():
    return html.Div(
        [
            html.Div(
                html.H4("Gospel Study", className="sidebar-title"),
                className="sidebar-header",
            ),
            dbc.Nav(
                [
                    dbc.NavLink(
                        [html.I(className="fas fa-home me-2"), "Home"],
                        href="/", active="exact",
                    ),
                    html.Hr(className="sidebar-divider"),
                    html.P("Conference", className="sidebar-section-label"),
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
                    html.Hr(className="sidebar-divider"),
                    html.P("Scriptures", className="sidebar-section-label"),
                    dbc.NavLink(
                        [html.I(className="fas fa-chart-simple me-2"), "Frequency"],
                        href="/scripture-frequency", active="exact",
                    ),
                    dbc.NavLink(
                        [html.I(className="fas fa-book me-2"), "Words in Context"],
                        href="/scripture-context", active="exact",
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
