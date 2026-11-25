import streamlit as st
import pandas as pd
import time
import os
from uuid import uuid4

# Create a folder called data in the main project folder
DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_project2")
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# Define CSV file paths for each part of the usability testing
CONSENT_CSV = os.path.join(DATA_FOLDER, "consent_data.csv")
DEMOGRAPHIC_CSV = os.path.join(DATA_FOLDER, "demographic_data.csv")
TASK_CSV = os.path.join(DATA_FOLDER, "task_data.csv")
EXIT_CSV = os.path.join(DATA_FOLDER, "exit_data.csv")


CSV_SCHEMAS = {
    CONSENT_CSV: ["participant_id", "timestamp", "consent_given"],
    DEMOGRAPHIC_CSV: ["participant_id", "timestamp", "name", "age", "occupation", "familiarity", "spotify_frequency", "concert_frequency", "setlist_experience", "artist_interest"],
    TASK_CSV: ["participant_id", "timestamp", "task_name", "success", "duration_seconds", "notes", "task_ease"],
    EXIT_CSV: ["participant_id", "timestamp", "satisfaction", "difficulty", "navigation", "clarity", "use_again", "open_feedback"],
}


def load_from_csv(csv_file):
    if os.path.isfile(csv_file):
        try:
            return pd.read_csv(csv_file)
        except pd.errors.EmptyDataError:
            pass
    return pd.DataFrame()


def initialize_csv_files():
    for path, schema in CSV_SCHEMAS.items():
        if not os.path.isfile(path):
            pd.DataFrame(columns=schema).to_csv(path, index=False)


def save_to_csv(data_dict, csv_file):
    record = {"participant_id": st.session_state["participant_id"], **data_dict}
    existing = load_from_csv(csv_file)
    columns = list(dict.fromkeys([*CSV_SCHEMAS[csv_file], *existing.columns, *record]))
    pd.concat([existing.reindex(columns=columns), pd.DataFrame([record]).reindex(columns=columns)],
              ignore_index=True).to_csv(csv_file, index=False)


def render_report():
    st.header("Usability Report")
    st.caption("Task success rates, completion times, ease ratings, exit questionnaire results, and saved participant responses.")
    frames = {path: load_from_csv(path) for path in CSV_SCHEMAS}
    task_df = frames[TASK_CSV].copy()
    exit_df = frames[EXIT_CSV].copy()
    if not task_df.empty:
        st.subheader("Task comparisons")
        for column in ["duration_seconds", "task_ease"]:
            task_df[column] = pd.to_numeric(task_df[column], errors="coerce")
        task_df["completed"] = task_df["success"].eq("Yes").astype(float) * 100
        summary = task_df.groupby("task_name", sort=True).agg(
            Attempts=("success", "size"),
            Success_rate_percent=("completed", "mean"),
            Average_seconds=("duration_seconds", "mean"),
            Timed_attempts=("duration_seconds", "count"),
            Average_ease=("task_ease", "mean"),
        )
        st.dataframe(summary.round(2))
        st.caption("Success rate counts only Yes as completed; Partial and No count as incomplete. Missing times are excluded from time averages. Ease: 1 = very difficult, 7 = very easy.")
        st.write("**Task success rate (%)**")
        st.bar_chart(summary[["Success_rate_percent"]])
        st.write("**Average completion time (seconds)**")
        st.bar_chart(summary[["Average_seconds"]].dropna())
        st.write("**Average task ease (1-7)**")
        st.bar_chart(summary[["Average_ease"]].dropna())
        comparison = task_df.copy()
        comparison["participant_id"] = comparison.get("participant_id", pd.Series(index=comparison.index, dtype=str)).fillna("Legacy (ID not recorded)")
        timed = comparison.dropna(subset=["duration_seconds"])
        if not timed.empty:
            st.write("**Completion time by participant and task (seconds)**")
            st.bar_chart(timed.pivot_table(index="task_name", columns="participant_id", values="duration_seconds", aggfunc="mean"), stack=False)
            st.caption("Multiple attempts by the same participant are averaged within each task.")
    else:
        st.info("Save task results to see task comparison charts.")
    if not exit_df.empty:
        st.subheader("Exit questionnaire comparison")
        rating_columns = [column for column in ["satisfaction", "difficulty", "navigation", "clarity"] if column in exit_df]
        ratings = exit_df[rating_columns].apply(pd.to_numeric, errors="coerce")
        st.bar_chart(ratings.mean().dropna().rename("Average rating (1-10)"))
        st.caption("Higher satisfaction, navigation, and clarity are better. Higher difficulty means harder tasks. Missing answers are excluded.")
        if "use_again" in exit_df and exit_df["use_again"].notna().any():
            st.write("**Would participants use the app again?**")
            st.bar_chart(exit_df["use_again"].value_counts().rename("Responses"))
    st.subheader("Saved responses and CSV downloads")
    for path, title in [(CONSENT_CSV, "Consent"), (DEMOGRAPHIC_CSV, "Demographics"), (TASK_CSV, "Task results"), (EXIT_CSV, "Exit questionnaire")]:
        st.write(f"**{title}**")
        frame = frames[path]
        if frame.empty:
            st.info("No responses saved yet.")
        else:
            st.dataframe(frame)
        st.download_button(f"Download {title.lower()} CSV", frame.to_csv(index=False), file_name=os.path.basename(path), mime="text/csv")


SECTIONS = ["Home", "Consent", "Demographics", "Task", "Exit Questionnaire", "Report"]


def go_to_section(section):
    st.session_state["active_section"] = section


def start_participant():
    if not st.session_state.get("consent_given", False):
        st.session_state["consent_warning"] = True
        return
    st.session_state.clear()
    st.session_state["participant_id"] = "P-" + uuid4().hex[:8]
    st.session_state["consent_given"] = True
    st.session_state["consent_saved"] = True
    st.session_state["active_section"] = "Consent"
    save_to_csv({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "consent_given": True}, CONSENT_CSV)


def section_navigation(index):
    st.divider()
    previous, following = st.columns(2)
    with previous:
        if index > 0:
            st.button("←", key=f"previous_{index}",
                      on_click=go_to_section, args=(SECTIONS[index - 1],))
    with following:
        if index < len(SECTIONS) - 1:
            st.button("→", key=f"next_{index}",
                      on_click=go_to_section, args=(SECTIONS[index + 1],))


def main():
    initialize_csv_files()
    st.session_state.setdefault("participant_id", "P-" + uuid4().hex[:8])
    st.title("Setlist Archive - Project 2 Usability Test")
    st.sidebar.write(f"Current participant: **{st.session_state['participant_id']}**")
    st.sidebar.caption("Start each participant's test on the Consent page. Use the same participant ID for all sections.")

    home, consent, demographics, tasks, exit, report = st.tabs(
        SECTIONS, key="active_section", on_change="rerun"
    )

    with home:
        st.header("Introduction")
        st.write("""
        Welcome to the usability study for Setlist Archive (HCI Project 2).

        In this app, you will:
        1. Provide consent for data collection.
        2. Fill out a short demographic questionnaire.
        3. Complete tasks in Setlist Archive in a separate browser tab while thinking aloud.
        4. Answer an exit questionnaire about your experience.
        5. View a summary report (for demonstration purposes).
        """)


    with consent:
        st.header("Consent Form")

        st.write("""
                Welcome to the usability study for Setlist Archive (HCI Project 2).
        
                In this app, you will:
                1. Provide consent for data collection.
                2. Fill out a short demographic questionnaire.
                3. Complete tasks in Setlist Archive in a separate browser tab while thinking aloud.
                4. Answer an exit questionnaire about your experience.
                5. View a summary report (for demonstration purposes).
                """)
        
        st.checkbox("I agree to the consent terms and conditions.", key="consent_given")
        st.button("Start new participant", on_click=start_participant)
        if st.session_state.get("consent_warning"):
            st.warning("You must agree to the consent terms before starting a participant.")
        if st.session_state.get("consent_saved"):
            st.success("Participant started and consent saved. Continue to Demographics.")

    with demographics:
        st.header("Demographic Questionnaire")

        with st.form("demographic_form"):
            name = st.text_input("Name", key=f"{st.session_state['participant_id']}:name")
            age = st.number_input("Age", min_value=0, key=f"{st.session_state['participant_id']}:age")
            occupation = st.text_input("Occupation", key=f"{st.session_state['participant_id']}:occupation")
            familiarity = st.slider("How familiar are you with music or concert-history apps? (1 = not familiar, 10 = very familiar)", 1, 10, key=f"{st.session_state['participant_id']}:familiarity")
            spotify_frequency = st.selectbox("How often do you use Spotify?", ["Never", "Less than monthly", "Monthly", "Weekly", "Daily"], key=f"{st.session_state['participant_id']}:spotify_frequency")
            concert_frequency = st.selectbox("How often do you attend live concerts?", ["Never", "Less than once a year", "1-3 times a year", "4 or more times a year"], key=f"{st.session_state['participant_id']}:concert_frequency")
            setlist_experience = st.radio("Have you used setlist.fm or another site to look up concert setlists?", ["Yes", "No"], key=f"{st.session_state['participant_id']}:setlist_experience")
            artist_interest = st.text_input("Which artist would you like to explore during this test?", key=f"{st.session_state['participant_id']}:artist_interest")

            submitted = st.form_submit_button("Submit Demographics")
            if submitted:
                data_dict = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "name": name,
                    "age": age,
                    "occupation": occupation,
                    "familiarity": familiarity,
                    "spotify_frequency": spotify_frequency,
                    "concert_frequency": concert_frequency,
                    "setlist_experience": setlist_experience,
                    "artist_interest": artist_interest
                }
                save_to_csv(data_dict, DEMOGRAPHIC_CSV)
                st.success("Submitted Successfully.")

    with tasks:
        st.header("Task Page")

        st.write("Please select a task and record your experience completing it.")
        st.info("Open Setlist Archive in a separate tab. Do not interact with the app until you have selected a task and clicked Start Task Timer. Start the timer before each task and stop it when you finish.")
        st.link_button("Open Setlist Archive", "https://setlistarchive.streamlit.app/")

        task_descriptions = {
            "Task 1: Find an artist": "Find an artist you know in Setlist Archive.",
            "Task 2: Filter concert history": "Show only the selected artist's concerts from the last four years.",
            "Task 3: Find a setlist": "Find the latest recorded setlist for the currently selected city.",
            "Task 4: Load a song": "Load a Spotify recording of one of the displayed songs.",
        }
        st.caption("Use the same artist where possible. Record unavailable data or service errors in the notes; the observer can distinguish these from usability problems.")
        selected_task = st.selectbox("Select Task", list(task_descriptions), key=f"{st.session_state['participant_id']}:selected_task")
        st.write("Task Description: " + task_descriptions[selected_task])
        if st.session_state.get("timed_task") != selected_task:
            st.session_state.pop("start_time", None)
            st.session_state.pop("task_duration", None)
            st.session_state["timed_task"] = selected_task

        # Track success, completion time, etc.
        start_button = st.button("Start Task Timer")
        if start_button:
            st.session_state.pop("task_duration", None)
            st.session_state["start_time"] = time.time()
            
            st.success("Task timer started.")

        stop_button = st.button("Stop Task Timer")
        if stop_button and "start_time" in st.session_state:
            duration = time.time() - st.session_state.pop("start_time")
            st.session_state["task_duration"] = duration
            st.success("Task timer stopped.")

        success = st.radio("Was the task completed successfully?", ["Yes", "No", "Partial"], key=f"{st.session_state['participant_id']}:success")
        task_ease = st.slider("How easy was this task? (1 = very difficult, 7 = very easy)", 1, 7, key=f"{st.session_state['participant_id']}:task_ease")
        notes = st.text_area("Observer notes: participant answer, hesitation, errors, help needed, or unavailable data", key=f"{st.session_state['participant_id']}:notes")

        if st.button("Save Task Results"):
            duration_val = st.session_state.get("task_duration", None)

            data_dict = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "task_name": selected_task,
                "success": success,
                "duration_seconds": duration_val if duration_val is not None else "",
                "notes": notes,
                "task_ease": task_ease
            }
            save_to_csv(data_dict, TASK_CSV)
            st.success("Saved Successfully.")
            # Reset any stored time in session_state if you'd like
            if "start_time" in st.session_state:
                del st.session_state["start_time"]
            if "task_duration" in st.session_state:
                del st.session_state["task_duration"]

    
    with exit:
        st.header("Exit Questionnaire")

        with st.form("exit_form"):
            satisfaction = st.slider("How satisfied are you with Setlist Archive? (1 = not satisfied, 10 = very satisfied)", 1, 10, key=f"{st.session_state['participant_id']}:satisfaction")
            difficulty = st.slider("How difficult were the tasks overall? (1 = very easy, 10 = very difficult)", 1, 10, key=f"{st.session_state['participant_id']}:difficulty")
            navigation = st.slider("How easy was it to find the features you needed? (1 = very difficult, 10 = very easy)", 1, 10, key=f"{st.session_state['participant_id']}:navigation")
            clarity = st.slider("How clear was the concert and setlist information? (1 = very unclear, 10 = very clear)", 1, 10, key=f"{st.session_state['participant_id']}:clarity")
            use_again = st.radio("Would you use Setlist Archive again?", ["Yes", "Maybe", "No"], key=f"{st.session_state['participant_id']}:use_again")
            open_feedback = st.text_area("What is the main thing you would improve about Setlist Archive? (Optional)", key=f"{st.session_state['participant_id']}:open_feedback")

            submitted_exit = st.form_submit_button("Submit Exit Questionnaire")
            if submitted_exit:
                data_dict = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "satisfaction": satisfaction,
                    "difficulty": difficulty,
                    "navigation": navigation,
                    "clarity": clarity,
                    "use_again": use_again,
                    "open_feedback": open_feedback
                }
                save_to_csv(data_dict, EXIT_CSV)
                st.success("Exit questionnaire data saved.")

    with report:
        render_report()

    for index, section in enumerate([home, consent, demographics, tasks, exit, report]):
        with section:
            if index in (2, 3, 4):
                st.caption("Save your responses above before moving to the next section.")
            section_navigation(index)


if __name__ == "__main__":
    main()