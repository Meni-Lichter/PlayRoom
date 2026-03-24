"""Side menu navigation component"""

import customtkinter as ctk
from PIL import Image
from pathlib import Path
import tkinter as tk
from tkinter import messagebox


class SideMenu(ctk.CTkFrame):
    """Vertical side menu with logo and navigation buttons"""
    
    def __init__(self, parent, app_controller, logo_path=None):
        super().__init__(parent, width=250, corner_radius=0, fg_color="#F8FAFC")
        
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
                text="Play\nRoom", 
                font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
                text_color="#35586E"
            )
            logo_label.pack()
            
        # Separator
        separator = ctk.CTkFrame(self, height=2, fg_color="#D8E0E8")
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
                fg_color="#35586E",
                hover_color="#2F4F63",
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                anchor="w",
                text_color="#FFFFFF",
                border_width=0
            )
            btn.pack(pady=8)
            self.nav_buttons[screen_name] = btn
    
    def _create_help_section(self):
        """Create help section at bottom"""
        help_frame = ctk.CTkFrame(self, fg_color="transparent")
        help_frame.pack(side="bottom", fill="x", padx=15, pady=25)
        
        # Separator
        separator = ctk.CTkFrame(help_frame, height=2, fg_color="#D8E0E8")
        separator.pack(fill="x", pady=15)
        
        help_label = ctk.CTkLabel(
            help_frame,
            text="Need Help?",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#1E2A33"
        )
        help_label.pack(pady=5)
        
        # Contact row with copy button
        contact_row = ctk.CTkFrame(help_frame, fg_color="transparent")
        contact_row.pack(pady=5)
        
        # Email entry (readonly)
        self.contact_entry = ctk.CTkEntry(
            contact_row,
            width=150,
            height=35,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="#FFFFFF",
            border_color="#D8E0E8",
            text_color="#5F6E7C",
            justify="center"
        )
        self.contact_entry.insert(0, "support@company.com")
        self.contact_entry.configure(state="readonly")
        self.contact_entry.pack(side="left", padx=(0, 5))
        
        # Copy button with tooltip
        copy_btn = ctk.CTkButton(
            contact_row,
            text="📋",
            width=35,
            height=35,
            corner_radius=6,
            fg_color="#4A8F93",
            hover_color="#3F7F83",
            font=ctk.CTkFont(size=16),
            command=self.copy_email
        )
        copy_btn.pack(side="left")
        
        # Create tooltip
        self._create_tooltip(copy_btn, "Copy email to clipboard")
    
    def navigate_to(self, screen_name):
        """Handle navigation button click"""
        self.app_controller.show_screen(screen_name)
        self._highlight_active_button(screen_name)
    
    def _highlight_active_button(self, active_screen):
        """Highlight the active navigation button"""
        for screen_name, btn in self.nav_buttons.items():
            if screen_name == active_screen:
                btn.configure(fg_color="#4A8F93")  # Accent color for active
            else:
                btn.configure(fg_color="#35586E")  # Primary color for inactive
    
    def copy_email(self):
        """Copy email to clipboard"""
        email = self.contact_entry.get()
        self.clipboard_clear()
        self.clipboard_append(email)
        # Show brief confirmation
        messagebox.showinfo("Copied", f"Email copied to clipboard:\n{email}")
    
    def _create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        tooltip = None
        
        def on_enter(event):
            nonlocal tooltip
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(
                tooltip,
                text=text,
                background="#FFFFFF",
                foreground="#1E2A33",
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
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
