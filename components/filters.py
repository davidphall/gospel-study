"""Reusable conference/speaker/year filter row."""
from dash import html, dcc
import dash_bootstrap_components as dbc
from db.queries import get_speakers, get_conferences
from datetime import date


def create_filter_row(prefix: str, show_year_slider: bool = True):
    conferences = get_conferences()
    speakers = get_speakers()
    current_year = date.today().year

    children = [
        dbc.Col([
            html.Label("Select Conference(s)"),
            dcc.Dropdown(
                id=f"{prefix}-conference-filter",
                options=[{"label": c, "value": c} for c in conferences],
                multi=True, placeholder="All conferences",
            ),
        ], width=3),
        dbc.Col([
            html.Label("Select Speaker(s)"),
            dcc.Dropdown(
                id=f"{prefix}-speaker-filter",
                options=[{"label": s, "value": s} for s in speakers],
                multi=True, placeholder="All speakers",
            ),
        ], width=3),
    ]

    if show_year_slider:
        children.append(
            dbc.Col([
                html.Label("Select Year(s)"),
                dcc.RangeSlider(
                    id=f"{prefix}-year-slider",
                    min=1971, max=current_year,
                    value=[1971, current_year],
                    marks={y: str(y) for y in range(1971, current_year + 1, 10)},
                    tooltip={"placement": "bottom", "always_visible": False},
                ),
            ], width=4)
        )

    return dbc.Row(children, className="mb-3")
