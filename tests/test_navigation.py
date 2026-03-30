"""
Navigation and Screen Management Test Suite
Tests screen navigation, routing, and state management.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import tkinter as tk
import customtkinter as ctk
from unittest.mock import Mock, patch

# Import UI modules
from src.ui.app import PerformanceCenterApp
from src.ui.screens.entity_mode_screen import EntityModeScreen
from src.ui.screens.welcome_screen import WelcomeScreen
from src.models.mapping import Room, TwelveNC


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def app_with_data():
    """Create app instance with sample data loaded"""
    app = PerformanceCenterApp()
    
    # Add sample data
    sample_rooms = [
        Room(
            id=f"ROOM_{i:03d}", 
            description=f"Room {i}",
            components={},
            sales_history=[]
        )
        for i in range(1, 6)
    ]
    sample_12ncs = [
        TwelveNC(
            id=f"12NC_{i:03d}", 
            description=f"Component {i}",
            igt="",
            components={},
            sales_history=[]
        )
        for i in range(1, 6)
    ]
    
    app.current_data = {
        'rooms': sample_rooms,
        'nc12s': sample_12ncs
    }
    
    yield app
    
    try:
        app.destroy()
    except:
        pass


# ============================================================================
# SCREEN NAVIGATION TESTS
# ============================================================================


class TestScreenNavigation:
    """Test suite for screen navigation and routing"""
    
    def test_navigate_to_welcome(self, app_with_data):
        """Test navigation to welcome screen"""
        app = app_with_data
        
        app.show_screen("welcome")
        app.update()
        
        assert app.current_screen is not None
        assert isinstance(app.current_screen, WelcomeScreen)
        assert "welcome" in app.screens
    
    def test_navigate_to_12nc_mode(self, app_with_data):
        """Test navigation to 12NC mode"""
        app = app_with_data
        
        app.show_screen("12nc_mode")
        app.update()
        
        assert app.current_screen is not None
        assert isinstance(app.current_screen, EntityModeScreen)
        assert app.current_screen.current_mode == "12nc"
    
    def test_navigate_to_room_mode(self, app_with_data):
        """Test navigation to Room mode"""
        app = app_with_data
        
        app.show_screen("room_mode")
        app.update()
        
        assert app.current_screen is not None
        assert isinstance(app.current_screen, EntityModeScreen)
        assert app.current_screen.current_mode == "room"
    
    def test_navigate_to_bulk_view(self, app_with_data):
        """Test navigation to bulk view (placeholder)"""
        app = app_with_data
        
        app.show_screen("bulk_view")
        app.update()
        
        assert app.current_screen is not None
        # Should create a placeholder screen
    
    def test_navigate_to_config(self, app_with_data):
        """Test navigation to config (placeholder)"""
        app = app_with_data
        
        app.show_screen("config")
        app.update()
        
        assert app.current_screen is not None
        # Should create a placeholder screen
    
    def test_navigate_to_invalid_screen(self, app_with_data):
        """Test navigation to invalid screen name"""
        app = app_with_data
        
        app.show_screen("invalid_screen_name")
        app.update()
        
        # Should handle gracefully (current screen remains or becomes None)
        # Should not crash


class TestScreenCaching:
    """Test suite for screen instance caching"""
    
    def test_welcome_screen_cached(self, app_with_data):
        """Test that welcome screen is cached after first creation"""
        app = app_with_data
        
        # Navigate to welcome first time
        app.show_screen("welcome")
        first_instance = app.current_screen
        
        # Navigate away
        app.show_screen("12nc_mode")
        app.update()
        
        # Navigate back to welcome
        app.show_screen("welcome")
        second_instance = app.current_screen
        
        # Should be same instance (cached)
        assert first_instance is second_instance
    
    def test_entity_mode_screen_shared(self, app_with_data):
        """Test that entity mode screen is shared between 12NC and Room modes"""
        app = app_with_data
        
        # Navigate to 12NC mode
        app.show_screen("12nc_mode")
        app.update()
        nc12_screen = app.current_screen
        
        # Navigate to Room mode
        app.show_screen("room_mode")
        app.update()
        room_screen = app.current_screen
        
        # Should be same screen instance, just different mode
        assert nc12_screen is room_screen
        assert room_screen.current_mode == "room"
    
    def test_screen_hidden_when_switching(self, app_with_data):
        """Test that previous screen is hidden when switching"""
        app = app_with_data
        
        # Show welcome screen
        app.show_screen("welcome")
        welcome_screen = app.current_screen
        
        # Switch to 12NC mode
        app.show_screen("12nc_mode")
        app.update()
        
        # Welcome screen should no longer be the current screen
        assert app.current_screen is not welcome_screen


class TestEntityModeHandling:
    """Test suite for entity mode screen specific navigation"""
    
    def test_switch_between_entity_modes(self, app_with_data):
        """Test switching between 12NC and Room modes"""
        app = app_with_data
        
        # Start with 12NC
        app.show_screen("12nc_mode")
        app.update()
        assert app.current_screen.current_mode == "12nc"
        
        # Switch to Room
        app.show_screen("room_mode")
        app.update()
        assert app.current_screen.current_mode == "room"
        
        # Switch back to 12NC
        app.show_screen("12nc_mode")
        app.update()
        assert app.current_screen.current_mode == "12nc"
    
    def test_entity_mode_screen_created_once(self, app_with_data):
        """Test that entity mode screen is only created once"""
        app = app_with_data
        
        # Navigate to 12NC mode (creates entity_mode screen)
        app.show_screen("12nc_mode")
        app.update()
        
        # Check that entity_mode is in screens dict
        assert "entity_mode" in app.screens
        
        # Navigate to room mode
        app.show_screen("room_mode")
        app.update()
        
        # Should still be same screen instance
        assert "entity_mode" in app.screens
    
    def test_mode_change_handler_called(self, app_with_data):
        """Test that mode change handler is called when switching modes"""
        app = app_with_data
        
        # Create entity screen
        app.show_screen("12nc_mode")
        app.update()
        entity_screen = app.current_screen
        
        # Mock the mode change handler
        original_handler = entity_screen._on_mode_change
        call_count = []
        
        def mock_handler(value):
            call_count.append(value)
            original_handler(value)
        
        entity_screen._on_mode_change = mock_handler
        
        # Switch to room mode
        app.show_screen("room_mode")
        app.update()
        
        # Handler should have been called
        assert len(call_count) > 0


# ============================================================================
# STATE MANAGEMENT TESTS
# ============================================================================


class TestStateManagement:
    """Test suite for application state management"""
    
    def test_current_data_initialization(self, app_with_data):
        """Test that current_data is properly initialized"""
        app = app_with_data
        
        assert isinstance(app.current_data, dict)
        assert 'rooms' in app.current_data
        assert 'nc12s' in app.current_data
    
    def test_loaded_files_initialization(self, app_with_data):
        """Test that loaded_files is properly initialized"""
        app = app_with_data
        
        assert isinstance(app.loaded_files, dict)
    
    def test_current_screen_tracking(self, app_with_data):
        """Test that current_screen is properly tracked"""
        app = app_with_data
        
        # Initially should have a screen
        assert app.current_screen is not None
        
        # After navigation, should update
        app.show_screen("12nc_mode")
        app.update()
        nc_screen = app.current_screen
        
        app.show_screen("welcome")
        app.update()
        welcome_screen = app.current_screen
        
        assert nc_screen is not welcome_screen
    
    def test_data_persists_across_navigation(self, app_with_data):
        """Test that data persists when navigating between screens"""
        app = app_with_data
        
        initial_rooms = app.current_data['rooms']
        initial_nc12s = app.current_data['nc12s']
        
        # Navigate between screens
        app.show_screen("12nc_mode")
        app.update()
        app.show_screen("room_mode")
        app.update()
        app.show_screen("welcome")
        app.update()
        
        # Data should still be there
        assert app.current_data['rooms'] == initial_rooms
        assert app.current_data['nc12s'] == initial_nc12s


# ============================================================================
# SIDE MENU INTEGRATION TESTS
# ============================================================================


class TestSideMenuIntegration:
    """Test suite for side menu and navigation integration"""
    
    def test_side_menu_exists(self, app_with_data):
        """Test that side menu is created"""
        app = app_with_data
        
        assert hasattr(app, 'side_menu')
        assert app.side_menu is not None
    
    def test_side_menu_highlight_updates(self, app_with_data):
        """Test that side menu highlight updates on navigation"""
        app = app_with_data
        
        # Mock the highlight method to track calls
        if hasattr(app.side_menu, '_highlight_active_button'):
            original_highlight = app.side_menu._highlight_active_button
            calls = []
            
            def mock_highlight(screen_name):
                calls.append(screen_name)
                return original_highlight(screen_name)
            
            app.side_menu._highlight_active_button = mock_highlight
            
            # Navigate to different screens
            app.show_screen("12nc_mode")
            app.update()
            
            app.show_screen("room_mode")
            app.update()
            
            # Should have called highlight method
            assert len(calls) > 0


# ============================================================================
# PLACEHOLDER SCREEN TESTS
# ============================================================================


class TestPlaceholderScreens:
    """Test suite for placeholder screens (bulk_view, config)"""
    
    def test_bulk_view_placeholder_created(self, app_with_data):
        """Test that bulk view placeholder is created"""
        app = app_with_data
        
        app.show_screen("bulk_view")
        app.update()
        
        assert app.current_screen is not None
        assert "bulk_view" in app.screens
    
    def test_config_placeholder_created(self, app_with_data):
        """Test that config placeholder is created"""
        app = app_with_data
        
        app.show_screen("config")
        app.update()
        
        assert app.current_screen is not None
        assert "config" in app.screens
    
    def test_placeholder_has_description(self, app_with_data):
        """Test that placeholder screens have descriptive content"""
        app = app_with_data
        
        # Create placeholder
        placeholder = app._create_placeholder_screen(
            title="Test Placeholder",
            description="Test description",
            status="Coming Soon"
        )
        
        assert placeholder is not None


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


class TestNavigationEdgeCases:
    """Test suite for edge cases in navigation"""
    
    def test_navigate_to_none(self, app_with_data):
        """Test navigation with None parameter"""
        app = app_with_data
        
        try:
            app.show_screen(None)
            app.update()
            # Should handle gracefully or current screen remains
        except:
            pytest.fail("Navigation with None should not crash")
    
    def test_rapid_navigation(self, app_with_data):
        """Test rapid consecutive navigation"""
        app = app_with_data
        
        # Rapidly switch between screens
        for _ in range(5):
            app.show_screen("12nc_mode")
            app.show_screen("room_mode")
            app.show_screen("welcome")
        
        app.update()
        
        # Should not crash and current_screen should be valid
        assert app.current_screen is not None
    
    def test_navigate_before_data_loaded(self):
        """Test navigation before any data is loaded"""
        app = PerformanceCenterApp()
        
        # Navigate without any data
        app.show_screen("12nc_mode")
        app.update()
        
        # Should not crash
        assert app.current_screen is not None
        
        try:
            app.destroy()
        except:
            pass


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


class TestNavigationPerformance:
    """Test suite for navigation performance"""
    
    def test_screen_creation_performance(self, app_with_data):
        """Test that screen creation is reasonably fast"""
        import time
        app = app_with_data
        
        start_time = time.time()
        
        # Create all screens
        app.show_screen("welcome")
        app.update()
        app.show_screen("12nc_mode")
        app.update()
        app.show_screen("room_mode")
        app.update()
        app.show_screen("bulk_view")
        app.update()
        app.show_screen("config")
        app.update()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should create all screens in reasonable time (e.g., < 5 seconds)
        assert duration < 5.0, f"Screen creation took {duration:.2f}s, expected < 5s"
    
    def test_navigation_switching_performance(self, app_with_data):
        """Test that switching between screens is fast"""
        import time
        app = app_with_data
        
        # Pre-create screens
        app.show_screen("welcome")
        app.show_screen("12nc_mode")
        app.update()
        
        # Time the switching
        start_time = time.time()
        
        for _ in range(10):
            app.show_screen("12nc_mode")
            app.show_screen("room_mode")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 20 switches should be very fast (< 1 second)
        assert duration < 1.0, f"20 screen switches took {duration:.2f}s, expected < 1s"


# ============================================================================
# INTEGRATION TEST SCENARIOS
# ============================================================================


class TestCompleteUserJourneys:
    """Integration tests for complete user interaction scenarios"""
    
    def test_first_time_user_journey(self, app_with_data):
        """Test complete journey of a first-time user"""
        app = app_with_data
        
        # User starts at welcome screen
        assert isinstance(app.current_screen, WelcomeScreen)
        
        # User navigates to 12NC mode
        app.show_screen("12nc_mode")
        app.update()
        assert app.current_screen.current_mode == "12nc"
        
        # User switches to Room mode
        app.show_screen("room_mode")
        app.update()
        assert app.current_screen.current_mode == "room"
        
        # User goes back to welcome
        app.show_screen("welcome")
        app.update()
        assert isinstance(app.current_screen, WelcomeScreen)
    
    def test_power_user_journey(self, app_with_data):
        """Test journey of a power user rapidly navigating"""
        app = app_with_data
        
        # Power user rapidly switches modes
        app.show_screen("12nc_mode")
        app.update()
        
        # Searches in 12NC mode
        entity_screen = app.current_screen
        entity_screen.search_var.set("12NC_001")
        entity_screen._on_search_button()
        assert entity_screen.selected_entity == "12NC_001"
        
        # Switches to Room mode
        app.show_screen("room_mode")
        app.update()
        
        # Searches in Room mode
        entity_screen.search_var.set("ROOM_001")
        entity_screen._on_search_button()
        assert entity_screen.selected_entity == "ROOM_001"
        
        # Explores other sections
        app.show_screen("bulk_view")
        app.update()
        
        # Returns to analysis
        app.show_screen("12nc_mode")
        app.update()
        assert app.current_screen.current_mode == "12nc"


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================


if __name__ == "__main__":
    """Run tests with verbose output"""
    pytest.main([__file__, "-v", "--tb=short"])
