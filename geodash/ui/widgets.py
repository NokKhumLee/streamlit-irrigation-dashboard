from typing import Optional

import pandas as pd
import streamlit as st


def metadata_panel(selected_row: Optional[pd.Series]) -> None:
    if selected_row is None:
        st.text_area("Metadata", "Select a well to see details.", height=120)
        return
    text = (
        f"Well ID: {selected_row['well_id']}\n"
        f"Region: {selected_row['region']}\n"
        f"Depth (m): {int(selected_row['depth_m'])}\n"
        f"Survival: {'Yes' if selected_row['survived'] else 'No'}\n"
    )
    st.text_area("Metadata", text, height=140)


def download_button(filtered_df: pd.DataFrame) -> None:
    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered wells (CSV)", data=csv, file_name="wells_filtered.csv", mime="text/csv")



