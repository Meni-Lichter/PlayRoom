"""Prediction Panel - Shows forecast and prediction data"""

import customtkinter as ctk
from datetime import date, datetime
from src.analysis.performance_analyzer import PerformanceAnalyzer
from src.analysis.predictor import Predictor
from src.models.mapping import G_entity
from src.utils.date_utils import get_next_period_label


class PredictionPanel:
    """Manages the Prediction panel content and updates"""
    
    def __init__(self, panel_widget, colors, font_sizes, get_font_func):
        """Initialize the prediction panel manager
        
        Args:
            panel_widget: The CTkFrame panel widget
            colors: Dictionary of color constants
            font_sizes: Dictionary of font sizes
            get_font_func: Function to get cached fonts
        Does: Sets up initial state and references for the prediction panel.
        The actual UI content is built in the update() method when an entity is loaded.
        """
        self.panel = panel_widget
        self.COLORS = colors
        self.FONT_SIZES = font_sizes
        self._get_font = get_font_func
        self.content_frame = None
        self.analyzer = PerformanceAnalyzer()
        
        # Config state
        self.entity_obj = None
        self.mode = None
        self.prediction_result = None
        
        # Data limits (set when entity is loaded)
        self.max_years = 10
        self.max_periods = 36
        
        # Defaults
        self.defaults = {
            "granularity": "monthly",
            "method": "avg_last_n_periods",
            "buffer_percentage": 10.0,
            "n_periods": 11,
            "n_years": 3
        }
    
    def update(self, entity_obj, mode):
        """Update panel with prediction data
        Args:
            entity_obj: Room or TwelveNC object
            mode: Current mode ('room' or '12nc')
        Does: Builds the prediction configuration UI and results section based on the provided entity and mode.
        Returns: None
        """
        if not entity_obj or mode not in ["room", "12nc"]:
            return
        
        # Store current entity and mode
        self.entity_obj = entity_obj
        self.mode = mode
        self.prediction_result = None
        
        self.content_frame = self._find_content_frame()
        print(f"[PREDICTION] content_frame found: {self.content_frame is not None}")
        if not self.content_frame:
            print("[PREDICTION] ERROR: No content frame found!")
            return
        
        # Clear existing content
        print(f"[PREDICTION] Clearing {len(self.content_frame.winfo_children())} existing widgets")
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Main container
        container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Check sales data
        print(f"[PREDICTION] Sales history exists: {bool(entity_obj.sales_history)}")
        if not entity_obj.sales_history:
            print("[PREDICTION] No sales data - showing no data message")
            self._show_no_data(container)
            return
        
        # Calculate available data limits
        self._calculate_data_limits()
        
        # Configuration section
        print("[PREDICTION] Creating configuration UI...")
        config_frame = ctk.CTkFrame(container, fg_color=self.COLORS["bg_panel"], corner_radius=10)
        config_frame.pack(fill="x", pady=(0, 10))
        self._build_config_ui(config_frame)
        print("[PREDICTION] Configuration UI created")
        
        # Results section (initially empty)
        print("[PREDICTION] Creating results frame...")
        self.results_frame = ctk.CTkFrame(container, fg_color=self.COLORS["bg_panel"], corner_radius=10)
        self.results_frame.pack(fill="both", expand=True)
        print("[PREDICTION] Update complete!")
    
    def _calculate_data_limits(self):
        """Calculate max periods and years based on available sales data"""
        if not self.entity_obj or not self.entity_obj.sales_history:
            self.max_years = 3
            self.max_periods = 12
            return
        
        # Get all unique dates from sales history
        dates = [record.date for record in self.entity_obj.sales_history]
        if not dates:
            self.max_years = 3
            self.max_periods = 12
            return
        
        # Calculate years span
        min_date = min(dates)
        max_date = max(dates)
        years_span = max_date.year - min_date.year + 1 # Add 1 to include both start and end years 
        self.max_years = max(1, min(years_span, 10))
        
        # Calculate months span (for max periods)
        # We calculate the total number of months between min and max date to determine how many monthly periods we have, then cap it at 36
        months_span = (max_date.year - min_date.year) * 12 + (max_date.month - min_date.month) + 1
        self.max_periods = max(1, min(months_span, 36))  # Cap at 36 months
        
        print(f"[PREDICTION] Data limits: max_years={self.max_years}, max_periods={self.max_periods}")
    
    def _find_content_frame(self):
        """Find the content frame within the panel widget"""
        print(f"[PREDICTION] Searching for content frame in panel: {self.panel}")
        for child in self.panel.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                try:
                    grid_info = child.grid_info()
                    if grid_info and grid_info.get('row') == 1:
                        print(f"[PREDICTION] Found content frame at row 1")
                        return child
                except:
                    continue
        print("[PREDICTION] WARNING: Content frame not found!")
        return None
     
    def _show_no_data(self, parent):
        """Show no data message"""
        print("[PREDICTION] Displaying no data message")
        label = ctk.CTkLabel(
            parent,
            text="No sales data available for predictions",
            font=self._get_font(size=self.FONT_SIZES["body"]),
            text_color=self.COLORS["text_muted"]
        )
        label.pack(pady=50)
        print("[PREDICTION] No data message displayed")
    
    def _build_config_ui(self, parent):
        """Build configuration UI controls"""
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_columnconfigure(3, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            parent,
            text="Configure Prediction",
            font=self._get_font(size=self.FONT_SIZES["label"], weight="bold"),
            text_color=self.COLORS["text_dark"]
        )
        title.grid(row=0, column=0, columnspan=4, padx=15, pady=(15,8), sticky="w")
        
        row = 1
        
        # Row 1: Granularity and Method
        ctk.CTkLabel(parent, text="Granularity:", font=self._get_font(size=self.FONT_SIZES["small"])).grid(
            row=row, column=0, padx=(15,8), pady=4, sticky="w")
        self.granularity_var = ctk.StringVar(value=self.defaults["granularity"])
        granularity_dropdown = ctk.CTkOptionMenu(
            parent, values=["monthly", "quarterly", "yearly"],
            variable=self.granularity_var, command=self._on_granularity_change,
            font=self._get_font(size=self.FONT_SIZES["small"]), width=120, height=28
        )
        granularity_dropdown.grid(row=row, column=1, padx=(0,15), pady=4, sticky="w")
        
        ctk.CTkLabel(parent, text="Method:", font=self._get_font(size=self.FONT_SIZES["small"])).grid(
            row=row, column=2, padx=(15,8), pady=4, sticky="w")
        self.method_var = ctk.StringVar(value=self.defaults["method"])
        method_dropdown = ctk.CTkOptionMenu(
            parent, values=["avg_last_n_periods", "avg_same_period_previous_years"],
            variable=self.method_var, command=self._on_method_change,
            font=self._get_font(size=self.FONT_SIZES["small"]), width=240, height=28
        )
        method_dropdown.grid(row=row, column=3, padx=(0,15), pady=4, sticky="w")
        row += 1
        
        # Row 2: Target Period and Buffer
        self.target_label = ctk.CTkLabel(parent, text="Target:", font=self._get_font(size=self.FONT_SIZES["small"]))
        self.target_label.grid(row=row, column=0, padx=(15,8), pady=4, sticky="w")
        
        # Container for target period widgets
        self.target_container = ctk.CTkFrame(parent, fg_color="transparent")
        self.target_container.grid(row=row, column=1, padx=(0,15), pady=4, sticky="w")
        self.target_row = row
        
        ctk.CTkLabel(parent, text="Buffer %:", font=self._get_font(size=self.FONT_SIZES["small"])).grid(
            row=row, column=2, padx=(15,8), pady=4, sticky="w")
        
        buffer_frame = ctk.CTkFrame(parent, fg_color="transparent")
        buffer_frame.grid(row=row, column=3, padx=(0,15), pady=4, sticky="w")
        
        self.buffer_var = ctk.DoubleVar(value=self.defaults["buffer_percentage"])
        buffer_entry = ctk.CTkEntry(
            buffer_frame, textvariable=self.buffer_var,
            font=self._get_font(size=self.FONT_SIZES["small"]), width=50, height=28
        )
        buffer_entry.pack(side="left", padx=(0,4))
        
        # Up/Down arrows for buffer
        arrows_frame = ctk.CTkFrame(buffer_frame, fg_color="transparent")
        arrows_frame.pack(side="left")
        
        buffer_up = ctk.CTkButton(
            arrows_frame, text="▲", width=20, height=14,
            command=lambda: self._increment_buffer(0.5),
            font=self._get_font(size=self.FONT_SIZES["xsmall"]),
            fg_color=self.COLORS["accent_teal"], hover_color=self.COLORS["accent_teal_hover"]
        )
        buffer_up.pack()
        
        buffer_down = ctk.CTkButton(
            arrows_frame, text="▼", width=20, height=14,
            command=lambda: self._increment_buffer(-0.5),
            font=self._get_font(size=self.FONT_SIZES["xsmall"]),
            fg_color=self.COLORS["accent_teal"], hover_color=self.COLORS["accent_teal_hover"]
        )
        buffer_down.pack()
        row += 1
        
        # Row 3: N Periods (conditional)
        self.n_periods_label = ctk.CTkLabel(
            parent, 
            text=f"N Periods (max {self.max_periods}):", 
            font=self._get_font(size=self.FONT_SIZES["small"])
        )
        
        self.n_periods_frame = ctk.CTkFrame(parent, fg_color="transparent")
        
        # Adjust default if it exceeds available data
        n_periods_default = min(self.defaults["n_periods"], self.max_periods)
        self.n_periods_var = ctk.IntVar(value=n_periods_default)
        self.n_periods_entry = ctk.CTkEntry(
            self.n_periods_frame, textvariable=self.n_periods_var,
            font=self._get_font(size=self.FONT_SIZES["small"]), width=50, height=28
        )
        self.n_periods_entry.pack(side="left", padx=(0,4))
        
        # Up/Down arrows for n_periods
        periods_arrows_frame = ctk.CTkFrame(self.n_periods_frame, fg_color="transparent")
        periods_arrows_frame.pack(side="left")
        
        periods_up = ctk.CTkButton(
            periods_arrows_frame, text="▲", width=20, height=14,
            command=lambda: self._increment_periods(1),
            font=self._get_font(size=self.FONT_SIZES["xsmall"]),
            fg_color=self.COLORS["accent_teal"], hover_color=self.COLORS["accent_teal_hover"]
        )
        periods_up.pack()
        
        periods_down = ctk.CTkButton(
            periods_arrows_frame, text="▼", width=20, height=14,
            command=lambda: self._increment_periods(-1),
            font=self._get_font(size=self.FONT_SIZES["xsmall"]),
            fg_color=self.COLORS["accent_teal"], hover_color=self.COLORS["accent_teal_hover"]
        )
        periods_down.pack()
        self.n_periods_row = row
        row += 1
        
        # Row 4: N Years Back (conditional)
        self.n_years_label = ctk.CTkLabel(
            parent, 
            text=f"N Years (max {self.max_years}):", 
            font=self._get_font(size=self.FONT_SIZES["small"])
        )
        
        self.n_years_frame = ctk.CTkFrame(parent, fg_color="transparent")
        
        # Adjust default if it exceeds available data
        n_years_default = min(self.defaults["n_years"], self.max_years)
        self.n_years_var = ctk.IntVar(value=n_years_default)
        self.n_years_entry = ctk.CTkEntry(
            self.n_years_frame, textvariable=self.n_years_var,
            font=self._get_font(size=self.FONT_SIZES["small"]), width=50, height=28
        )
        self.n_years_entry.pack(side="left", padx=(0,4))
        
        # Up/Down arrows for n_years
        years_arrows_frame = ctk.CTkFrame(self.n_years_frame, fg_color="transparent")
        years_arrows_frame.pack(side="left")
        
        years_up = ctk.CTkButton(
            years_arrows_frame, text="▲", width=20, height=14,
            command=lambda: self._increment_years(1),
            font=self._get_font(size=self.FONT_SIZES["xsmall"]),
            fg_color=self.COLORS["accent_teal"], hover_color=self.COLORS["accent_teal_hover"]
        )
        years_up.pack()
        
        years_down = ctk.CTkButton(
            years_arrows_frame, text="▼", width=20, height=14,
            command=lambda: self._increment_years(-1),
            font=self._get_font(size=self.FONT_SIZES["xsmall"]),
            fg_color=self.COLORS["accent_teal"], hover_color=self.COLORS["accent_teal_hover"]
        )
        years_down.pack()
        self.n_years_row = row
        row += 1
        
        # Generate button
        generate_btn = ctk.CTkButton(
            parent, text="Generate Prediction",
            command=self._generate_prediction,
            font=self._get_font(size=self.FONT_SIZES["small"], weight="bold"),
            fg_color=self.COLORS["accent_teal"], hover_color=self.COLORS["accent_teal_hover"],
            width=200, height=32
        )
        generate_btn.grid(row=row, column=0, columnspan=4, padx=15, pady=(10,15))
        
        # Initial visibility
        self._update_target_period_ui()
        self._on_method_change(self.defaults["method"])
    
    def _on_granularity_change(self, granularity):
        """Handle granularity dropdown change"""
        print(f"[PREDICTION] Granularity changed to: {granularity}")
        self._update_target_period_ui()
    
    def _on_method_change(self, method):
        """Handle method dropdown change"""
        print(f"[PREDICTION] Method changed to: {method}")
        self._update_target_period_ui()
        
        # Show/hide appropriate parameter controls
        if method == "avg_last_n_periods":
            self.n_periods_label.grid(row=self.n_periods_row, column=0, padx=(15,8), pady=4, sticky="w")
            self.n_periods_frame.grid(row=self.n_periods_row, column=1, columnspan=3, padx=(0,15), pady=4, sticky="w")
            self.n_years_label.grid_remove()
            self.n_years_frame.grid_remove()
        else:  # avg_same_period_previous_years
            self.n_periods_label.grid_remove()
            self.n_periods_frame.grid_remove()
            self.n_years_label.grid(row=self.n_years_row, column=0, padx=(15,8), pady=4, sticky="w")
            self.n_years_frame.grid(row=self.n_years_row, column=1, columnspan=3, padx=(0,15), pady=4, sticky="w")
    
    def _increment_buffer(self, amount):
        """Increment buffer percentage by amount"""
        current = self.buffer_var.get()
        new_value = max(0, min(100, current + amount))
        self.buffer_var.set(round(new_value, 1))
    
    def _increment_periods(self, amount):
        """Increment n_periods by amount"""
        current = self.n_periods_var.get()
        new_value = max(1, min(self.max_periods, current + amount))
        self.n_periods_var.set(new_value)
    
    def _increment_years(self, amount):
        """Increment n_years by amount"""
        current = self.n_years_var.get()
        new_value = max(1, min(self.max_years, current + amount))
        self.n_years_var.set(new_value)
    
    def _update_target_period_ui(self):
        """Update target period UI based on method and granularity"""
        # Clear existing widgets
        for widget in self.target_container.winfo_children():
            widget.destroy()
        
        method = self.method_var.get()
        granularity = self.granularity_var.get()
        
        if method == "avg_last_n_periods":
            # Show read-only next period
            next_period = get_next_period_label(granularity)
            label = ctk.CTkLabel(
                self.target_container,
                text=next_period,
                font=self._get_font(size=self.FONT_SIZES["small"]),
                text_color=self.COLORS["text_dark"]
            )
            label.pack(side="left")
        else:  # avg_same_period_previous_years
            # Show dropdowns based on granularity
            today = date.today()
            
            if granularity == "yearly":
                # Year only
                years = [str(y) for y in range(today.year + 1, today.year + 6)]
                self.target_year_var = ctk.StringVar(value=years[0])
                year_dropdown = ctk.CTkOptionMenu(
                    self.target_container, values=years,
                    variable=self.target_year_var,
                    font=self._get_font(size=self.FONT_SIZES["small"]), width=80, height=28
                )
                year_dropdown.pack(side="left")
            
            elif granularity == "quarterly":
                # Year + Quarter
                years = [str(y) for y in range(today.year, today.year + 6)]
                self.target_year_var = ctk.StringVar(value=years[0])
                year_dropdown = ctk.CTkOptionMenu(
                    self.target_container, values=years,
                    variable=self.target_year_var, command=self._validate_future_selection,
                    font=self._get_font(size=self.FONT_SIZES["small"]), width=80, height=28
                )
                year_dropdown.pack(side="left", padx=(0,4))
                
                quarters = ["Q1", "Q2", "Q3", "Q4"]
                # Default to next quarter
                current_q = (today.month - 1) // 3 + 1
                next_q = current_q + 1 if current_q < 4 else 1
                self.target_quarter_var = ctk.StringVar(value=f"Q{next_q}")
                quarter_dropdown = ctk.CTkOptionMenu(
                    self.target_container, values=quarters,
                    variable=self.target_quarter_var, command=self._validate_future_selection,
                    font=self._get_font(size=self.FONT_SIZES["small"]), width=60, height=28
                )
                quarter_dropdown.pack(side="left")
            
            elif granularity == "monthly":
                # Year + Month
                years = [str(y) for y in range(today.year, today.year + 6)]
                self.target_year_var = ctk.StringVar(value=years[0])
                year_dropdown = ctk.CTkOptionMenu(
                    self.target_container, values=years,
                    variable=self.target_year_var, command=self._validate_future_selection,
                    font=self._get_font(size=self.FONT_SIZES["small"]), width=80, height=28
                )
                year_dropdown.pack(side="left", padx=(0,4))
                
                months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                # Default to next month
                next_month_idx = today.month if today.month < 12 else 0
                self.target_month_var = ctk.StringVar(value=months[next_month_idx])
                month_dropdown = ctk.CTkOptionMenu(
                    self.target_container, values=months,
                    variable=self.target_month_var, command=self._validate_future_selection,
                    font=self._get_font(size=self.FONT_SIZES["small"]), width=60, height=28
                )
                month_dropdown.pack(side="left")
    
    def _validate_future_selection(self, *args):
        """Validate that selected period is in the future"""
        # This could show a warning if past is selected, but for now we trust the user
        pass
    
    def _get_target_time(self) -> str:
        """Build target time string from UI widgets"""
        method = self.method_var.get()
        granularity = self.granularity_var.get()
        
        if method == "avg_last_n_periods":
            return get_next_period_label(granularity)
        else:
            # Build from dropdowns
            year = self.target_year_var.get()
            
            if granularity == "yearly":
                return year
            elif granularity == "quarterly":
                quarter = self.target_quarter_var.get()
                return f"{year}-{quarter}"
            elif granularity == "monthly":
                month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                month_str = self.target_month_var.get()
                month_num = month_names.index(month_str) + 1
                return f"{month_num:02d}-{year}"
        
        return ""
    
    def _generate_prediction(self):
        """Generate prediction with configured parameters"""
        print("\n[PREDICTION] ===== GENERATE PREDICTION CLICKED =====")
        try:
            if not self.entity_obj:
                print("[PREDICTION] ERROR: No entity object")
                self._show_error("No entity selected")
                return
            
            # Parse inputs
            method = self.method_var.get()
            granularity = self.granularity_var.get()
            target_time = self._get_target_time()
            buffer = float(self.buffer_var.get())
            print(f"[PREDICTION] Config: method={method}, granularity={granularity}, target={target_time}, buffer={buffer}%")
            
            # Analyze performance with selected granularity
            entity_type = "room" if self.mode == "room" else "12NC"
            g_entity = G_entity(g_entity=self.entity_obj, entity_type=entity_type)
            
            # Clamp lookback to available data
            if method == "avg_same_period_previous_years":
                lookback = min(int(self.n_years_var.get()), self.max_years)
                print(f"[PREDICTION] Using lookback={lookback} years (max available: {self.max_years})")
            else:
                lookback = 3
            
            print(f"[PREDICTION] Analyzing performance: type={entity_type}, granularity={granularity}, lookback={lookback}")
            performance = self.analyzer.analyze(g_entity, lookback_years=lookback, granularity=granularity)
            print(f"[PREDICTION] Performance analyzed: {performance}")
            
            # Create predictor
            print("[PREDICTION] Creating Predictor...")
            predictor = Predictor(performance)
            print(f"[PREDICTION] Predictor created: {predictor}")
            
            # Generate prediction
            kwargs = {
                "target_time": target_time,
                "method": method,
                "buffer_percentage": buffer
            }
            if method == "avg_last_n_periods":
                # Clamp n_periods to available data
                n_periods = min(int(self.n_periods_var.get()), self.max_periods)
                kwargs["n_periods"] = n_periods
                print(f"[PREDICTION] Using n_periods={n_periods} (max available: {self.max_periods})")
            
            print(f"[PREDICTION] Calling predictor.predict with: {kwargs}")
            self.prediction_result = predictor.predict(**kwargs)
            print(f"[PREDICTION] Prediction result: {self.prediction_result}")
            print("[PREDICTION] Showing results...")
            self._show_results()
            print("[PREDICTION] ===== GENERATION COMPLETE =====")
            
        except Exception as e:
            print(f"[PREDICTION] ERROR during generation: {e}")
            import traceback
            traceback.print_exc()
            self._show_error(str(e))
    
    def _show_results(self):
        """Display prediction results"""
        print(f"[PREDICTION] _show_results called, result={self.prediction_result}")
        # Clear results frame
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        if not self.prediction_result:
            print("[PREDICTION] No prediction result to show")
            return
        
        pred = self.prediction_result
        print(f"[PREDICTION] Building results UI for: period={pred.period_label}, method={pred.method}")
        
        # Title
        title = ctk.CTkLabel(
            self.results_frame,
            text="Prediction Results",
            font=self._get_font(size=self.FONT_SIZES["label"], weight="bold"),
            text_color=self.COLORS["text_dark"]
        )
        title.pack(padx=15, pady=(15,8), anchor="w")
        
        # Results grid
        grid = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=15, pady=(0,15))
        
        results = [
            ("Granularity", self.granularity_var.get().title()),
            ("Period", pred.period_label),
            ("Method", pred.method.replace("_", " ").title()),
            ("Baseline", f"{pred.baseline:.1f}"),
            ("Buffer %", f"{pred.buffer_percentage:.1f}%"),
            ("Buffer Amount", f"{pred.buffer_amount:.1f}"),
            ("Predicted Quantity", f"{pred.predicted_quantity:.1f}")
        ]
        
        for i, (label, value) in enumerate(results):
            is_final = (i == len(results) - 1)
            
            lbl = ctk.CTkLabel(
                grid, text=f"{label}:",
                font=self._get_font(size=self.FONT_SIZES["small"], weight="bold" if is_final else "normal"),
                text_color=self.COLORS["accent_teal"] if is_final else self.COLORS["text_dark"]
            )
            lbl.grid(row=i, column=0, padx=(0,15), pady=3, sticky="w")
            
            val = ctk.CTkLabel(
                grid, text=value,
                font=self._get_font(size=self.FONT_SIZES["small"], weight="bold" if is_final else "normal"),
                text_color=self.COLORS["accent_teal"] if is_final else self.COLORS["text_dark"]
            )
            val.grid(row=i, column=1, pady=3, sticky="w")
        
        print("[PREDICTION] Results UI complete!")
    
    def _show_error(self, message):
        """Display error message"""
        print(f"[PREDICTION] Showing error: {message}")
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        error_label = ctk.CTkLabel(
            self.results_frame,
            text=f"Error: {message}",
            font=self._get_font(size=self.FONT_SIZES["small"]),
            text_color="red"
        )
        error_label.pack(padx=15, pady=15)
