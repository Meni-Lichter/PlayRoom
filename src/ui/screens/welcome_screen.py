"""Welcome screen - Landing page with file loading and system overview"""

import customtkinter as ctk
from tkinter import filedialog
from datetime import datetime
from pathlib import Path


class WelcomeScreen(ctk.CTkFrame):
    """Welcome/home screen with file loading and system information"""
    
    def __init__(self, parent, app_controller):
        super().__init__(parent, fg_color="#F7F9FB")
        
        self.app_controller = app_controller
        self.loaded_files = {
            "cbom": "",
            "ymbd": "",
            "fit_cvi": ""
        }
        
        # Main container
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=50, pady=50)
        
        # Title Section
        self._create_title_section(main_container)
        
        # File Loading Section
        self._create_file_loading_section(main_container)
        
        # System Info Section
        self._create_system_info_section(main_container)
        
        # Quick Actions Section
        self._create_quick_actions_section(main_container)
    
    def _create_title_section(self, parent):
        """Create welcome title"""
        title_frame = ctk.CTkFrame(parent, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 40))
        
        title = ctk.CTkLabel(
            title_frame,
            text="Welcome to Performance Center",
            font=ctk.CTkFont(family="Segoe UI", size=42, weight="bold"),
            text_color="#1E293B"
        )
        title.pack()
        
        date_label = ctk.CTkLabel(
            title_frame,
            text=f"Today: {datetime.now().strftime('%B %d, %Y')}",
            font=ctk.CTkFont(family="Segoe UI", size=18),
            text_color="#64748B"
        )
        date_label.pack(pady=8)
    
    def _create_file_loading_section(self, parent):
        """Create file loading section"""
        file_frame = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=15)
        file_frame.pack(fill="x", pady=15)
        
        # Section title
        section_title = ctk.CTkLabel(
            file_frame,
            text="📁 Load Data Files",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#1E293B"
        )
        section_title.pack(pady=25, padx=25, anchor="w")
        
        # File loading rows
        files_config = [
            ("CBOM File", "cbom", "Component Bill of Materials"),
            ("YMBD Sales", "ymbd", "Sales data for 12NCs"),
            ("FIT/CVI Sales", "fit_cvi", "Sales data for Rooms")
        ]
        
        for label, key, description in files_config:
            self._create_file_row(file_frame, label, key, description)
        
        # Load button
        load_btn = ctk.CTkButton(
            file_frame,
            text="Load All Files",
            command=self.load_files,
            width=220,
            height=50,
            corner_radius=8,
            fg_color="#1F5A73",
            hover_color="#2EC4B6",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        )
        load_btn.pack(pady=25)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            file_frame,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color="#10b981"
        )
        self.status_label.pack(pady=(0, 25))
            font=ctk.CTkFont(size=12),
            text_color="#10b981"
        )
        self.status_label.pack(pady=(0, 20))
    
    def _create_file_row(self, parent, label, key, description):
        """Create a file selection row"""
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill="x", padx=25, pady=12)
        
        # Label
        label_widget = ctk.CTkLabel(
            row_frame,
            text=label,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#1E293B",
            width=140,
            anchor="w"
        )
        label_widget.pack(side="left", padx=(0, 15))
        
        # File path display
        path_var = ctk.StringVar(value="No file selected")
        path_entry = ctk.CTkEntry(
            row_frame,
            textvariable=path_var,
            state="readonly",
            width=450,
            height=40,
            corner_radius=8,
            fg_color="#F7F9FB",
            border_color="#E2E8F0",
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        path_entry.pack(side="left", padx=8)
        
        # Browse button
        browse_btn = ctk.CTkButton(
            row_frame,
            text="Browse",
            command=lambda: self.browse_file(key, path_var),
            width=110,
            height=40,
            corner_radius=8,
            fg_color="#1F5A73",
            hover_color="#2EC4B6",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        )
        browse_btn.pack(side="left", padx=8)
        
        # Description
        desc_label = ctk.CTkLabel(
            row_frame,
            text=description,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#64748B"
        )
        desc_label.pack(side="left", padx=12)
        
        # Store reference
        setattr(self, f"{key}_path_var", path_var)
    
    def _create_system_info_section(self, parent):
        """Create system capabilities overview"""
        info_frame = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=15)
        info_frame.pack(fill="x", pady=15)
        
        section_title = ctk.CTkLabel(
            info_frame,
            text="📊 System Capabilities",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#1E293B"
        )
        section_title.pack(pady=25, padx=25, anchor="w")
        
        capabilities = [
            "🔍 Search and analyze 12NC and Room performance",
            "📈 View historical sales trends with customizable granularity",
            "🎯 Generate demand predictions with multiple methods",
            "🗺️ Track 12NC deployment across rooms",
            "📦 Analyze inventory levels and distributions",
            "📊 Bulk analysis for multiple entities",
            "⚙️ Configurable data source handling"
        ]
        
        for capability in capabilities:
            cap_label = ctk.CTkLabel(
                info_frame,
                text=capability,
                font=ctk.CTkFont(family="Segoe UI", size=15),
                text_color="#64748B",
                anchor="w"
            )
            cap_label.pack(padx=45, pady=6, anchor="w")
        
        info_frame.pack_configure(pady=(15, 25))
    
    def _create_quick_actions_section(self, parent):
        """Create quick action buttons"""
        actions_frame = ctk.CTkFrame(parent, fg_color="transparent")
        actions_frame.pack(fill="x", pady=15)
        
        # Action buttons
        btn_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
        btn_frame.pack()
        
        actions = [
            ("View 12NC", "12nc_mode", "#1F5A73"),
            ("View Room", "room_mode", "#2EC4B6"),
            ("Bulk Analysis", "bulk_view", "#f59e0b"),
            ("Settings", "config", "#64748B")
        ]
        
        for text, screen, color in actions:
            btn = ctk.CTkButton(
                btn_frame,
                text=text,
                command=lambda s=screen: self.app_controller.show_screen(s),
                width=200,
                height=50,
                corner_radius=10,
                fg_color=color,
                hover_color=color,
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
            )
            btn.pack(side="left", padx=12)
    
    def browse_file(self, file_key, path_var):
        """Open file browser dialog"""
        filename = filedialog.askopenfilename(
            title=f"Select {file_key.upper()} File",
            filetypes=[("Excel files", "*.xlsx *.xlsm *.xls"), ("All files", "*.*")]
        )
        
        if filename:
            self.loaded_files[file_key] = filename
            path_var.set(Path(filename).name)
            self.status_label.configure(text="")
    
    def load_files(self):
        """Load and process all selected files"""
        missing_files = [key for key, path in self.loaded_files.items() if not path]
        
        if missing_files:
            self.status_label.configure(
                text=f"⚠️ Please select all files. Missing: {', '.join(missing_files)}",
                text_color="#ef4444"
            )
            return
        
        try:
            # TODO: Call actual data loading functions
            self.status_label.configure(
                text="✓ Files loaded successfully!",
                text_color="#10b981"
            )
            
            # Store loaded files in app controller for other screens to access
            self.app_controller.set_loaded_files(self.loaded_files)
            
        except Exception as e:
            self.status_label.configure(
                text=f"❌ Error loading files: {str(e)}",
                text_color="#ef4444"
            )
