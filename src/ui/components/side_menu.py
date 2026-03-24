"""Side menu navigation component"""

import customtkinter as ctk
from PIL import Image
from pathlib import Path


class SideMenu(ctk.CTkFrame):
    """Vertical side menu with logo and navigation buttons"""
    
    def __init__(self, parent, app_controller, logo_path=None):
        super().__init__(parent, width=250, corner_radius=0, fg_color="#FFFFFF")
        
        self.app_controller = app_controller
        
        # Logo section
        self._create_logo_section(logo_path)
        
        # Navigation buttons
        self._create_navigation_buttons()
        
        # Help section at bottom
        self._create_help_section()
        
    def _create_logo_section(self, logo_path):
        """Create logo at top of menu"""
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(pady=30, padx=15)
        
        if logo_path and Path(logo_path).exists():
            try:
                logo_image = Image.open(logo_path)
                # Bigger logo: 200x200
                logo_image = logo_image.resize((200, 200), Image.Resampling.LANCZOS) 
                logo_photo = ctk.CTkImage(light_image=logo_image, dark_image=logo_image, size=(200, 200))
                logo_label = ctk.CTkLabel(logo_frame, image=logo_photo, text="", fg_color="transparent")
                logo_label.pack()
            except Exception as e:
                # Fallback to text logo
                logo_label = ctk.CTkLabel(
                    logo_frame, 
                    text="Performance\nCenter", 
                    font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
                    text_color="#1F5A73"
                )
                logo_label.pack()
        else:
            # Text logo as placeholder
            logo_label = ctk.CTkLabel(
                logo_frame, 
                text="Performance\nCenter", 
                font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
                text_color="#1F5A73"
            )
            logo_label.pack()
            
        # Separator
        separator = ctk.CTkFrame(self, height=2, fg_color="#E2E8F0")
        separator.pack(fill="x", padx=15, pady=15)
    
    def _create_navigation_buttons(self):
        """Create navigation buttons"""
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        buttons_config = [
            ("🏠 Welcome", "welcome"),
            ("📦 12NC Mode", "12nc_mode"),
            ("🏢 Room Mode", "room_mode"),
            ("📊 Bulk View", "bulk_view"),
            ("⚙️ Configuration", "config"),
        ]
        
        self.nav_buttons = {}
        for text, screen_name in buttons_config:
            btn = ctk.CTkButton(
                nav_frame,
                text=text,
                command=lambda s=screen_name: self.navigate_to(s),
                width=220,
                height=45,
                corner_radius=8,
                fg_color="#1F5A73",
                hover_color="#2EC4B6",
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                anchor="w",
                text_color="white"
            )
            btn.pack(pady=8)
            self.nav_buttons[screen_name] = btn
    
    def _create_help_section(self):
        """Create help section at bottom"""
        help_frame = ctk.CTkFrame(self, fg_color="transparent")
        help_frame.pack(side="bottom", fill="x", padx=15, pady=25)
        
        # Separator
        separator = ctk.CTkFrame(help_frame, height=2, fg_color="#E2E8F0")
        separator.pack(fill="x", pady=15)
        
        help_label = ctk.CTkLabel(
            help_frame,
            text="Need Help?",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#1E293B"
        )
        help_label.pack(pady=5)
        
        # Copyable contact entry
        contact_entry = ctk.CTkEntry(
            help_frame,
            width=220,
            height=35,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#F7F9FB",
            border_color="#E2E8F0",
            text_color="#64748B",
            justify="center"
        )
        contact_entry.insert(0, "support@company.com")
        contact_entry.configure(state="readonly")
        contact_entry.pack(pady=5)
    
    def navigate_to(self, screen_name):
        """Handle navigation button click"""
        self.app_controller.show_screen(screen_name)
        self._highlight_active_button(screen_name)
    
    def _highlight_active_button(self, active_screen):
        """Highlight the active navigation button"""
        for screen_name, btn in self.nav_buttons.items():
            if screen_name == active_screen:
                btn.configure(fg_color="#2EC4B6")  # Active state color
            else:
                btn.configure(fg_color="#1F5A73")  # Default button color
