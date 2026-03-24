"""Entity Mode Screen - Shared by 12NC and Room analysis modes"""

import customtkinter as ctk
from datetime import datetime
import tkinter as tk
from tkinter import Listbox


class EntityModeScreen(ctk.CTkFrame):
    """Main analysis screen with 2x2 grid layout for 12NC and Room modes"""
    
    def __init__(self, parent, app_controller, mode="12nc"):
        super().__init__(parent, fg_color="#EEF2F6")
        
        self.app_controller = app_controller
        self.current_mode = mode  # "12nc" or "room"
        self.selected_entity = None
        
        # Sample data for autocomplete (will be replaced with real data)
        self.sample_12nc_items = [
            "12NC-001234", "12NC-002345", "12NC-003456", "12NC-004567",
            "12NC-005678", "12NC-006789", "12NC-007890", "12NC-008901"
        ]
        self.sample_room_items = [
            "Room-A101", "Room-A102", "Room-B201", "Room-B202",
            "Room-C301", "Room-C302", "Room-D401", "Room-D402"
        ]
        
        # Store all items for current mode (for filtering)
        self.all_items = self.sample_12nc_items if mode == "12nc" else self.sample_room_items
        
        # Configure grid weights for responsive layout
        self.grid_rowconfigure(0, weight=0)  # Title header (fixed)
        self.grid_rowconfigure(1, weight=0)  # Search area (fixed)
        self.grid_rowconfigure(2, weight=1)  # Top row panels
        self.grid_rowconfigure(3, weight=1)  # Bottom row panels
        self.grid_columnconfigure(0, weight=1)  # Left column
        self.grid_columnconfigure(1, weight=1)  # Right column
        
        # Create UI components
        self._create_title_header()
        self._create_search_area()
        self._create_grid_panels()
    
    def _create_title_header(self):
        """Create title and description header"""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 15))
        
        # Title
        mode_title = "12NC Component Analysis" if self.current_mode == "12nc" else "Room Performance Analysis"
        self.title_label = ctk.CTkLabel(
            header_frame,
            text=mode_title,
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color="#1E2A33"
        )
        self.title_label.pack()
        
        # Description
        mode_desc = "Search and analyze component performance, belonging relationships, and demand forecasts" if self.current_mode == "12nc" else "Analyze room performance metrics, deployed components, and predict future demand"
        self.description_label = ctk.CTkLabel(
            header_frame,
            text=mode_desc,
            font=ctk.CTkFont(family="Segoe UI", size=15),
            text_color="#5F6E7C"
        )
        self.description_label.pack(pady=(5, 0))
    
    def _create_search_area(self):
        """Create dedicated search area with custom dropdown"""
        search_container = ctk.CTkFrame(self, fg_color="#F8FAFC", corner_radius=0)
        search_container.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 10))
        
        # Inner frame for search components
        search_frame = ctk.CTkFrame(search_container, fg_color="#FFFFFF", corner_radius=12, border_width=2, border_color="#4A8F93")
        search_frame.pack(fill="x", padx=10, pady=10)
        
        # Search content
        content_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=15, pady=15)
        
        # Search icon and label
        label_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        label_frame.pack(side="left", padx=(0, 15))
        
        search_label = ctk.CTkLabel(
            label_frame,
            text="🔍 Search:",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#1E2A33"
        )
        search_label.pack()
        
        mode_hint = ctk.CTkLabel(
            label_frame,
            text=f"({self.current_mode.upper()})",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#8A98A6"
        )
        mode_hint.pack()
        self.search_mode_hint = mode_hint
        
        # Search entry
        entry_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        entry_frame.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search_change)
        
        self.search_entry = ctk.CTkEntry(
            entry_frame,
            textvariable=self.search_var,
            placeholder_text=f"Type to search {self.current_mode.upper()}...",
            width=400,
            height=45,
            font=ctk.CTkFont(family="Segoe UI", size=15),
            fg_color="#FFFFFF",
            border_color="#D8E0E8",
            border_width=2,
            text_color="#1E2A33",
            placeholder_text_color="#8A98A6"
        )
        self.search_entry.pack(fill="x")
        self.search_entry.bind("<FocusIn>", self._on_entry_focus)
        self.search_entry.bind("<FocusOut>", self._on_entry_blur)
        
        # Dropdown list (initially hidden)
        self.dropdown_frame = ctk.CTkFrame(entry_frame, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#D8E0E8")
        
        self.dropdown_listbox = Listbox(
            self.dropdown_frame,
            font=("Segoe UI", 13),
            bg="#FFFFFF",
            fg="#1E2A33",
            selectbackground="#E3EDF5",
            selectforeground="#1E2A33",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            height=8
        )
        self.dropdown_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.dropdown_listbox.bind("<<ListboxSelect>>", self._on_dropdown_select)
        self.dropdown_listbox.bind("<Button-1>", self._on_dropdown_click)
        
        self.dropdown_visible = False
        
        # Search button
        search_btn = ctk.CTkButton(
            content_frame,
            text="Search",
            command=self._on_search_button,
            width=120,
            height=45,
            corner_radius=8,
            fg_color="#35586E",
            hover_color="#2F4F63",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold")
        )
        search_btn.pack(side="left")
        self._create_tooltip(search_btn, f"Search for {self.current_mode.upper()}")
    
    def _create_grid_panels(self):
        """Create 2x2 grid with four main panels"""
        # Top-left: Belonging List
        self.belonging_panel = self._create_panel(
            row=2, column=0,
            title="📦 Belonging List",
            content_text="Selected entity and related items will appear here"
        )
        
        # Top-right: Details
        self.details_panel = self._create_panel(
            row=2, column=1,
            title="ℹ️ Details",
            content_text="Entity information and metadata"
        )
        
        # Bottom-left: Performance
        self.performance_panel = self._create_panel(
            row=3, column=0,
            title="📈 Performance",
            content_text="Historical sales chart will appear here"
        )
        
        # Bottom-right: Prediction
        self.prediction_panel = self._create_panel(
            row=3, column=1,
            title="🔮 Prediction",
            content_text="Forecast and prediction data"
        )
    
    def _create_panel(self, row, column, title, content_text):
        """Create a single panel in the grid"""
        # Panel container
        panel = ctk.CTkFrame(
            self,
            fg_color="#F8FAFC",
            corner_radius=12,
            border_width=1,
            border_color="#D8E0E8"
        )
        panel.grid(row=row, column=column, sticky="nsew", padx=10, pady=10)
        
        # Configure panel grid
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)
        
        # Panel header
        header = ctk.CTkFrame(panel, fg_color="#FFFFFF", corner_radius=0, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        
        # Title
        title_label = ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#1E2A33",
            anchor="w"
        )
        title_label.pack(side="left", padx=20, pady=15)
        
        # Export buttons frame
        export_frame = ctk.CTkFrame(header, fg_color="transparent")
        export_frame.pack(side="right", padx=15)
        
        # Excel export
        excel_btn = ctk.CTkButton(
            export_frame,
            text="📊",
            width=35,
            height=35,
            corner_radius=6,
            fg_color="#E7EDF3",
            hover_color="#DCE4EC",
            text_color="#2B3A44",
            border_width=1,
            border_color="#D8E0E8",
            font=ctk.CTkFont(size=16),
            command=lambda: self._export_panel(title, "excel")
        )
        excel_btn.pack(side="left", padx=2)
        self._create_tooltip(excel_btn, "Export to Excel")
        
        # PNG export
        png_btn = ctk.CTkButton(
            export_frame,
            text="🖼️",
            width=35,
            height=35,
            corner_radius=6,
            fg_color="#E7EDF3",
            hover_color="#DCE4EC",
            text_color="#2B3A44",
            border_width=1,
            border_color="#D8E0E8",
            font=ctk.CTkFont(size=16),
            command=lambda: self._export_panel(title, "png")
        )
        png_btn.pack(side="left", padx=2)
        self._create_tooltip(png_btn, "Export as PNG image")
        
        # Separator
        separator = ctk.CTkFrame(panel, height=1, fg_color="#D8E0E8")
        separator.grid(row=0, column=0, sticky="ews", pady=(60, 0))
        
        # Content area
        content = ctk.CTkFrame(panel, fg_color="#FFFFFF", corner_radius=0)
        content.grid(row=1, column=0, sticky="nsew")
        
        # Placeholder content
        placeholder = ctk.CTkLabel(
            content,
            text=content_text,
            font=ctk.CTkFont(family="Segoe UI", size=16),
            text_color="#8A98A6"
        )
        placeholder.pack(expand=True, pady=50)
        
        # Coming soon label
        coming_soon = ctk.CTkLabel(
            content,
            text=f"Implementation: Stage 3+",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#A8B3BD"
        )
        coming_soon.pack(pady=(0, 50))
        
        return panel
    
    def _on_mode_change(self, value):
        """Handle mode change from side menu (not from toggle)"""
        # This is now called internally when mode changes via side menu
        # Update all items list
        self.all_items = self.sample_12nc_items if self.current_mode == "12nc" else self.sample_room_items
        
        # Update title and description
        mode_title = "12NC Component Analysis" if self.current_mode == "12nc" else "Room Performance Analysis"
        mode_desc = "Search and analyze component performance, belonging relationships, and demand forecasts" if self.current_mode == "12nc" else "Analyze room performance metrics, deployed components, and predict future demand"
        self.title_label.configure(text=mode_title)
        self.description_label.configure(text=mode_desc)
        
        # Update search area
        self.search_entry.configure(placeholder_text=f"Type to search {self.current_mode.upper()}...")
        self.search_mode_hint.configure(text=f"({self.current_mode.upper()})")
        self.search_var.set("")  # Clear search
        self._hide_dropdown()
        
        # Update side menu to highlight the correct button
        screen_name = "12nc_mode" if self.current_mode == "12nc" else "room_mode"
        if hasattr(self.app_controller, 'side_menu'):
            self.app_controller.side_menu._highlight_active_button(screen_name)
        
        print(f"Mode changed to: {self.current_mode}")
    
    def _on_search_change(self, *args):
        """Handle search text changes - filter and show dropdown"""
        search_text = self.search_var.get().strip()
        
        if not search_text:
            self._hide_dropdown()
            return
        
        # Filter items
        filtered = [item for item in self.all_items if search_text.lower() in item.lower()]
        
        # Update listbox
        self.dropdown_listbox.delete(0, tk.END)
        
        if filtered:
            for item in filtered:
                self.dropdown_listbox.insert(tk.END, item)
            self._show_dropdown()
        else:
            self.dropdown_listbox.insert(tk.END, "No matches found")
            self._show_dropdown()
    
    def _on_entry_focus(self, event):
        """Show all items when entry gets focus"""
        if not self.search_var.get().strip():
            # Show all items
            self.dropdown_listbox.delete(0, tk.END)
            for item in self.all_items:
                self.dropdown_listbox.insert(tk.END, item)
            self._show_dropdown()
    
    def _on_entry_blur(self, event):
        """Hide dropdown when losing focus (with delay to allow clicks)"""
        self.after(200, self._check_hide_dropdown)
    
    def _check_hide_dropdown(self):
        """Check if we should hide dropdown"""
        # Only hide if not clicking in the listbox
        try:
            if not self.dropdown_listbox.winfo_containing(self.winfo_pointerx(), self.winfo_pointery()):
                self._hide_dropdown()
        except:
            pass
    
    def _on_dropdown_select(self, event):
        """Handle selection from dropdown list"""
        selection = self.dropdown_listbox.curselection()
        if selection:
            selected_text = self.dropdown_listbox.get(selection[0])
            if selected_text != "No matches found":
                self.search_var.set(selected_text)
    
    def _on_dropdown_click(self, event):
        """Handle click on dropdown item"""
        selection = self.dropdown_listbox.curselection()
        if selection:
            selected_text = self.dropdown_listbox.get(selection[0])
            if selected_text != "No matches found":
                self.search_var.set(selected_text)
                self._hide_dropdown()
                self.search_entry.focus()
    
    def _show_dropdown(self):
        """Show the dropdown list"""
        if not self.dropdown_visible:
            self.dropdown_frame.pack(fill="x", pady=(5, 0))
            self.dropdown_visible = True
    
    def _hide_dropdown(self):
        """Hide the dropdown list"""
        if self.dropdown_visible:
            self.dropdown_frame.pack_forget()
            self.dropdown_visible = False
    
    def _on_search_button(self):
        """Handle search button click"""
        search_term = self.search_var.get().strip()
        if search_term and search_term != "No matches found":
            print(f"Searching for {self.current_mode}: {search_term}")
            # TODO: Implement actual search logic
            self.selected_entity = search_term
            self._update_panels()
            self._hide_dropdown()
        else:
            # Show error or prompt
            print("Please enter or select a search term")
    
    def _update_panels(self):
        """Update all panels with data for selected entity"""
        # TODO: Load and display actual data in Stage 3+
        print(f"Updating panels for entity: {self.selected_entity}")
        pass
        pass
    
    def _export_panel(self, panel_title, format_type):
        """Export panel data to Excel or PNG"""
        print(f"Exporting '{panel_title}' as {format_type.upper()}")
        # TODO: Implement export functionality in later stages
        pass
    
    def _create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        tooltip = None
        
        def on_enter(event):
            nonlocal tooltip
            x = widget.winfo_rootx() + 25
            y = widget.winfo_rooty() + widget.winfo_height() + 5
            
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(
                tooltip,
                text=text,
                background="#1E2A33",
                foreground="#FFFFFF",
                relief="solid",
                borderwidth=1,
                font=("Segoe UI", 10),
                padx=8,
                pady=4
            )
            label.pack()
        
        def on_leave(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None
        
        try:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
        except (AttributeError, NotImplementedError):
            # Some CustomTkinter widgets (like CTkSegmentedButton) don't support bind
            pass
