"""Main application window and controller"""

import customtkinter as ctk
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.components.side_menu import SideMenu
from src.ui.screens.welcome_screen import WelcomeScreen
from src.ui.screens.entity_mode_screen import EntityModeScreen


class PerformanceCenterApp(ctk.CTk):
    """Main application window with navigation"""
    
    def __init__(self):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        super().__init__()

        # Window configuration
        self.title("Play Room - Room & 12NC Analysis")
        self.configure(fg_color="#EEF2F6")

        # Open maximized on Windows
        self.state("zoomed")
       

        # Grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, minsize=250)
        self.grid_columnconfigure(1, weight=1)

        # Data storage
        self.loaded_files = {}
        self.current_data = {}

        # Create UI
        self._create_side_menu()
        self._create_content_area()

        # Default screen
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
        self.content_frame = ctk.CTkFrame(self, fg_color="#EEF2F6", corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        
        # Dictionary to hold screen instances
        self.screens = {}
        self.current_screen = None
    
    def show_screen(self, screen_name):
        """Switch to specified screen"""
        # Hide current screen
        if self.current_screen:
            self.current_screen.pack_forget()
        
        # For entity mode screens (12nc/room), check if we need to switch mode
        if screen_name in ["12nc_mode", "room_mode"]:
            # If entity screen doesn't exist, create it
            if "entity_mode" not in self.screens:
                self.screens["entity_mode"] = EntityModeScreen(self.content_frame, self, mode="12nc")
            
            # Get the screen instance
            entity_screen = self.screens["entity_mode"]
            
            # Update the mode on the existing screen
            new_mode = "12nc" if screen_name == "12nc_mode" else "room"
            if entity_screen.current_mode != new_mode:
                # Update mode directly
                entity_screen.current_mode = new_mode
                # Trigger the mode change handler to update all related UI
                entity_screen._on_mode_change(None)
            
            # Show the entity screen
            self.current_screen = entity_screen
            self.current_screen.pack(fill="both", expand=True)
        else:
            # For other screens, use normal screen creation
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
            return EntityModeScreen(self.content_frame, self, mode="12nc")
        elif screen_name == "room_mode":
            return EntityModeScreen(self.content_frame, self, mode="room")
        elif screen_name == "bulk_view":
            return self._create_placeholder_screen(
                "Bulk Analysis View", 
                "Analyze multiple 12NCs or Rooms simultaneously for comparative insights",
                "Coming in Stage 9"
            )
        elif screen_name == "config":
            return self._create_placeholder_screen(
                "Configuration", 
                "Manage data sources, prediction settings, and system preferences",
                "Coming in Stage 8"
            )
        else:
            return None
    
    def _create_placeholder_screen(self, title, description, status):
        """Create a placeholder screen for future implementation"""
        frame = ctk.CTkFrame(self.content_frame, fg_color="#EEF2F6")
        
        # Title section at the top
        title_container = ctk.CTkFrame(frame, fg_color="transparent")
        title_container.pack(fill="x", padx=50, pady=(30, 20))
        
        title_label = ctk.CTkLabel(
            title_container,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color="#1E2A33"
        )
        title_label.pack()
        
        desc_label = ctk.CTkLabel(
            title_container,
            text=description,
            font=ctk.CTkFont(family="Segoe UI", size=15),
            text_color="#5F6E7C"
        )
        desc_label.pack(pady=(5, 0))
        
        # Coming soon message in center
        center_frame = ctk.CTkFrame(frame, fg_color="transparent")
        center_frame.pack(expand=True)
        
        status_label = ctk.CTkLabel(
            center_frame,
            text=status,
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#8A98A6"
        )
        status_label.pack()
        
        
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
