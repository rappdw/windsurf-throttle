"""Streamlit app for managing Windsurf credit caps."""

import os

import pandas as pd
import streamlit as st

from windsurf_throttle.api import (
    BASE_CREDITS,
    DEFAULT_INDIVIDUAL_CAP_BUFFER,
    DEFAULT_ORG_ADDON_CAP,
    WindsurfAPIError,
    get_team_users,
    get_usage_config,
    set_usage_config,
)


def run() -> None:
    """Run the Streamlit application."""
    main()


def check_configuration() -> bool:
    """Check if required environment variables are set."""
    service_key = os.getenv("WINDSURF_SERVICE_KEY")
    if not service_key:
        st.error("⚠️ WINDSURF_SERVICE_KEY environment variable is not set.")
        st.info(
            "Set it before running the app:\n"
            "```bash\n"
            "export WINDSURF_SERVICE_KEY=your_key_here\n"
            "```\n"
            "Or create a `.env` file in the working directory."
        )
        return False
    return True


def render_verify_section() -> None:
    """Render the Verify Credit Caps section."""
    st.header("🔍 Verify Credit Caps")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Team-Level Configuration")
        if st.button("Get Team Config", key="get_team_config"):
            with st.spinner("Fetching team configuration..."):
                try:
                    config = get_usage_config(team_level=True)
                    if "addOnCreditCap" in config:
                        st.success(f"✓ Add-on credit cap: **{config['addOnCreditCap']}**")
                    else:
                        st.warning("No add-on credit cap configured at team level")
                    with st.expander("Full API Response"):
                        st.json(config)
                except WindsurfAPIError as e:
                    st.error(f"Failed to get team config: {e}")

    with col2:
        st.subheader("User-Level Configuration")
        user_emails = st.text_area(
            "Email addresses (one per line)",
            placeholder="user1@example.com\nuser2@example.com",
            height=100,
            key="verify_emails",
        )

        if st.button("Check Users", key="check_users"):
            emails = [e.strip() for e in user_emails.strip().split("\n") if e.strip()]
            if not emails:
                st.warning("Please enter at least one email address")
            else:
                results = []
                progress = st.progress(0)
                for i, email in enumerate(emails):
                    try:
                        config = get_usage_config(user_email=email)
                        cap = config.get("addOnCreditCap", "Team default")
                        results.append({"Email": email, "Add-on Cap": cap, "Status": "✓"})
                    except WindsurfAPIError as e:
                        results.append({"Email": email, "Add-on Cap": "-", "Status": f"✗ {e}"})
                    progress.progress((i + 1) / len(emails))

                st.dataframe(pd.DataFrame(results), use_container_width=True)

    st.divider()

    st.subheader("👥 Users with Custom Caps")
    st.markdown("Find all users whose add-on credit cap differs from the team default.")

    if "custom_cap_users" not in st.session_state:
        st.session_state.custom_cap_users = []

    if st.button("Find Users with Custom Caps", key="find_custom_caps"):
        with st.spinner("Fetching team configuration..."):
            try:
                team_config = get_usage_config(team_level=True)
                team_cap = team_config.get("addOnCreditCap")
            except WindsurfAPIError as e:
                st.error(f"Failed to get team config: {e}")
                return

        with st.spinner("Fetching team users..."):
            try:
                users = get_team_users()
            except WindsurfAPIError as e:
                st.error(f"Failed to get team users: {e}")
                return

        if not users:
            st.warning("No users found in team")
            return

        st.info(f"Team cap: **{team_cap if team_cap is not None else 'Not set'}** | Checking {len(users)} users...")

        results = []
        progress = st.progress(0)
        status_text = st.empty()

        for i, user in enumerate(users):
            email = user.get("email", "")
            name = user.get("name", "")
            if not email:
                continue

            status_text.text(f"Checking {email}...")
            try:
                config = get_usage_config(user_email=email)
                user_cap = config.get("addOnCreditCap")

                if user_cap is not None and user_cap != team_cap:
                    results.append({
                        "Name": name,
                        "Email": email,
                        "User Cap": user_cap,
                        "Team Cap": team_cap if team_cap is not None else "Not set",
                    })
            except WindsurfAPIError:
                pass

            progress.progress((i + 1) / len(users))

        status_text.empty()
        progress.empty()

        st.session_state.custom_cap_users = results

        if results:
            st.success(f"Found **{len(results)}** users with custom caps")
        else:
            st.success("All users are using the team default cap")

    if st.session_state.custom_cap_users:
        st.dataframe(pd.DataFrame(st.session_state.custom_cap_users), use_container_width=True)

        st.divider()
        st.markdown("**Reset to Team Default**")
        st.markdown("Clear individual caps for selected users so they use the team default.")

        select_all = st.checkbox("Select all users", key="select_all_custom_caps")

        selected_emails = []
        for user in st.session_state.custom_cap_users:
            email = user["Email"]
            checked = st.checkbox(
                f"{user['Name']} ({email}) - Current cap: {user['User Cap']}",
                value=select_all,
                key=f"clear_cap_{email}",
            )
            if checked:
                selected_emails.append(email)

        if selected_emails and st.button(
            f"🗑️ Clear Caps for {len(selected_emails)} User(s)",
            type="primary",
            key="clear_selected_caps",
        ):
            progress = st.progress(0)
            status_text = st.empty()
            success_count = 0
            fail_count = 0

            for i, email in enumerate(selected_emails):
                status_text.text(f"Clearing cap for {email}...")
                try:
                    set_usage_config(clear_add_on_credit_cap=True, user_email=email)
                    success_count += 1
                except WindsurfAPIError as e:
                    st.error(f"Failed to clear cap for {email}: {e}")
                    fail_count += 1
                progress.progress((i + 1) / len(selected_emails))

            status_text.empty()
            progress.empty()

            if success_count > 0:
                st.success(f"✓ Cleared caps for {success_count} user(s)")
            if fail_count > 0:
                st.warning(f"Failed to clear caps for {fail_count} user(s)")

            st.session_state.custom_cap_users = []
            st.rerun()


def render_set_team_section() -> None:
    """Render the Set Team Cap section."""
    st.header("🏢 Set Team-Level Cap")

    col1, col2 = st.columns([2, 1])

    with col1:
        team_cap = st.number_input(
            "Organization-wide add-on credit cap",
            min_value=0,
            max_value=100000,
            value=DEFAULT_ORG_ADDON_CAP,
            step=100,
            help=f"Users will have {BASE_CREDITS} base credits + this add-on cap",
        )
        st.info(
            f"Total credits per user: **{BASE_CREDITS}** base + **{team_cap}** add-on = **{BASE_CREDITS + team_cap}**"
        )

    with col2:
        st.write("")  # Spacer
        st.write("")
        if st.button("🚀 Set Team Cap", type="primary", key="set_team_cap"):
            with st.spinner("Setting team-level cap..."):
                try:
                    result = set_usage_config(set_add_on_credit_cap=int(team_cap), team_level=True)
                    st.success(f"✓ Team cap set to {team_cap}")
                    with st.expander("API Response"):
                        st.json(result)
                except WindsurfAPIError as e:
                    st.error(f"Failed to set team cap: {e}")

    st.divider()

    if st.button("🗑️ Clear Team Cap", key="clear_team_cap"):
        with st.spinner("Clearing team-level cap..."):
            try:
                result = set_usage_config(clear_add_on_credit_cap=True, team_level=True)
                st.success("✓ Team cap cleared")
                with st.expander("API Response"):
                    st.json(result)
            except WindsurfAPIError as e:
                st.error(f"Failed to clear team cap: {e}")


def render_set_individual_section() -> None:
    """Render the Set Individual Caps section."""
    st.header("👤 Set Individual Caps")

    tab1, tab2 = st.tabs(["Single User", "Bulk from CSV"])

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            email = st.text_input("User email", placeholder="user@example.com", key="single_email")
            cap = st.number_input(
                "Add-on credit cap",
                min_value=0,
                max_value=100000,
                value=1500,
                step=100,
                key="single_cap",
            )

        with col2:
            st.write("")  # Spacer
            st.info(f"Total: **{BASE_CREDITS}** base + **{cap}** add-on = **{BASE_CREDITS + cap}**")

            if st.button("Set User Cap", type="primary", key="set_single_cap"):
                if not email:
                    st.warning("Please enter an email address")
                else:
                    with st.spinner(f"Setting cap for {email}..."):
                        try:
                            result = set_usage_config(
                                set_add_on_credit_cap=int(cap), user_email=email
                            )
                            st.success(f"✓ Cap set for {email}")
                            with st.expander("API Response"):
                                st.json(result)
                        except WindsurfAPIError as e:
                            st.error(f"Failed: {e}")

            if st.button("Clear User Cap", key="clear_single_cap"):
                if not email:
                    st.warning("Please enter an email address")
                else:
                    with st.spinner(f"Clearing cap for {email}..."):
                        try:
                            result = set_usage_config(
                                clear_add_on_credit_cap=True, user_email=email
                            )
                            st.success(f"✓ Cap cleared for {email}")
                        except WindsurfAPIError as e:
                            st.error(f"Failed: {e}")

    with tab2:
        st.markdown(
            """
            Upload a CSV file with columns:
            - `email` (required): User email address
            - `credits_used` (required): Current credit usage

            Caps will be calculated as: `(credits_used - base_credits) + buffer`
            """
        )

        col1, col2 = st.columns(2)
        with col1:
            threshold = st.number_input(
                "Only process users above this usage",
                min_value=0,
                value=1000,
                step=100,
                key="csv_threshold",
            )
        with col2:
            buffer = st.number_input(
                "Buffer to add above current usage",
                min_value=0,
                value=DEFAULT_INDIVIDUAL_CAP_BUFFER,
                step=100,
                key="csv_buffer",
            )

        uploaded_file = st.file_uploader("Upload CSV", type=["csv"], key="csv_upload")

        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)

            if "email" not in df.columns or "credits_used" not in df.columns:
                st.error("CSV must have 'email' and 'credits_used' columns")
            else:
                # Filter and calculate caps
                high_usage = df[df["credits_used"] > threshold].copy()
                high_usage["addon_used"] = high_usage["credits_used"] - BASE_CREDITS
                high_usage["proposed_cap"] = (high_usage["addon_used"] + buffer).astype(int)
                high_usage["total_available"] = BASE_CREDITS + high_usage["proposed_cap"]

                st.write(f"**{len(high_usage)}** users above threshold:")
                st.dataframe(
                    high_usage[["email", "credits_used", "addon_used", "proposed_cap", "total_available"]],
                    use_container_width=True,
                )

                dry_run = st.checkbox("Dry run (don't actually set caps)", value=True)

                if st.button("Apply Caps", type="primary", key="apply_bulk_caps"):
                    results = []
                    progress = st.progress(0)
                    status_text = st.empty()

                    for i, row in high_usage.iterrows():
                        email = row["email"]
                        cap = int(row["proposed_cap"])
                        status_text.text(f"Processing {email}...")

                        if dry_run:
                            results.append(
                                {"email": email, "cap": cap, "status": "Would set (dry run)"}
                            )
                        else:
                            try:
                                set_usage_config(set_add_on_credit_cap=cap, user_email=email)
                                results.append({"email": email, "cap": cap, "status": "✓ Set"})
                            except WindsurfAPIError as e:
                                results.append({"email": email, "cap": cap, "status": f"✗ {e}"})

                        progress.progress((i + 1) / len(high_usage))

                    status_text.empty()
                    st.success("Processing complete!")
                    st.dataframe(pd.DataFrame(results), use_container_width=True)


def main() -> None:
    """Main Streamlit app entry point."""
    st.set_page_config(
        page_title="Windsurf Credit Throttle",
        page_icon="🌊",
        layout="wide",
    )

    st.title("🌊 Windsurf Credit Throttle")
    st.markdown("Manage add-on credit caps for your Windsurf organization")

    if not check_configuration():
        st.stop()

    try:
        team_config = get_usage_config(team_level=True)
        team_cap = team_config.get("addOnCreditCap")

        if team_cap is not None:
            st.info(
                f"📊 **Team Add-on Credit Cap:** {team_cap} credits | "
                f"[View Current Balance →](https://windsurf.com/team/analytics)"
            )
        else:
            st.warning(
                "⚠️ No team add-on credit cap configured | "
                "[View Current Balance →](https://windsurf.com/team/analytics)"
            )
    except WindsurfAPIError:
        st.warning("[View Team Analytics →](https://windsurf.com/team/analytics)")

    st.divider()

    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select action:",
        ["Verify Caps", "Set Team Cap", "Set Individual Caps"],
        label_visibility="collapsed",
    )

    st.sidebar.divider()
    st.sidebar.markdown(
        f"""
        **Configuration**
        - Base credits: {BASE_CREDITS}
        - Default org cap: {DEFAULT_ORG_ADDON_CAP}
        - Default buffer: {DEFAULT_INDIVIDUAL_CAP_BUFFER}
        """
    )

    if page == "Verify Caps":
        render_verify_section()
    elif page == "Set Team Cap":
        render_set_team_section()
    elif page == "Set Individual Caps":
        render_set_individual_section()


if __name__ == "__main__":
    main()
