"""Streamlit app for managing Windsurf credit caps."""

import os
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from windsurf_throttle.api import (
    BASE_CREDITS,
    DEFAULT_INDIVIDUAL_CAP_BUFFER,
    DEFAULT_ORG_ADDON_CAP,
    WindsurfAPIError,
    get_scim_groups,
    get_scim_users,
    get_team_credit_balance,
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

                st.dataframe(pd.DataFrame(results), width="stretch")

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
        st.dataframe(pd.DataFrame(st.session_state.custom_cap_users), width="stretch")

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
                    width="stretch",
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
                    st.dataframe(pd.DataFrame(results), width="stretch")


def _shift_cycle(
    balance: dict[str, Any], n_cycles_back: int
) -> tuple[str | None, str | None, str]:
    """Shift the current billing cycle backwards by N cycles.

    Returns (start_iso, end_iso, label). If N=0, returns the current cycle.
    """
    start_raw = balance.get("billingCycleStart")
    end_raw = balance.get("billingCycleEnd")
    if not start_raw or not end_raw:
        return None, None, "unknown cycle"

    # Parse ISO 8601; handle trailing Z
    def _parse(s: str) -> datetime:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))

    start = _parse(start_raw)
    end = _parse(end_raw)
    duration = end - start
    new_start = start - n_cycles_back * duration
    new_end = end - n_cycles_back * duration

    def _fmt(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    label = f"{new_start.date()} to {new_end.date()}"
    return _fmt(new_start), _fmt(new_end), label


def _resolve_scope(
    scope: str, n_back: int, balance: dict[str, Any]
) -> tuple[str | None, str | None, str]:
    """Resolve a scope choice into (start_timestamp, end_timestamp, label)."""
    if scope == "Lifetime (no timestamp filter)":
        return None, None, "lifetime"
    if scope == "Current billing cycle":
        return _shift_cycle(balance, 0)
    if scope == "Nth previous billing cycle":
        return _shift_cycle(balance, n_back)
    return None, None, "unknown"


def render_reports_section() -> None:
    """Render the Utilization Reports section."""
    st.header("📊 Utilization Reports")

    st.subheader("📊 Per-Group Usage Report (CSV)")
    st.markdown(
        "Aggregates per-user flow credit usage by group for the **current billing cycle**. "
        "**Cost model:** $32 base seat fee + $0.04 × (credits used above 500). "
        "A user counts in every group they belong to."
    )

    group_scope = st.radio(
        "Time scope",
        ["Current billing cycle", "Lifetime (no timestamp filter)", "Nth previous billing cycle"],
        key="group_report_scope",
        horizontal=True,
    )
    group_n_back = 1
    if group_scope == "Nth previous billing cycle":
        group_n_back = st.number_input(
            "N (1 = previous cycle, 2 = two cycles ago, ...)",
            min_value=1,
            max_value=60,
            value=1,
            step=1,
            key="group_report_n_back",
        )

    if st.button("Generate Report", type="primary", key="gen_usage_report"):
        with st.spinner("Fetching team usage, SCIM users, groups, and billing cycle..."):
            try:
                balance = get_team_credit_balance()
                start_ts, end_ts, scope_label = _resolve_scope(
                    group_scope, int(group_n_back), balance
                )
                team_users = get_team_users(start_timestamp=start_ts, end_timestamp=end_ts)
                scim_users = get_scim_users()
                scim_groups = get_scim_groups()
            except WindsurfAPIError as e:
                st.error(f"Failed to fetch data: {e}")
                return

        cycle_start = (start_ts or "")[:10]
        cycle_end = (end_ts or "")[:10]
        st.caption(f"📅 Scope: **{scope_label}**")

        # Map SCIM user id -> email (to join with team_users which is keyed by email)
        def _email_of(u: dict[str, Any]) -> str:
            emails = u.get("emails") or []
            if emails:
                return str(emails[0].get("value", "")).lower()
            return str(u.get("userName", "")).lower()

        scim_id_to_email = {u.get("id", ""): _email_of(u) for u in scim_users}
        scim_id_to_name = {
            u.get("id", ""): u.get("displayName") or _email_of(u) for u in scim_users
        }

        # Map email -> usage (promptCreditsUsed is in hundredths; divide by 100 for credits)
        email_to_credits: dict[str, int] = {}
        email_to_name: dict[str, str] = {}
        for u in team_users:
            email = str(u.get("email", "")).lower()
            if not email:
                continue
            raw = u.get("promptCreditsUsed", 0) or 0
            credits = int(raw) // 100
            email_to_credits[email] = credits
            email_to_name[email] = u.get("name", "") or email

        def _cost(credits: int) -> float:
            overage = max(0, credits - 500)
            return 32.0 + 0.04 * overage

        # Build per-group rows
        group_rows: dict[str, list[dict[str, Any]]] = {}
        missing_usage: set[str] = set()

        for g in scim_groups:
            gname = g.get("displayName", "")
            if not gname:
                continue
            rows: list[dict[str, Any]] = []
            for m in g.get("members", []):
                uid = m.get("value", "")
                email = scim_id_to_email.get(uid, "")
                if not email:
                    continue
                credits = email_to_credits.get(email)
                name = email_to_name.get(email) or scim_id_to_name.get(uid, "")
                if credits is None:
                    missing_usage.add(email)
                    credits = 0
                rows.append({
                    "Name": name,
                    "Email": email,
                    "Credits Used": credits,
                    "Base Cost": 32.00,
                    "Overage Cost": round(0.04 * max(0, credits - 500), 2),
                    "Total Cost": round(_cost(credits), 2),
                })
            group_rows[gname] = rows

        # Build summary sheet
        summary = []
        for gname, rows in sorted(group_rows.items()):
            total_credits = sum(r["Credits Used"] for r in rows)
            total_cost = sum(r["Total Cost"] for r in rows)
            summary.append({
                "Group": gname,
                "# Members": len(rows),
                "Total Credits Used": total_credits,
                "Total Cost ($)": round(total_cost, 2),
                "Avg Credits / Member": round(total_credits / len(rows), 1) if rows else 0,
                "Avg Cost / Member ($)": round(total_cost / len(rows), 2) if rows else 0,
            })

        # Preview
        st.success(f"Report generated for {len(group_rows)} group(s)")
        if cycle_start and cycle_end:
            st.caption(f"📅 Billing cycle: **{cycle_start}** to **{cycle_end}**")
        st.dataframe(pd.DataFrame(summary), width="stretch")

        if missing_usage:
            with st.expander(f"⚠️ {len(missing_usage)} user(s) in groups had no usage data"):
                st.write(sorted(missing_usage))

        csv_data = pd.DataFrame(summary).to_csv(index=False).encode("utf-8")
        fname_suffix = f"{cycle_start}_to_{cycle_end}" if cycle_start and cycle_end else "current"
        st.download_button(
            label="📥 Download Group CSV",
            data=csv_data,
            file_name=f"windsurf-group-usage_{fname_suffix}.csv",
            mime="text/csv",
            key="download_group_csv",
        )

    st.divider()

    st.subheader("📄 Per-User Usage Report (CSV)")
    st.markdown(
        "Per-user flow credit usage and cost for the **current billing cycle**. "
        "**Cost model:** $32 base seat fee + $0.04 × (credits used above 500)."
    )

    scope = st.radio(
        "Time scope",
        ["Current billing cycle", "Lifetime (no timestamp filter)", "Nth previous billing cycle"],
        key="usage_scope",
        horizontal=True,
    )
    user_n_back = 1
    if scope == "Nth previous billing cycle":
        user_n_back = st.number_input(
            "N (1 = previous cycle, 2 = two cycles ago, ...)",
            min_value=1,
            max_value=60,
            value=1,
            step=1,
            key="user_csv_n_back",
        )

    if st.button("Generate User CSV", type="primary", key="gen_user_csv"):
        with st.spinner("Fetching user usage..."):
            try:
                balance = get_team_credit_balance()
                start_ts, end_ts, scope_label = _resolve_scope(
                    scope, int(user_n_back), balance
                )
                team_users = get_team_users(
                    start_timestamp=start_ts, end_timestamp=end_ts
                )
            except WindsurfAPIError as e:
                st.error(f"Failed to fetch data: {e}")
                return

        cycle_start = (start_ts or "")[:10]
        cycle_end = (end_ts or "")[:10]
        st.caption(f"📅 Scope: **{scope_label}**")

        rows = []
        for u in team_users:
            email = str(u.get("email", ""))
            if not email:
                continue
            raw = int(u.get("promptCreditsUsed", 0) or 0)
            credits = raw // 100
            overage = max(0, credits - 500)
            rows.append({
                "Name": u.get("name", "") or email,
                "Email": email,
                "Raw promptCreditsUsed": raw,
                "Credits Used": credits,
                "Base Cost": 32.00,
                "Overage Cost": round(0.04 * overage, 2),
                "Total Cost": round(32.0 + 0.04 * overage, 2),
                "Last Chat Usage": str(u.get("lastChatUsageTime", ""))[:10],
                "Active Days": u.get("activeDays", 0),
                "Role": u.get("role", ""),
                "Team Status": u.get("teamStatus", ""),
            })

        rows.sort(key=lambda r: r["Credits Used"], reverse=True)
        df = pd.DataFrame(rows)

        total_credits = int(df["Credits Used"].sum()) if not df.empty else 0
        total_cost = float(df["Total Cost"].sum()) if not df.empty else 0.0

        st.success(f"Report generated for {len(rows)} user(s)")
        if cycle_start and cycle_end:
            st.caption(f"📅 Billing cycle: **{cycle_start}** to **{cycle_end}**")
        st.metric("Total Credits", f"{total_credits:,}")
        st.metric("Total Cost", f"${total_cost:,.2f}")
        st.dataframe(df, width="stretch")

        csv_data = df.to_csv(index=False).encode("utf-8")
        fname_suffix = f"{cycle_start}_to_{cycle_end}" if cycle_start and cycle_end else "current"
        st.download_button(
            label="📥 Download User CSV",
            data=csv_data,
            file_name=f"windsurf-user-usage_{fname_suffix}.csv",
            mime="text/csv",
            key="download_user_csv",
        )


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
        balance = get_team_credit_balance()

        with st.expander("🔍 Debug: Raw API Response"):
            st.json(balance)

        addon_available = int(balance.get("addOnCreditsAvailable", 0))
        addon_used = int(balance.get("addOnCreditsUsed", 0))
        addon_remaining = addon_available - addon_used

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                label="💳 Add-on Credits Remaining",
                value=f"{addon_remaining:,}",
                delta=f"{addon_available:,} total"
            )

        with col2:
            usage_pct = (addon_used / addon_available * 100) if addon_available > 0 else 0
            st.metric(
                label="📊 Add-on Credits Used",
                value=f"{addon_used:,}",
                delta=f"{usage_pct:.1f}% used"
            )

        billing_start = balance.get("billingCycleStart", "")
        billing_end = balance.get("billingCycleEnd", "")
        if billing_start and billing_end:
            st.caption(f"📅 Billing cycle: {billing_start[:10]} to {billing_end[:10]}")
    except WindsurfAPIError as e:
        st.warning(f"⚠️ Could not fetch credit balance: {e}")
        st.info("[View Team Analytics →](https://windsurf.com/team/analytics)")

    st.divider()

    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select action:",
        ["Verify Caps", "Set Team Cap", "Set Individual Caps", "Generate Utilization Reports"],
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
    elif page == "Generate Utilization Reports":
        render_reports_section()


if __name__ == "__main__":
    main()
