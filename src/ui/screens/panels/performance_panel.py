"""Performance Panel - Shows sales history and performance metrics"""

import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import calendar

from src.analysis.performance_analyzer import PerformanceAnalyzer
from src.models.performance import PerformanceData, TimePeriod
from src.models.mapping import G_entity


class PerformancePanel:
    """Manages the Performance panel content and updates"""
    
    def __init__(self, panel_widget, colors, font_sizes, get_font_func):
        """Initialize the performance panel manager
        
        Args:
            panel_widget: The CTkFrame panel widget
            colors: Dictionary of color constants
            font_sizes: Dictionary of font sizes
            get_font_func: Function to get cached fonts
        """
        self.panel = panel_widget
        self.COLORS = colors
        self.FONT_SIZES = font_sizes
        self._get_font = get_font_func
        self.content_frame = None
        
        # Initialize the performance analyzer
        self.analyzer = PerformanceAnalyzer()
        
        # Chart state
        self.entity_obj = None
        self.mode = None
        self.granularity = "Months"  # UI granularity
        self.selected_years = set()  # Years to display
        self.time_range = (0, 11)  # Default: full range (12 periods for months)
        
        # Map UI granularities to analyzer granularities
        self.granularity_map = {
            "Months": "monthly",
            "Quarters": "quarterly",
            "Years": "yearly"
        }
        
        # Year colors
        self.year_colors = {
            2026: "#FF8C42",  # Orange
            2025: "#4A90E2",  # Blue
            2024: "#50C878",  # Green
            2023: "#9E9E9E",  # Grey
            2022: "#9C27B0",  # Purple
        }
        
        # UI components
        self.canvas = None
        self.figure = None
        self.ax = None
        self.year_checkboxes = {}
        self.range_dropdown_start = None
        self.range_dropdown_end = None
        self.granularity_dropdown = None
    
    def update(self, entity_obj, mode):
        """Update panel with sales performance data
        
        Args:
            entity_obj: Room or TwelveNC object
            mode: Current mode ('room' or '12nc')
        """
        # Store entity and mode
        self.entity_obj = entity_obj
        self.mode = mode
        
        # Find the content frame in the panel
        self.content_frame = self._find_content_frame()
        
        if not self.content_frame:
            return
        
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Check if there are sales records
        if not entity_obj.sales_history:
            no_data_label = ctk.CTkLabel(
                self.content_frame,
                text="No sales data available",
                font=self._get_font(size=self.FONT_SIZES["body"]),
                text_color=self.COLORS["text_light"]
            )
            no_data_label.pack(pady=20)
            return
        
        # Initialize selected years (default: all available years)
        available_years = self._get_available_years()
        self.selected_years = set(available_years)
        
        # Build the UI
        self._build_ui()
        
        # Initial chart render
        self._update_chart()
    
    def _find_content_frame(self):
        """Find the content frame within the panel widget
        Args:None 
        Does: Searches for a CTkFrame in the panel's children that is located at grid row=1, which is where we expect the content to be.
        Returns: The content frame widget if found, otherwise None.
        """
        # Look for the content frame at grid row=1
        for child in self.panel.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                try:
                    grid_info = child.grid_info()
                    if grid_info and grid_info.get('row') == 1:
                        return child
                except:
                    continue
        return None
    
    def _get_available_years(self) -> List[int]:
        """Get list of years present in sales data, limited to last 4 years from most recent
        Args: None
        Does: Extracts the years from the sales history of the current entity object.
        Returns: A list of up to 4 most recent years.
        """
        if not self.entity_obj or not self.entity_obj.sales_history:
            return []
        
        years = set(record.date.year for record in self.entity_obj.sales_history)
        sorted_years = sorted(years, reverse=True)
        # Return up to 4 most recent years
        return sorted_years[:4]
    
    def _build_ui(self):
        """Build the complete UI with controls and chart
        Args: None
        Does: Creates the main container, controls panel, and chart area within the content frame.
        Returns: None
        """
        # Main container
        main_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Controls panel at the top
        controls_frame = ctk.CTkFrame(
            main_frame,
            fg_color=self.COLORS["bg_light"],
            corner_radius=8
        )
        controls_frame.pack(fill="x", pady=(0, 15))
        
        self._build_controls(controls_frame)
        
        # Chart area
        chart_frame = ctk.CTkFrame(
            main_frame,
            fg_color=self.COLORS["bg_white"],
            corner_radius=8
        )
        chart_frame.pack(fill="both", expand=True)
        
        self._build_chart(chart_frame)
    
    def _build_controls(self, parent):
        """Build control widgets (granularity dropdown, time range dropdowns, year checkboxes)
        Args:
            parent: Parent frame for controls
        Does: Creates the controls for adjusting the chart, including a dropdown for granularity,
        dropdowns for time range selection (start/end), and checkboxes for selecting years.
        Returns: None
        """
        # Outer frame for centering
        outer_frame = ctk.CTkFrame(parent, fg_color="transparent")
        outer_frame.pack(fill="x", padx=20, pady=15)
        
        # Inner frame with all controls - centered
        controls_frame = ctk.CTkFrame(outer_frame, fg_color="transparent")
        controls_frame.pack(anchor="center")
        
        # 1. Granularity dropdown
        granularity_label = ctk.CTkLabel(
            controls_frame,
            text="Granularity:",
            font=self._get_font(size=self.FONT_SIZES["small"], weight="bold"),
            text_color=self.COLORS["text_dark"]
        )
        granularity_label.pack(side="left", padx=(0, 10))
        
        self.granularity_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            values=["Months", "Quarters", "Years"],
            command=self._on_granularity_change,
            width=120,
            fg_color=self.COLORS["accent_teal"],
            button_color=self.COLORS["accent_teal"],
            button_hover_color="#1C7A7A"
        )
        self.granularity_dropdown.set(self.granularity)
        self.granularity_dropdown.pack(side="left", padx=(0, 30))
        
        # 2. Time Range dropdowns
        time_range_label = ctk.CTkLabel(
            controls_frame,
            text="Time Range:",
            font=self._get_font(size=self.FONT_SIZES["small"], weight="bold"),
            text_color=self.COLORS["text_dark"]
        )
        time_range_label.pack(side="left", padx=(0, 10))
        
        # From dropdown
        from_label = ctk.CTkLabel(
            controls_frame,
            text="From:",
            font=self._get_font(size=self.FONT_SIZES["small"]),
            text_color=self.COLORS["text_muted"]
        )
        from_label.pack(side="left", padx=(0, 5))
        
        all_periods = self._get_all_period_labels()
        self.range_dropdown_start = ctk.CTkOptionMenu(
            controls_frame,
            values=all_periods if all_periods else ["1"],
            command=lambda _: self._on_range_change(None),
            width=100,
            fg_color=self.COLORS["accent_teal"],
            button_color=self.COLORS["accent_teal"],
            button_hover_color="#1C7A7A"
        )
        self.range_dropdown_start.set(all_periods[0] if all_periods else "1")
        self.range_dropdown_start.pack(side="left", padx=(0, 15))
        
        # To dropdown
        to_label = ctk.CTkLabel(
            controls_frame,
            text="To:",
            font=self._get_font(size=self.FONT_SIZES["small"]),
            text_color=self.COLORS["text_muted"]
        )
        to_label.pack(side="left", padx=(0, 5))
        
        max_periods = self._get_max_periods()
        self.range_dropdown_end = ctk.CTkOptionMenu(
            controls_frame,
            values=all_periods if all_periods else ["1"],
            command=lambda _: self._on_range_change(None),
            width=100,
            fg_color=self.COLORS["accent_teal"],
            button_color=self.COLORS["accent_teal"],
            button_hover_color="#1C7A7A"
        )
        end_idx = max_periods - 1 if all_periods else 0
        self.range_dropdown_end.set(all_periods[end_idx] if all_periods and end_idx < len(all_periods) else "1")
        self.range_dropdown_end.pack(side="left", padx=(0, 30))
        
        # 3. Year checkboxes
        years_label = ctk.CTkLabel(
            controls_frame,
            text="Years:",
            font=self._get_font(size=self.FONT_SIZES["small"], weight="bold"),
            text_color=self.COLORS["text_dark"]
        )
        years_label.pack(side="left", padx=(0, 10))
        
        available_years = self._get_available_years()
        for year in available_years:
            color = self.year_colors.get(year, "#666666")
            
            checkbox = ctk.CTkCheckBox(
                controls_frame,
                text=str(year),
                command=lambda y=year: self._on_year_toggle(y),
                font=self._get_font(size=self.FONT_SIZES["small"]),
                fg_color=color,
                hover_color=color,
                border_color=color
            )
            checkbox.select()  # Default: all selected
            checkbox.pack(side="left", padx=(0, 15))
            
            self.year_checkboxes[year] = checkbox
    
    def _build_chart(self, parent):
        """Build matplotlib chart
        Args:
            parent: Parent frame for chart
        Does: Initializes the matplotlib figure and canvas for displaying the sales performance chart.
        Returns: None
        """
        # Header frame for title and sum
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(15,0))
        
        # Sum label at the top right
        self.sum_label = ctk.CTkLabel(
            header_frame,
            text="Total: 0",
            font=self._get_font(size=self.FONT_SIZES["body"], weight="bold"),
            text_color=self.COLORS["accent_teal"]
        )
        self.sum_label.pack(side="right")
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(10, 6), dpi=100, facecolor='white')
        self.ax = self.figure.add_subplot(111)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.figure, parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=15, pady=(5,15))
    
    def _get_max_periods(self) -> int:
        """Get maximum number of periods based on granularity"""
        granularity_periods = {
            "Months": 12,
            "Quarters": 4,
            "Years": 3
        }
        return granularity_periods.get(self.granularity, 12)
    
    def _aggregate_sales_data(self) -> Dict[int, Dict[str, int]]:
        """Aggregate sales data by year and time period using PerformanceAnalyzer
        
        Args: None
        Does: Analyzes sales data for the last 3 years combined using PerformanceAnalyzer,
              then groups results by year for display.
        Returns:
            Dictionary: {year: {period_label: quantity}}
            For example: {2024: {"Jan": 100, "Feb": 150}, 2023: {"Jan": 80, "Feb": 120}}
        """
        if not self.entity_obj or not self.entity_obj.sales_history:
            return {}
        
        # Get analyzer granularity from UI granularity
        analyzer_granularity = self.granularity_map.get(self.granularity, "monthly")
        
        try:
            # Wrap entity_obj in G_entity for analyzer
            entity_type = "12NC" if self.mode == "12nc" else "room"
            g_entity_obj = G_entity(g_entity=self.entity_obj, entity_type=entity_type)
            
            # Analyze using PerformanceAnalyzer for the last 4 years
            performance_data: PerformanceData = self.analyzer.analyze(
                analyzed_obj=g_entity_obj,
                lookback_years=4,
                granularity=analyzer_granularity
            )
            
            # Group periods by year
            data = {}
            for period in performance_data.periods:
                # Extract year from period label
                year = self._extract_year_from_period(period.label, analyzer_granularity)
                if year is None:
                    continue
                    
                # Convert period label to UI format
                ui_label = self._convert_period_label_to_ui(period.label, analyzer_granularity)
                
                # Initialize year dict if needed
                if year not in data:
                    data[year] = {}
                
                data[year][ui_label] = period.quantity
            
            return data
            
        except Exception as e:
            print(f"Error analyzing sales data: {e}")
            return {}
    
    def _extract_year_from_period(self, period_label: str, analyzer_granularity: str) -> int | None:
        """Extract year from analyzer period label
        
        Args:
            period_label: Period label from analyzer (e.g., "03-2024", "2024-Q1", "2024")
            analyzer_granularity: The granularity used by analyzer
            
        Returns:
            Year as integer, or None if cannot be extracted
        """
        try:
            if analyzer_granularity == "monthly":
                # Format: "03-2024" -> 2024
                return int(period_label.split("-")[1])
            elif analyzer_granularity == "quarterly":
                # Format: "2024-Q1" -> 2024
                return int(period_label.split("-")[0])
            elif analyzer_granularity == "yearly":
                # Format: "2024" -> 2024
                return int(period_label)
        except (ValueError, IndexError):
            return None
        return None
    
    def _convert_period_label_to_ui(self, period_label: str, analyzer_granularity: str) -> str:
        """Convert analyzer period label to UI-friendly format
        
        Args:
            period_label: Period label from analyzer (e.g., "03-2024", "2024-Q1")
            analyzer_granularity: The granularity used by analyzer
            
        Returns:
            UI-friendly label (e.g., "Mar", "Q1", "2024")
        """
        try:
            if analyzer_granularity == "monthly":
                # Format: "03-2024" -> "Mar"
                month_num = int(period_label.split("-")[0])
                return calendar.month_abbr[month_num]
            elif analyzer_granularity == "quarterly":
                # Format: "2024-Q1" -> "Q1"
                parts = period_label.split("-")
                return parts[1] if len(parts) > 1 else period_label
            elif analyzer_granularity == "yearly":
                # Format: "2024" -> "2024"
                return period_label
        except (ValueError, IndexError):
            pass
        return period_label
    
    def _get_all_period_labels(self) -> List[str]:
        """Get all possible period labels for current granularity
        
        Returns:
            List of period labels in order
        """
        if self.granularity == "Months":
            return [calendar.month_abbr[i] for i in range(1, 13)]
        elif self.granularity == "Quarters":
            return ["Q1", "Q2", "Q3", "Q4"]
        elif self.granularity == "Years":
            available_years = self._get_available_years()
            return [str(year) for year in sorted(available_years)]
        return []
    
    def _update_chart(self):
        """Update the bar chart with current setting
        Args: None
        Does: Clears the existing chart and redraws it based on the current selected years, time range, and granularity.
              It uses the aggregated sales data to plot bars for each period and year.
        Returns: None
        """
        if not self.ax:
            return
        
        # Clear previous chart
        self.ax.clear()
        
        # Get aggregated data
        data = self._aggregate_sales_data()
        
        # Get all period labels
        all_periods = self._get_all_period_labels()
        
        # Apply time range filter
        start_idx = int(self.time_range[0])
        end_idx = int(self.time_range[1])
        filtered_periods = all_periods[start_idx:end_idx + 1]
        
        if not filtered_periods:
            self.ax.text(0.5, 0.5, 'No data to display',
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=self.ax.transAxes,
                        fontsize=14, color='#666666')
            if self.canvas:
                self.canvas.draw()
            return
        
        # Prepare data for plotting
        x_positions = list(range(len(filtered_periods)))
        
        # For yearly granularity, show single bars (periods ARE years)
        if self.granularity == "Years":
            values = []
            colors = []
            for period in filtered_periods:
                # Get the year value from data
                try:
                    year = int(period)
                    if year in data and period in data[year]:
                        values.append(data[year][period])
                        colors.append(self.year_colors.get(year, "#666666"))
                    else:
                        values.append(0)
                        colors.append("#CCCCCC")
                except ValueError:
                    values.append(0)
                    colors.append("#CCCCCC")
            
            bars = self.ax.bar(
                x_positions,
                values,
                width=0.6,
                color=colors,
                alpha=0.9,
                edgecolor='white',
                linewidth=1
            )
            
            # Add value labels on top of bars
            self.add_bar_values(bars, values)

        else:
            # For monthly/quarterly: group bars by year
            bar_width = 0.8 / max(len(self.selected_years), 1)
            
            # Plot bars for each selected year
            for i, year in enumerate(sorted(self.selected_years)):
                if year not in data:
                    continue
                
                year_data = data[year]
                values = [year_data.get(period, 0) for period in filtered_periods]
                
                # Calculate x offset for grouped bars
                offset = (i - len(self.selected_years) / 2 + 0.5) * bar_width
                x_positions_offset = [x + offset for x in x_positions]
                
                color = self.year_colors.get(year, "#666666")
                bars = self.ax.bar(
                    x_positions_offset,
                    values,
                    width=bar_width,
                    label=str(year),
                    color=color,
                    alpha=0.9,
                    edgecolor='white',
                    linewidth=1
                )
                
                # Add value labels on top of bars
                self.add_bar_values(bars, values)

        # Customize chart
        self.ax.set_xlabel('Time Period', fontsize=11, fontweight='bold', color='#333333')
        self.ax.set_ylabel('Sales Quantity', fontsize=11, fontweight='bold', color='#333333')
        self.ax.set_title(f'Sales History ({self.granularity})', 
                         fontsize=13, fontweight='bold', color='#333333', pad=15)
        
        # Set x-axis labels
        self.ax.set_xticks(x_positions)
        self.ax.set_xticklabels(filtered_periods, rotation=45, ha='right')
        
        # Customize grid
        self.ax.grid(True, axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
        self.ax.set_axisbelow(True)
        
        # Legend (only for monthly/quarterly where we have grouped bars by year)
        if self.selected_years and self.granularity != "Years":
            self.ax.legend(loc='upper right', framealpha=0.9, edgecolor='#CCCCCC')
        
        # Calculate and update total sum
        total_sum = 0
        for year in self.selected_years:
            if year in data:
                for period in filtered_periods:
                    if period in data[year]:
                        total_sum += data[year][period]
        
        if hasattr(self, 'sum_label'):
            self.sum_label.configure(text=f"Total: {int(total_sum)}")
        
        # Tight layout
        if self.figure:
            self.figure.tight_layout()
        
        # Redraw canvas
        if self.canvas:
            self.canvas.draw()
    
    def _on_granularity_change(self, new_granularity: str):
        """Handle granularity dropdown change
        Args:
            new_granularity: New granularity value
        Does: Updates the granularity state, resets the time range to match the new granularity, 
        updates the range dropdowns, and refreshes the chart.
        Returns: None
        """
        self.granularity = new_granularity
        
        # Reset time range
        max_periods = self._get_max_periods()
        self.time_range = (0, max_periods - 1)
        
        # Update dropdowns
        if self.range_dropdown_start and self.range_dropdown_end:
            all_periods = self._get_all_period_labels()
            
            # Update dropdown values
            self.range_dropdown_start.configure(values=all_periods)
            self.range_dropdown_end.configure(values=all_periods)
            
            # Set default selections
            self.range_dropdown_start.set(all_periods[0] if all_periods else "1")
            self.range_dropdown_end.set(all_periods[max_periods - 1] if all_periods and max_periods - 1 < len(all_periods) else all_periods[-1] if all_periods else "1")
        
        # Update chart
        self._update_chart()
    
    def _on_year_toggle(self, year: int):
        """Handle year checkbox toggle
        Args:
            year: Year that was toggled
        Does: Adds or removes the year from the selected_years set based on the checkbox state, 
              and for yearly granularity adjusts dropdowns to match the selected year range, then updates the chart.
        Returns: None
        """
        if year in self.selected_years:
            self.selected_years.remove(year)
        else:
            self.selected_years.add(year)
        
        # For yearly granularity: sync dropdowns with selected years
        if self.granularity == "Years" and self.selected_years:
            all_periods = self._get_all_period_labels()
            
            # Find the range that includes all selected years
            selected_year_indices = []
            for idx, period in enumerate(all_periods):
                try:
                    period_year = int(period)
                    if period_year in self.selected_years:
                        selected_year_indices.append(idx)
                except ValueError:
                    pass
            
            if selected_year_indices:
                # Set dropdowns to span from min to max selected year
                min_idx = min(selected_year_indices)
                max_idx = max(selected_year_indices)
                
                if self.range_dropdown_start and self.range_dropdown_end:
                    self.range_dropdown_start.set(all_periods[min_idx])
                    self.range_dropdown_end.set(all_periods[max_idx])
                    self.time_range = (min_idx, max_idx)
        
        # Update chart
        self._update_chart()
    
    def _on_range_change(self, value):
        """Handle range dropdown change
        Args:
            value: Dropdown value (not used, we read directly from dropdowns)
        Does: Updates the time range based on the dropdown selections, ensures start <= end, and refreshes the chart.
        Returns: None
        """
        # Validate dropdowns exist
        if not self.range_dropdown_start or not self.range_dropdown_end:
            return
        
        all_periods = self._get_all_period_labels()
        if not all_periods:
            return
        
        # Get selected values
        start_value = self.range_dropdown_start.get()
        end_value = self.range_dropdown_end.get()
        
        # Find indices
        try:
            start = all_periods.index(start_value)
            end = all_periods.index(end_value)
        except ValueError:
            return
        
        # Ensure start <= end
        if start > end:
            # Swap to maintain valid range
            start, end = end, start
            self.range_dropdown_start.set(all_periods[start])
            self.range_dropdown_end.set(all_periods[end])
        
        self.time_range = (start, end)
        
        # For yearly granularity: sync checkboxes with visible year range
        if self.granularity == "Years":
            visible_periods = all_periods[start:end + 1]
            visible_years = set()
            for period in visible_periods:
                try:
                    visible_years.add(int(period))
                except ValueError:
                    pass
            
            # Update checkboxes and selected_years to match visible range
            for year, checkbox in self.year_checkboxes.items():
                if year in visible_years:
                    if year not in self.selected_years:
                        self.selected_years.add(year)
                        checkbox.select()
                else:
                    if year in self.selected_years:
                        self.selected_years.remove(year)
                        checkbox.deselect()
        
        # Update chart
        self._update_chart()

    def add_bar_values(self, bars, values):
        """Add value labels on top of bars in the chart
        Args:
            bars: The bar containers returned by ax.bar()
            values: The corresponding values for each bar
        Does: Iterates through the bars and adds a text label on top of each bar that has a value greater than 0.
        Returns: None
        """
        # Validate inputs
        if not bars or not values:
            return
        
        for bar, value in zip(bars, values):
            if value > 0:
                height = bar.get_height()
                if self.ax:
                    self.ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        height,
                        f'{int(value)}',
                        ha='center',
                        va='bottom',
                        fontsize=8,
                        fontweight='bold',
                        color='#333333'
                    )
