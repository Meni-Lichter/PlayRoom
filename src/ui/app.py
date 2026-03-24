"""Main application window and controller"""

import customtkinter as ctk
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.components.side_menu import SideMenu
from src.ui.screens.welcome_screen import WelcomeScreen


class PerformanceCenterApp(ctk.CTk):
    """Main application window with navigation"""
    
    def __init__(self):
        super().__init__()
        
        # Window configuration
        self.title("Performance Center - Room & 12NC Analysis")
        
        # Set fullscreen
        self.state('zoomed')  # Windows fullscreen
        self.attributes('-fullscreen', False)  # Can use True for true fullscreen
        
        # Set theme
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        
        # Configure window background
        self.configure(fg_color="#F7F9FB")
        
        # Configure grid to fill screen
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, minsize=250)  # Sidebar fixed width
        self.grid_columnconfigure(1, weight=1)  # Content area expands
        
        # Data storage
        self.loaded_files = {}
        self.current_data = {}
        
        # Create UI components
        self._create_side_menu()
        self._create_content_area()
        
        # Show welcome screen by default
        self.show_screen("welcome")
    
    def _create_side_menu(self):
        """Create side navigation menu"""
        # Look for logo in project root
        logo_path = project_root / "logo.png"
        if not logo_path.exists():
            logo_path = None
        
        self.side_menu = SideMenu(self, self, logo_path=logo_path)
        self.side_menu.grid(row=0, column=0, sticky="nsew")
    
    def _create_content_area(self):
        """Create main content area"""
        self.content_frame = ctk.CTkFrame(self, fg_color="#F7F9FB", corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        
        # Dictionary to hold screen instances
        self.screens = {}
        self.current_screen = None
    
    def show_screen(self, screen_name):
        """Switch to specified screen"""
        # Hide current screen
        if self.current_screen:
            self.current_screen.pack_forget()
        
        # Create screen if it doesn't exist
        if screen_name not in self.screens:
            self.screens[screen_name] = self._create_screen(screen_name)
        
        # Show requested screen
        self.current_screen = self.screens[screen_name]
        if self.current_screen:
            self.current_screen.pack(fill="both", expand=True)
        
        # Update side menu highlight
        if hasattr(self, 'side_menu'):
            self.side_menu._highlight_active_button(screen_name)
    
    def _create_screen(self, screen_name):
        """Factory method to create screen instances"""
        if screen_name == "welcome":
            return WelcomeScreen(self.content_frame, self)
        elif screen_name == "12nc_mode":
            return self._create_placeholder_screen("12NC Mode", "Coming in Stage 3")
        elif screen_name == "room_mode":
            return self._create_placeholder_screen("Room Mode", "Coming in Stage 3")
        elif screen_name == "bulk_view":
            return self._create_placeholder_screen("Bulk View", "Coming in Stage 9")
        elif screen_name == "config":
            return self._create_placeholder_screen("Configuration", "Coming in Stage 8")
        else:
            return None
    
    def _create_placeholder_screen(self, title, subtitle):
        """Create a placeholder screen for future implementation"""
        frame = ctk.CTkFrame(self.content_frame, fg_color="#F7F9FB")
        
        label = ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=42, weight="bold"),
            text_color="#1E293B"
        )
        label.pack(pady=(200, 20))
        
        subtitle_label = ctk.CTkLabel(
            frame,
            text=subtitle,
            font=ctk.CTkFont(family="Segoe UI", size=20),
            text_color="#64748B"
        )
        subtitle_label.pack()
        
        return frame
    
    def set_loaded_files(self, files_dict):
        """Store loaded files for access by other screens"""
        self.loaded_files = files_dict.copy()
        # TODO: Actually load and process the files here
        print(f"Files loaded: {self.loaded_files}")
    
    def get_loaded_files(self):
        """Get currently loaded files"""
        return self.loaded_files


def main():
    """Entry point for the application"""
    app = PerformanceCenterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
