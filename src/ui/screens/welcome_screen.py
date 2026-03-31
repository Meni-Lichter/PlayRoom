"""Welcome screen - Landing page with file loading and system overview"""

import customtkinter as ctk
from tkinter import filedialog
from datetime import datetime
from pathlib import Path
import sys

from src.models.mapping import Room

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure import load_cbom
from src.infrastructure.data_loaders import read_file
from src.infrastructure.data_transformer import transform_cbom_data, parse_ymbd_to_sales_records, parse_fit_cvi_to_sales_records
from src.utils import load_config
from src.utils.config_util import get_last_files, save_last_files


class WelcomeScreen(ctk.CTkFrame):
    """Welcome/home screen with file loading and system information"""
    
    def __init__(self, parent, app_controller):
        super().__init__(parent, fg_color="#EEF2F6")
        
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
        
        # Auto-load last files if they exist
        self.after(100, self._auto_load_last_files)
    
    def _create_title_section(self, parent):
        """Create welcome title"""
        title_frame = ctk.CTkFrame(parent, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 40))
        
        title = ctk.CTkLabel(
            title_frame,
            text="Welcome to Play Room",
            font=ctk.CTkFont(family="Segoe UI", size=48, weight="bold"),
            text_color="#1E2A33"
        )
        title.pack()
        
        description = ctk.CTkLabel(
            title_frame,
            text="Performance analysis and demand prediction for 12NC components and Rooms",
            font=ctk.CTkFont(family="Segoe UI", size=18),
            text_color="#5F6E7C"
        )
        description.pack(pady=(8, 0))
        
        date_label = ctk.CTkLabel(
            title_frame,
            text=f"Today: {datetime.now().strftime('%B %d, %Y')}",
            font=ctk.CTkFont(family="Segoe UI", size=20),
            text_color="#5F6E7C"
        )
        date_label.pack(pady=8)
    
    def _create_file_loading_section(self, parent):
        """Create file loading section"""
        file_frame = ctk.CTkFrame(parent, fg_color="#F8FAFC", corner_radius=15, border_width=1, border_color="#D8E0E8")
        file_frame.pack(fill="x", pady=15)
        
        # Section title
        section_title = ctk.CTkLabel(
            file_frame,
            text="📁 Load Data Files",
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color="#1E2A33"
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
            height=52,
            corner_radius=8,
            fg_color="#35586E",
            hover_color="#2F4F63",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        )
        load_btn.pack(pady=25)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            file_frame,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=16),
            text_color="#10b981"
        )
        self.status_label.pack(pady=(0, 25))
        self.status_label.pack(pady=(0, 20))
    
    def _create_file_row(self, parent, label, key, description):
        """Create a file selection row"""
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill="x", padx=25, pady=12)
        
        # Label
        label_widget = ctk.CTkLabel(
            row_frame,
            text=label,
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#1E2A33",
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
            fg_color="#FFFFFF",
            border_color="#D8E0E8",
            text_color="#5F6E7C",
            font=ctk.CTkFont(family="Segoe UI", size=15)
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
            fg_color="#E7EDF3",
            hover_color="#DCE4EC",
            text_color="#2B3A44",
            border_width=1,
            border_color="#D8E0E8",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        )
        browse_btn.pack(side="left", padx=8)
        
        # Description
        desc_label = ctk.CTkLabel(
            row_frame,
            text=description,
            font=ctk.CTkFont(family="Segoe UI", size=15),
            text_color="#8A98A6"
        )
        desc_label.pack(side="left", padx=12)
        
        # Store reference
        setattr(self, f"{key}_path_var", path_var)
    
    def _create_system_info_section(self, parent):
        """Create system capabilities overview"""
        info_frame = ctk.CTkFrame(parent, fg_color="#F8FAFC", corner_radius=15, border_width=1, border_color="#D8E0E8")
        info_frame.pack(fill="x", pady=15)
        
        section_title = ctk.CTkLabel(
            info_frame,
            text="📊 System Capabilities",
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color="#1E2A33"
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
                font=ctk.CTkFont(family="Segoe UI", size=17),
                text_color="#5F6E7C",
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
            ("View 12NC", "12nc_mode", "#35586E", "#2F4F63"),
            ("View Room", "room_mode", "#35586E", "#2F4F63"),
            ("Bulk Analysis", "bulk_view", "#4A8F93", "#3F7F83"),
            ("Settings", "config", "#E7EDF3", "#DCE4EC")
        ]
        
        for text, screen, color, hover_color in actions:
            # Determine text color based on button color
            if color == "#E7EDF3":
                text_color = "#2B3A44"
                border_width = 1
                border_color = "#D8E0E8"
            else:
                text_color = "#FFFFFF"
                border_width = 0
                border_color = None
                
            btn = ctk.CTkButton(
                btn_frame,
                text=text,
                command=lambda s=screen: self.app_controller.show_screen(s),
                width=200,
                height=52,
                corner_radius=10,
                fg_color=color,
                hover_color=hover_color,
                text_color=text_color,
                border_width=border_width,
                border_color=border_color,
                font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
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
            # Load configuration
            config = load_config("config/config.json")
            
            # Load CBOM file
            self.status_label.configure(
                text="⏳ Loading CBOM file...",
                text_color="#f59e0b"
            )
            self.update()
            
            cbom_path = Path(self.loaded_files["cbom"])
            room_data, data_12nc = load_cbom(cbom_path, config)
            
            if not room_data or not data_12nc:
                self.status_label.configure(
                    text="❌ Error: CBOM file is empty or invalid",
                    text_color="#ef4444"
                )
                return
            
            # Transform CBOM data into Room and TwelveNC objects
            self.status_label.configure(
                text="⏳ Processing data...",
                text_color="#f59e0b"
            )
            self.update()
            
            rooms, nc12s = transform_cbom_data(room_data, data_12nc, config)
            
            # Load and process YMBD sales data for 12NCs
            self.status_label.configure(
                text="⏳ Loading YMBD sales data...",
                text_color="#f59e0b"
            )
            self.update()
            
            ymbd_path = Path(self.loaded_files["ymbd"])
            ymbd_df = read_file(ymbd_path, "ymbd", header=0)
            if ymbd_df is not None:
                nc12s = parse_ymbd_to_sales_records(nc12s, ymbd_df)
            
            # Load and process FIT_CVI sales data for Rooms
            self.status_label.configure(
                text="⏳ Loading FIT_CVI sales data...",
                text_color="#f59e0b"
            )
            self.update()
            
            fit_cvi_path = Path(self.loaded_files["fit_cvi"])
            fit_cvi_df = read_file(fit_cvi_path, "fit_cvi", header=0)
            if fit_cvi_df is not None:
                rooms = parse_fit_cvi_to_sales_records(rooms, fit_cvi_df)
            
            # Build lookup dictionaries for O(1) entity access across all screens
            rooms_dict: dict[str, Room] = {room.id: room for room in rooms}
            nc12s_dict = {nc12.id: nc12 for nc12 in nc12s}
            
            # Store only the dictionaries - lists and raw data not needed
            self.app_controller.current_data = {
                "rooms_dict": rooms_dict,
                "nc12s_dict": nc12s_dict
            }
            
            # Store loaded file paths
            self.app_controller.set_loaded_files(self.loaded_files)
            
            # Update entity screens if they exist
            if "entity_mode" in self.app_controller.screens:
                entity_screen = self.app_controller.screens["entity_mode"]
                entity_screen.reload_data_from_uploaded_files(rooms_dict, nc12s_dict)
            
            # Success message with counts
            self.status_label.configure(
                text=f"✓ Files loaded successfully! ({len(rooms_dict)} Rooms, {len(nc12s_dict)} 12NCs)",
                text_color="#10b981"
            )
            
            # Save file paths for next session
            save_last_files(self.loaded_files)
            
        except Exception as e:
            self.status_label.configure(
                text=f"❌ Error loading files: {str(e)}",
                text_color="#ef4444"
            )
            print(f"Error loading files: {e}")
            import traceback
            traceback.print_exc()
    
    def _auto_load_last_files(self):
        """Auto-load files from last session if they exist"""
        try:
            last_files = get_last_files()
            
            # Check if all files exist
            all_exist = all(
                last_files.get(key) and Path(last_files[key]).exists()
                for key in ["cbom", "ymbd", "fit_cvi"]
            )
            
            if all_exist:
                # Set loaded files
                for key in ["cbom", "ymbd", "fit_cvi"]:
                    self.loaded_files[key] = last_files[key]
                    path_var = getattr(self, f"{key}_path_var", None)
                    if path_var:
                        path_var.set(Path(last_files[key]).name)
                
                # Show loading message
                self.status_label.configure(
                    text="⏳ Auto-loading previous files...",
                    text_color="#f59e0b"
                )
                self.update()
                
                # Automatically load and process the files
                self.load_files()
                
                # Update success message to indicate auto-load
                if "✓" in self.status_label.cget("text"):
                    current_text = self.status_label.cget("text")
                    self.status_label.configure(
                        text=f"🔄 {current_text} (auto-loaded from previous session)",
                        text_color="#10b981"
                    )
        except Exception as e:
            # Silent fail - user can load manually
            print(f"Could not auto-load last files: {e}")
