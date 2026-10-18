from nicegui import ui
from pandasgui import show
from src.label_watch.fetch import fetch_from_ndc, fetch_records_json
from src.label_watch.fetch_distinct_values import get_distinct_values


def show_gui(df):
    """
    Show the GUI for the application.
    """
    show(df)
