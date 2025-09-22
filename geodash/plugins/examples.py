from dataclasses import dataclass
import streamlit as st


@dataclass
class NotesPlugin:
    name: str = "Notes"

    def render(self) -> None:
        st.text_area("Notes", placeholder="Write notes about selected wells or regions…", height=120)



