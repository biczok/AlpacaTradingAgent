"""
Chart-related callbacks for TradingAgents WebUI
Enhanced with symbol-based pagination
"""

from dash import Input, Output, State, ctx, html, ALL, dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from webui.utils.state import app_state
from webui.utils.charts import create_chart, create_welcome_chart
from webui.utils.report_history import collect_picker_symbols, resolve_picker_symbol


def _live_symbols():
    return list(app_state.symbol_states.keys()) if app_state.symbol_states else []


def _picker_symbols(ticker_value=None):
    return collect_picker_symbols(ticker_value, live_symbols=_live_symbols())


def create_symbol_button(symbol, index, is_active=False):
    """Create a symbol button for pagination"""
    return dbc.Button(
        symbol,
        id={"type": "symbol-btn", "index": index, "component": "charts"},
        color="primary" if is_active else "outline-primary",
        size="sm",
        className=f"symbol-btn {'active' if is_active else ''}",
    )


def register_chart_callbacks(app):
    """Register all chart-related callbacks including symbol pagination"""
    
    @app.callback(
        [Output("chart-pagination-container", "children"),
         Output("chart-pagination", "max_value", allow_duplicate=True)],
        [Input("app-store", "data"),
         Input("refresh-interval", "n_intervals"),
         Input("ticker-input", "value")],
        prevent_initial_call="initial_duplicate"
    )
    def update_chart_symbol_pagination(store_data, n_intervals, ticker_value):
        """Update the symbol pagination buttons for charts"""
        symbols = _picker_symbols(ticker_value)
        if not symbols:
            empty = html.Div("No symbols available",
                          className="text-muted text-center",
                          style={"padding": "10px"})
            return empty, 1

        current_symbol = app_state.current_symbol
        
        # Find active symbol index
        active_index = 0
        if current_symbol and current_symbol in symbols:
            active_index = symbols.index(current_symbol)
        
        buttons = []
        for i, symbol in enumerate(symbols):
            is_active = i == active_index
            buttons.append(create_symbol_button(symbol, i, is_active))
        
        if len(symbols) > 1:
            # Add navigation info
            nav_info = html.Div([
                html.I(className="fas fa-chart-line me-2"),
                f"Charts for {len(symbols)} symbols"
            ], className="text-muted small text-center mt-2")
            
            return html.Div([
                dbc.ButtonGroup(buttons, className="d-flex flex-wrap justify-content-center"),
                nav_info
            ], className="symbol-pagination-wrapper"), max(len(symbols), 1)
        else:
            return dbc.ButtonGroup(buttons, className="d-flex justify-content-center"), max(len(symbols), 1)

    @app.callback(
        [Output("chart-pagination", "active_page", allow_duplicate=True),
         Output("report-pagination", "active_page", allow_duplicate=True),
         Output("chart-pagination-container", "children", allow_duplicate=True),
         Output("chart-pagination", "max_value", allow_duplicate=True),
         Output("report-pagination", "max_value", allow_duplicate=True)],
        [Input({"type": "symbol-btn", "index": ALL, "component": "charts"}, "n_clicks")],
        [State("ticker-input", "value")],
        prevent_initial_call=True
    )
    def handle_chart_symbol_click(symbol_clicks, ticker_value):
        """Handle symbol button clicks for charts with immediate visual feedback"""
        if not any(symbol_clicks) or not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Find which button was clicked
        button_id = ctx.triggered[0]["prop_id"]
        if "symbol-btn" in button_id:
            # Extract index from the button ID
            import json
            button_data = json.loads(button_id.split('.')[0])
            clicked_index = button_data["index"]
            
            # Update current symbol
            symbols = _picker_symbols(ticker_value)
            if 0 <= clicked_index < len(symbols):
                app_state.current_symbol = symbols[clicked_index]
                page_number = clicked_index + 1
                
                # ⚡ IMMEDIATE BUTTON UPDATE - No waiting for refresh!
                buttons = []
                for i, symbol in enumerate(symbols):
                    is_active = i == clicked_index  # Active state based on click
                    buttons.append(create_symbol_button(symbol, i, is_active))
                
                if len(symbols) > 1:
                    # Add navigation info
                    nav_info = html.Div([
                        html.I(className="fas fa-chart-line me-2"),
                        f"Charts for {len(symbols)} symbols"
                    ], className="text-muted small text-center mt-2")
                    
                    button_container = html.Div([
                        dbc.ButtonGroup(buttons, className="d-flex flex-wrap justify-content-center"),
                        nav_info
                    ], className="symbol-pagination-wrapper")
                else:
                    button_container = dbc.ButtonGroup(buttons, className="d-flex justify-content-center")
                
                max_pages = max(len(symbols), 1)
                return page_number, page_number, button_container, max_pages, max_pages
        
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    @app.callback(
        [Output("chart-container", "figure"),
         Output("current-symbol-display", "children"),
         Output("chart-store", "data")],
        [Input("period-1d", "n_clicks"),
         Input("period-1w", "n_clicks"),
         Input("period-1mo", "n_clicks"),
         Input("period-1y", "n_clicks"),
         Input("chart-pagination", "active_page"),
         Input("manual-chart-refresh", "n_clicks"),
         Input("ticker-input", "value")],
        [State("chart-store", "data")]
    )
    def update_chart(n_1d, n_1w, n_1mo, n_1y, active_page, manual_refresh, ticker_value, chart_store_data):
        """Update the chart based on period selection or ticker change"""
        symbol = resolve_picker_symbol(
            active_page or 1,
            ticker_value,
            live_symbols=_live_symbols(),
            current_symbol=app_state.current_symbol,
        )
        if not symbol:
            return create_welcome_chart(), "", chart_store_data

        # Determine which input triggered the callback
        triggered_prop = ctx.triggered[0]["prop_id"] if ctx.triggered else None
        # print(f"[CHART] Triggered by: {triggered_prop}")

        # Default period handling
        period_map = {
            "period-1d.n_clicks": "1d",
            "period-1w.n_clicks": "1w",
            "period-1mo.n_clicks": "1mo",
            "period-1y.n_clicks": "1y"
        }

        # Determine selected period
        selected_period = None
        if triggered_prop in period_map:
            selected_period = period_map[triggered_prop]
        elif chart_store_data and "selected_period" in chart_store_data:
            selected_period = chart_store_data["selected_period"]
        else:
            selected_period = "1y"  # Default to 1Y to match button default

        # print(f"[CHART] Using period: {selected_period}")

        # Create chart
        try:
            chart_figure = create_chart(symbol, selected_period)
            symbol_display = f"📈 {symbol.upper()}"
            
            # Update store data
            updated_store_data = chart_store_data or {}
            updated_store_data["selected_period"] = selected_period
            updated_store_data["last_symbol"] = symbol
            updated_store_data["last_updated"] = datetime.now().isoformat()
            
            # print(f"[CHART] Successfully created chart for {symbol} with period {selected_period}")
            return chart_figure, symbol_display, updated_store_data
            
        except Exception as e:
            # print(f"[CHART] Error creating chart for {symbol}: {e}")
            return create_welcome_chart(), f"❌ Error loading {symbol.upper()}", chart_store_data

    @app.callback(
        Output("chart-last-updated", "children"),
        [Input("chart-store", "data")]
    )
    def update_chart_timestamp(chart_store_data):
        """Update the chart last updated timestamp"""
        if not chart_store_data or "last_updated" not in chart_store_data:
            return ""
        
        try:
            last_updated = datetime.fromisoformat(chart_store_data["last_updated"])
            return f"Last updated: {last_updated.strftime('%I:%M:%S %p')}"
        except:
            return ""

    @app.callback(
        [Output("period-1d", "active"),
         Output("period-1w", "active"),
         Output("period-1mo", "active"),
         Output("period-1y", "active")],
        [Input("period-1d", "n_clicks"),
         Input("period-1w", "n_clicks"),
         Input("period-1mo", "n_clicks"),
         Input("period-1y", "n_clicks")]
    )
    def update_active_period_button(n_1d, n_1w, n_1mo, n_1y):
        """Update which period button is active"""
        button_id = ctx.triggered_id if ctx.triggered_id else "period-1y"
        
        return (
            button_id == "period-1d",
            button_id == "period-1w", 
            button_id == "period-1mo",
            button_id == "period-1y"
        ) 