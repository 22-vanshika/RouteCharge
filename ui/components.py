def render_summary_card(label: str, value: str, icon: str = "") -> str:
    return f"""
    <div style="
        background-color: #f8f9fa;
        padding: 14px 18px;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        text-align: center;
        min-height: 85px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
    ">
        <span style="font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #495057;">{icon} &nbsp; {label}</span>
        <span style="font-size: 1.45rem; font-weight: 700; color: #1a1c23; margin-top: 4px;">{value}</span>
    </div>
    """


def render_validation_card(title: str, description: str) -> str:
    return f"""
    <div style="
        background-color: #e8f5e9;
        border: 1px solid #c8e6c9;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 12px;
        display: flex;
        align-items: flex-start;
        gap: 12px;
        min-height: 80px;
    ">
        <span style="font-size: 1.45rem; color: #2e7d32; font-weight: 800; line-height: 1.1;">✓</span>
        <div>
            <div style="font-weight: 700; color: #1a1c23; font-size: 0.95rem; line-height: 1.2;">{title}</div>
            <div style="font-size: 0.85rem; color: #37474f; margin-top: 4px; line-height: 1.45;">{description}</div>
        </div>
    </div>
    """


def render_weight_badge(label: str, value: float) -> str:
    return f"""
    <div style="
        background-color: #f8f9fa;
        padding: 12px 16px;
        border-radius: 6px;
        border: 1px solid #dee2e6;
        display: flex;
        justify-content: space-between;
        align-items: center;
        min-height: 48px;
    ">
        <span style="font-size: 0.85rem; font-weight: 600; color: #495057; text-transform: uppercase; letter-spacing: 0.5px;">{label}</span>
        <code style="font-size: 1.05rem; font-weight: 700; color: #1976d2; background: transparent; padding: 0;">{value:.1f}</code>
    </div>
    """
