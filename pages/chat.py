import dash
from dash import html, dcc, callback, Output, Input, State, no_update
import dash_bootstrap_components as dbc
from db.queries import get_similar_talks, get_similar_scriptures
from services.openai_client import (
    get_embeddings, chat_completion, DEFAULT_SYSTEM_PROMPT,
)

dash.register_page(__name__, path="/chat", name="Chat")

layout = html.Div([
    html.Br(),
    html.H2("Chat"),
    html.Hr(),

    dbc.Accordion([
        dbc.AccordionItem([
            dcc.Textarea(
                id="system-prompt-input",
                value=DEFAULT_SYSTEM_PROMPT,
                style={"width": "100%", "height": "100px", "fontFamily": "Calibri, sans-serif"},
            ),
            dbc.Button("Reset to default", id="reset-prompt-btn", color="link", size="sm",
                       className="mt-1"),
        ], title="System Prompt", item_id="sys-prompt"),
    ], start_collapsed=True, className="mb-3"),

    dbc.Row([
        dbc.Col([
            html.P("Chat", style={"fontSize": "20px", "fontWeight": "bold"}),
        ], width=10),
        dbc.Col([
            dbc.Button("Clear", id="clear-chat-btn", color="secondary",
                       style={"width": "100%"}),
        ], width=2),
    ]),
    html.Div(id="chat-output", style={"minHeight": "200px", "marginBottom": "20px"}),

    dbc.Row([
        dbc.Col([
            dbc.Input(id="chat-input", type="text", placeholder="Enter prompt here",
                      style={"width": "100%"}),
        ], width=10),
        dbc.Col([
            dbc.Button(
                html.I(className="fas fa-comments"),
                id="chat-submit-btn", color="secondary", style={"width": "100%"},
            ),
        ], width=2),
    ]),

    dcc.Store(id="chat-history-store", data=[]),
])


def format_context(talks: list[dict], scriptures: list[dict]) -> str:
    parts = []
    for t in talks:
        parts.append(
            f"[{t['speaker']}, {t['conference']} - \"{t['title']}\"]\n{t['paragraph']}"
        )
    for s in scriptures:
        parts.append(f"[{s['verse_ref']}]\n{s['text']}")
    return "\n\n---\n\n".join(parts)


def render_chat_history(history: list[dict]) -> list:
    children = []
    for msg in history:
        if msg["role"] == "user":
            children.append(
                html.Div(html.Strong(msg["content"]), className="chat-message-user")
            )
        else:
            children.append(
                html.Div(
                    dcc.Markdown(msg["content"]),
                    className="chat-message-assistant",
                )
            )
    if not children:
        children.append(html.P("Ask a question about the gospel.", className="text-muted"))
    return children


@callback(
    Output("system-prompt-input", "value"),
    Input("reset-prompt-btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset_system_prompt(n_clicks):
    return DEFAULT_SYSTEM_PROMPT


@callback(
    Output("chat-output", "children"),
    Output("chat-history-store", "data"),
    Output("chat-input", "value"),
    Input("chat-submit-btn", "n_clicks"),
    Input("clear-chat-btn", "n_clicks"),
    State("chat-input", "value"),
    State("system-prompt-input", "value"),
    State("chat-history-store", "data"),
    prevent_initial_call=True,
)
def handle_chat(submit_clicks, clear_clicks, user_input, system_prompt, history):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "clear-chat-btn":
        return render_chat_history([]), [], ""

    if trigger == "chat-submit-btn":
        if not user_input or not user_input.strip():
            return no_update, no_update, no_update

        query_embedding = get_embeddings([user_input])[0]

        similar_talks = get_similar_talks(query_embedding, limit=5)
        similar_scriptures = get_similar_scriptures(query_embedding, limit=10)

        context = format_context(similar_talks, similar_scriptures)
        augmented_prompt = (
            f"{system_prompt}\n\n"
            f"Use the following sources to inform your answer. "
            f"Cite the speaker and year for conference talks, and book/chapter/verse for scriptures.\n\n"
            f"{context}"
        )

        messages = list(history) + [{"role": "user", "content": user_input}]

        response = chat_completion(messages, system_prompt=augmented_prompt)

        new_history = list(history)
        new_history.append({"role": "user", "content": user_input})
        new_history.append({"role": "assistant", "content": response})

        return render_chat_history(new_history), new_history, ""

    return no_update, no_update, no_update
