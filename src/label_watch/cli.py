from typing import Annotated

from InquirerPy import inquirer
import pandas as pd
import questionary
import typer

from label_watch.database_reader import (
    add_tracked_drug,
    add_tracked_drugs,
    filter_records_by_dosage_form,
    read_all_brand_names,
    read_all_generic_names,
    read_all_manufacturers,
    read_all_options,
    read_dosage_forms,
    read_records,
)
from label_watch.gui import renderGrid

app = typer.Typer(no_args_is_help=True)


@app.command()
def start():
    """
    START
    """
    typer.echo("Welcome to LabelWatch")


@app.command()
def select_labels():
    """
    Use this function to select the set id you want to monitor by searching by drug name and company name
    """
    selected = questionary.select(
        "How do you want to search for the drug of your interest ?",
        choices=["Brand Name", "Generic Drug Name"],
    ).ask()

    selected_drug, selected_generic_drug = None, None
    if selected == "Brand Name":
        brand_names = read_all_brand_names()
        selected_drug = inquirer.fuzzy(
            message="Search for a drug by its brand name: ", choices=brand_names
        ).execute()

    else:
        generic_drug_names = read_all_generic_names()
        selected_generic_drug = inquirer.fuzzy(
            message="Search for a drug by its generic name:", choices=generic_drug_names
        ).execute()

    company_names = read_all_manufacturers(
        brand_name=selected_drug,
        generic_name=selected_generic_drug,
    )
    if not company_names:
        typer.echo("No manufacturers found matching the selected drug.")
        return

    selected_company_name = inquirer.fuzzy(
        message="Select a manufacturer:", choices=company_names
    ).execute()

    select_labels_phase2(
        selected_company=selected_company_name,
        selected_drug=selected_drug,
        selected_generic_drug=selected_generic_drug,
    )


def select_labels_phase2(
    selected_company: str,
    selected_drug: str | None = None,
    selected_generic_drug: str | None = None,
):
    returned_records = read_records(
        manufacturer=selected_company,
        brand_name=selected_drug,
        generic_name=selected_generic_drug,
    )
    if not returned_records:
        typer.echo("No records found matching your query.")
        return

    if len(returned_records) == 1:
        typer.echo(
            "Only one set id matching your query was found, moving to automatically add it to tracked set ids"
        )
        add_tracked_drug(record=returned_records[0])
        return

    available_dosage_forms = read_dosage_forms(returned_records)
    if len(available_dosage_forms) > 1:
        selected_dosage_form = inquirer.fuzzy(
            message="Select the dosage form you want to monitor",
            choices=available_dosage_forms + ["All"],
        ).execute()
        if selected_dosage_form != "All":
            returned_records = filter_records_by_dosage_form(
                returned_records, selected_dosage_form
            )

    rows = []

    for record in returned_records:
        openfda = record.get("openfda", {})

        rows.append(
            {
                "set_id": record.get("set_id"),
                "id": record.get("id"),
                "version": record.get("version"),
                "effective_time": record.get("effective_time"),
                "brand_name": openfda.get("brand_name", []),
                "manufacturer": openfda.get("manufacturer_name", []),
                "generic_name": openfda.get("generic_name", []),
                "product_ndc": openfda.get("product_ndc", []),
                "package_ndc": openfda.get("package_ndc", []),
                "strength": openfda.get("strength", []),
                "dosage_form": openfda.get("dosage_form", []),
                "route": openfda.get("route", []),
                "product_type": openfda.get("product_type", []),
            }
        )

    df = pd.DataFrame(rows)

    records_by_set_id = {
        record["set_id"]: record for record in returned_records if record.get("set_id")
    }
    display_df = df[
        [
            "set_id",
            "brand_name",
            "generic_name",
            "manufacturer",
            "dosage_form",
            "route",
        ]
    ].copy()
    for column in display_df.columns:
        if column != "set_id":
            display_df[column] = display_df[column].map(
                lambda value: ", ".join(map(str, value)) if isinstance(value, list) else value
            )

    def save_selection(set_ids: list[str], option_ids: list[int]) -> list[int]:
        records = [records_by_set_id[set_id] for set_id in dict.fromkeys(set_ids)]
        return add_tracked_drugs(records, option_ids=option_ids)

    renderGrid(display_df, save_selection, get_options=read_all_options)


@app.command(name="add_labels")
def add_labels_to_monitor(
    set_label: Annotated[str, "The set label you want the monitoring to be done on"],
):
    """
    Directly add new labels to add to your monitoring list
    If you are unsure about the set label of the drug report you want to monitor use the command select_labels instead
    """


if __name__ == "__main__":
    select_labels()
