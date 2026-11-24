from collections.abc import Callable

from nicegui import ui
import pandas as pd

from label_watch.database_reader import get_available_fields


async def add_new_option() -> None:
    with ui.dialog() as new_option_dialog:
        with ui.card().classes("min-w-[28rem]"):
            ui.label("Create New Option").classes("text-xl font-bold mb-1")

            ui.label(
                "Choose a name and select the fields you want to monitor for changes."
            ).classes("text-sm text-gray-500 mb-3")

            option_name = ui.input(
                "Option Name",
                placeholder="Enter a name for the new option",
            ).classes("w-full")

            selection = (
                ui.select(
                    options=get_available_fields(),
                    label="Select sections to monitor",
                    multiple=True,
                    with_input=True,
                    value=[],
                )
                .props("use-chips")
                .classes("w-full")
            )

            def on_create_option() -> None:
                name = (option_name.value or "").strip()
                selected_fields = list(selection.value or [])

                if not name:
                    ui.notify(
                        "Please enter an option name.",
                        type="warning",
                    )
                    return

                if not selected_fields:
                    ui.notify(
                        "Please select at least one field.",
                        type="warning",
                    )
                    return

                print("Option name:", name)
                print("Selected fields:", selected_fields)

                new_option_dialog.close()

                ui.notify(
                    "Option values collected (not saved yet).",
                    type="info",
                )

            with ui.row().classes("gap-2 mt-4"):
                ui.button(
                    "Confirm",
                    on_click=on_create_option,
                )

                ui.button(
                    "Cancel",
                    on_click=new_option_dialog.close,
                ).props("flat")

    new_option_dialog.open()


async def show_selected(
    grid: ui.aggrid,
    save_selected: Callable,
    get_options: Callable,
) -> None:

    rows = await grid.get_selected_rows()

    selected_set_ids = list(dict.fromkeys(row["set_id"] for row in rows if row.get("set_id")))

    if not selected_set_ids:
        ui.notify(
            "Please select at least one drug.",
            type="warning",
        )
        return

    options = get_options()

    checkbox_map: dict[int, ui.checkbox] = {}

    def on_checkbox_change(option_id: int, checked: bool) -> None:
        if checked:
            for other_id, checkbox in checkbox_map.items():
                if other_id != option_id:
                    checkbox.value = False
        else:
            if not any(cb.value for cb in checkbox_map.values()):
                checkbox_map[option_id].value = True

    with ui.dialog() as tracking_dialog, ui.card().classes("min-w-[28rem]"):
        ui.label("Select Fields to Track").classes("text-xl font-bold mb-1")

        ui.label(f"{len(selected_set_ids)} drug(s) selected. Choose tracking options:").classes(
            "text-sm text-gray-500 mb-3"
        )

        if not options:
            ui.label("No tracking options found. Create a new option first.")

        for index, opt in enumerate(options):
            fields = opt.get("list_of_options") or []

            preview = ", ".join(fields[:8])

            if len(fields) > 8:
                preview += f" ... (+{len(fields) - 8} more)"

            with ui.row().classes("items-start gap-3 w-full py-1"):
                cb = ui.checkbox(
                    value=(index == 0),
                    on_change=lambda e, oid=opt["id"]: on_checkbox_change(oid, e.value),
                )

                checkbox_map[opt["id"]] = cb

                with ui.column().classes("gap-0 flex-1"):
                    ui.label(opt["name"]).classes("font-semibold")
                    ui.label(preview).classes("text-xs text-gray-500")

        def on_confirm() -> None:
            selected_option_ids = [
                option_id for option_id, checkbox in checkbox_map.items() if checkbox.value
            ]

            if not selected_option_ids:
                ui.notify(
                    "Please select at least one tracking option.",
                    type="warning",
                )
                return

            try:
                product_ids = save_selected(
                    selected_set_ids,
                    selected_option_ids,
                )
            except Exception as exc:
                ui.notify(
                    f"Failed to save drugs: {exc}",
                    type="negative",
                )
                raise

            tracking_dialog.close()

            ui.notify(
                f"Successfully tracked {len(product_ids)} drug(s).",
                type="positive",
            )

        with ui.row().classes("mt-4 gap-2"):
            ui.button(
                "Confirm",
                on_click=on_confirm,
            )

            ui.button(
                "Add New Option",
                on_click=add_new_option,
            ).props("flat")

            ui.button(
                "Cancel",
                on_click=tracking_dialog.close,
            ).props("flat")

    tracking_dialog.open()


def renderGrid(
    df: pd.DataFrame,
    save_selected: Callable,
    get_options: Callable,
) -> None:

    @ui.page("/")
    def show_grid_page() -> None:

        ui.label("Welcome to LabelWatch - Select Drugs to Track").classes("text-xl font-bold mb-2")

        grid = ui.aggrid.from_pandas(df).classes("w-full h-80")

        grid.options["rowSelection"] = "multiple"

        if grid.options.get("columnDefs"):
            grid.options["columnDefs"][0]["checkboxSelection"] = True
            grid.options["columnDefs"][0]["headerCheckboxSelection"] = True

        grid.update()

        async def on_track_click() -> None:
            await show_selected(
                grid,
                save_selected,
                get_options,
            )

        ui.button(
            "Track Selected",
            on_click=on_track_click,
        ).classes("mt-4")

    ui.run(port=8082, reload=False)
