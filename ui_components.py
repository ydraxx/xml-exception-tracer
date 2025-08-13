import streamlit as st
from collections import defaultdict

def extract_filter_values(conditions):
    """Extract all possible filter values from conditions."""
    filter_values = defaultdict(set)
    for condition in conditions:
        for part in condition.split(','):
            if "==" in part:
                name, value = part.split("==")
                filter_values[name.strip()].add(value.strip().replace(";", ""))
    return {k: sorted(v) for k, v in filter_values.items()}

def display_ini_result(result: dict):
    """Display event groups and prefilters."""
    if "error" in result:
        st.error(result["error"])
        return

    # Event groups
    st.subheader("Event List")
    for group_name, group_data in result["eventGroups"].items():
        st.markdown(f"#### {'No group' if group_name == '__root__' else f'Event group: {group_name}'}")
        for event in group_data["events"]:
            st.markdown(f"- {', '.join(f'{k}: {v}' for k, v in event.items())}")

    # Prefilters
    st.subheader("Prefilter per entities")
    for entity, conditions in result["preFiltersGroupedByEntities"].items():
        with st.expander(f"Entity: {entity} ({len(conditions)} conditions)"):
            filter_values = extract_filter_values(conditions)
            filter_names = list(filter_values.keys())
            if all(len(c.split(',')) == 1 for c in conditions):
                for fname, values in filter_values.items():
                    st.markdown(f"- **{fname}**: {', '.join(values)}")
                continue
            cols = st.columns(len(filter_names))
            filters = {fname: cols[i].selectbox(fname, [""] + filter_values[fname]) for i, fname in enumerate(filter_names)}
            results = []
            for condition in conditions:
                parts = [p.strip() for p in condition.split(',')]
                if all(fv == "" or f"{fn}=={fv}" in condition for fn, fv in filters.items()):
                    results.append(condition)
            if results:
                st.write(", ".join(results))

def display_exceptions(exceptions, selected_groups, llm_request, print_code, replace_print_code, find_directory):
    """Display exceptions filtered by selected groups."""
    grouped = defaultdict(list)
    for exc in exceptions:
        grouped[exc.get('condition_group', 'Autre')].append(exc)

    for group, group_exceptions in grouped.items():
        if group not in selected_groups:
            continue
        st.subheader("No exception group" if group == 'None' else group)
        for exc in group_exceptions:
            st.markdown(f"**{exc['condition_id']}** - {exc['type']} - {exc['format']} - {exc['path']}")

            with st.expander("Details", expanded=False):
                # LLM code retrieval
                code_display = exc.get("llm_code")
                if not code_display:
                    code_display = llm_request(exc)
                    exc["llm_code"] = code_display

                # Option pour afficher le code original
                if st.checkbox("Show code", key=f"show_code_{exc['condition_id']}"):
                    st.code(print_code(code_display), language="cpp")

                # Option pour remplacer les prints
                if st.checkbox("Replace print_code", key=f"replace_print_{exc['condition_id']}"):
                    code_display = replace_print_code(code_display)
                    st.code(code_display, language="cpp")

                # Option pour ouvrir le fichier
                if st.button("Open file", key=f"open_file_{exc['condition_id']}"):
                    directory = find_directory(exc["path"])
                    st.info(f"Open directory: {directory}")
