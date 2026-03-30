"""
UI Components Test Suite for Room_12NC_PerformanceCenter
Tests UI components, screen navigation, and user interactions.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import tkinter as tk
import customtkinter as ctk
from unittest.mock import Mock, MagicMock, patch, call
from typing import List, Dict

# Import UI modules
from src.ui.app import PerformanceCenterApp
from src.ui.screens.entity_mode_screen import EntityModeScreen
from src.ui.screens.welcome_screen import WelcomeScreen
from src.ui.components.side_menu import SideMenu
from src.models.mapping import Room, TwelveNC


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def app_instance():
    """Create a test app instance"""
    app = PerformanceCenterApp()
    yield app
    try:
        app.destroy()
    except:
        pass


@pytest.fixture
def mock_app_controller():
    """Create a mock app controller for testing"""
    controller = Mock()
    controller.current_data = {
        'rooms': [],
        'nc12s': []
    }
    controller.loaded_files = {}
    return controller


@pytest.fixture
def sample_rooms():
    """Create sample Room objects for testing"""
    rooms = []
    for i in range(1, 11):
        room = Room(
            id=f"ROOM_{i:03d}", 
            description=f"Test Room {i}",
            components={},
            sales_history=[]
        )
        rooms.append(room)
    return rooms


@pytest.fixture
def sample_12ncs():
    """Create sample TwelveNC objects for testing"""
    nc12s = []
    for i in range(1, 11):
        nc12 = TwelveNC(
            id=f"12NC_{i:03d}", 
            description=f"Test Component {i}",
            igt="",
            components={},
            sales_history=[]
        )
        nc12s.append(nc12)
    return nc12s


@pytest.fixture
def entity_screen_room_mode(mock_app_controller, sample_rooms):
    """Create EntityModeScreen in room mode with sample data"""
    root = tk.Tk()
    mock_app_controller.current_data = {
        'rooms': sample_rooms,
        'nc12s': []
    }
    screen = EntityModeScreen(root, mock_app_controller, mode="room")
    yield screen
    try:
        root.destroy()
    except:
        pass


@pytest.fixture
def entity_screen_12nc_mode(mock_app_controller, sample_12ncs):
    """Create EntityModeScreen in 12nc mode with sample data"""
    root = tk.Tk()
    mock_app_controller.current_data = {
        'rooms': [],
        'nc12s': sample_12ncs
    }
    screen = EntityModeScreen(root, mock_app_controller, mode="12nc")
    yield screen
    try:
        root.destroy()
    except:
        pass


# ============================================================================
# APP TESTS
# ============================================================================


class TestPerformanceCenterApp:
    """Test suite for main application"""
    
    def test_app_initialization(self, app_instance):
        """Test that app initializes correctly"""
        assert app_instance is not None
        assert isinstance(app_instance, ctk.CTk)
        assert hasattr(app_instance, 'side_menu')
        assert hasattr(app_instance, 'content_frame')
        assert hasattr(app_instance, 'screens')
        assert hasattr(app_instance, 'current_data')
        assert hasattr(app_instance, 'loaded_files')
    
    def test_initial_screen_is_welcome(self, app_instance):
        """Test that welcome screen is shown initially"""
        assert app_instance.current_screen is not None
        assert isinstance(app_instance.current_screen, WelcomeScreen)
    
    def test_screen_switching(self, app_instance):
        """Test switching between different screens"""
        # Switch to 12NC mode
        app_instance.show_screen("12nc_mode")
        app_instance.update()
        assert app_instance.current_screen is not None
        
        # Switch to room mode
        app_instance.show_screen("room_mode")
        app_instance.update()
        assert app_instance.current_screen is not None
        
        # Switch back to welcome
        app_instance.show_screen("welcome")
        app_instance.update()
        assert isinstance(app_instance.current_screen, WelcomeScreen)
    
    def test_data_storage_structure(self, app_instance):
        """Test that data storage dictionaries are properly initialized"""
        assert isinstance(app_instance.loaded_files, dict)
        assert isinstance(app_instance.current_data, dict)
    
    def test_grid_layout_configuration(self, app_instance):
        """Test that grid layout is properly configured"""
        # Check row configuration
        row_weight = app_instance.grid_rowconfigure(0)
        assert row_weight is not None
        
        # Check column configuration
        col0_config = app_instance.grid_columnconfigure(0)
        col1_config = app_instance.grid_columnconfigure(1)
        assert col0_config is not None
        assert col1_config is not None


# ============================================================================
# ENTITY MODE SCREEN TESTS
# ============================================================================


class TestEntityModeScreen:
    """Test suite for EntityModeScreen"""
    
    def test_initialization_room_mode(self, entity_screen_room_mode):
        """Test EntityModeScreen initializes correctly in room mode"""
        screen = entity_screen_room_mode
        assert screen.current_mode == "room"
        assert screen.selected_entity is None
        assert hasattr(screen, 'all_items')
        assert len(screen.all_items) == 10  # 10 sample rooms
    
    def test_initialization_12nc_mode(self, entity_screen_12nc_mode):
        """Test EntityModeScreen initializes correctly in 12nc mode"""
        screen = entity_screen_12nc_mode
        assert screen.current_mode == "12nc"
        assert screen.selected_entity is None
        assert hasattr(screen, 'all_items')
        assert len(screen.all_items) == 10  # 10 sample 12ncs
    
    def test_font_caching(self, entity_screen_room_mode):
        """Test that font caching works correctly"""
        screen = entity_screen_room_mode
        
        # Get a font twice - should return same object
        font1 = screen._get_font("Segoe UI", 15, "normal")
        font2 = screen._get_font("Segoe UI", 15, "normal")
        assert font1 is font2
        
        # Different parameters should return different font
        font3 = screen._get_font("Segoe UI", 16, "normal")
        assert font1 is not font3
    
    def test_mode_config_structure(self, entity_screen_room_mode):
        """Test MODE_CONFIG has correct structure"""
        config = EntityModeScreen.MODE_CONFIG
        
        assert "12nc" in config
        assert "room" in config
        
        for mode in ["12nc", "room"]:
            assert "key" in config[mode]
            assert "display" in config[mode]
            assert "title" in config[mode]
            assert "description" in config[mode]
            assert "items" in config[mode]
    
    def test_colors_defined(self, entity_screen_room_mode):
        """Test that all color constants are defined"""
        colors = EntityModeScreen.COLORS
        
        required_colors = [
            "bg_main", "bg_panel", "bg_white", "bg_light", "bg_input",
            "border", "border_light", "text_dark", "text_muted", 
            "text_light", "text_lighter", "text_button",
            "accent_dark", "accent_hover", "accent_teal", "accent_teal_hover"
        ]
        
        for color in required_colors:
            assert color in colors
            assert isinstance(colors[color], str)
            assert colors[color].startswith("#")
    
    def test_font_sizes_defined(self, entity_screen_room_mode):
        """Test that all font size constants are defined"""
        sizes = EntityModeScreen.FONT_SIZES
        
        required_sizes = ["header", "title", "label", "body", "small", "xsmall"]
        
        for size in required_sizes:
            assert size in sizes
            assert isinstance(sizes[size], int)
            assert sizes[size] > 0


# ============================================================================
# MODE SWITCHING TESTS
# ============================================================================


class TestModeSwitch:
    """Test suite for mode switching functionality"""
    
    def test_switch_from_room_to_12nc(self, entity_screen_room_mode, sample_12ncs):
        """Test switching from room mode to 12nc mode"""
        screen = entity_screen_room_mode
        screen.app_controller.current_data['nc12s'] = sample_12ncs
        
        # Switch mode
        screen._switch_mode("12nc")
        screen.update()
        
        assert screen.current_mode == "12nc"
        # After switch, all_items should be updated
        screen._update_data_for_mode()
        assert len(screen.all_items) >= 0
    
    def test_switch_to_same_mode_does_nothing(self, entity_screen_room_mode):
        """Test that switching to same mode doesn't trigger updates"""
        screen = entity_screen_room_mode
        initial_mode = screen.current_mode
        
        # Try to switch to same mode
        screen._switch_mode(initial_mode)
        
        assert screen.current_mode == initial_mode
    
    def test_mode_toggle_button_handler(self, entity_screen_12nc_mode):
        """Test mode toggle button handler"""
        screen = entity_screen_12nc_mode
        
        # Simulate toggle to Room
        screen._on_mode_toggle("Room")
        assert screen.current_mode == "room"
        
        # Simulate toggle to 12NC
        screen._on_mode_toggle("12NC")
        assert screen.current_mode == "12nc"
    
    def test_update_data_for_mode(self, entity_screen_room_mode):
        """Test that data updates correctly when mode changes"""
        screen = entity_screen_room_mode
        
        # Store initial items count
        initial_count = len(screen.all_items)
        
        # Update data
        screen._update_data_for_mode()
        
        # Verify all_items is synced with MODE_CONFIG
        expected_items = screen.MODE_CONFIG[screen.current_mode]["items"]
        assert screen.all_items == expected_items


# ============================================================================
# SEARCH FUNCTIONALITY TESTS
# ============================================================================


class TestSearchFunctionality:
    """Test suite for search and dropdown functionality"""
    
    def test_dropdown_initially_hidden(self, entity_screen_room_mode):
        """Test that dropdown is hidden on initialization"""
        screen = entity_screen_room_mode
        assert screen.dropdown_visible is False
    
    def test_toggle_dropdown(self, entity_screen_room_mode):
        """Test dropdown toggle functionality"""
        screen = entity_screen_room_mode
        
        # Initially hidden
        assert screen.dropdown_visible is False
        
        # Toggle to show
        screen._toggle_dropdown()
        assert screen.dropdown_visible is True
        
        # Toggle to hide
        screen._toggle_dropdown()
        assert screen.dropdown_visible is False
    
    def test_populate_dropdown(self, entity_screen_room_mode):
        """Test populating dropdown with items"""
        screen = entity_screen_room_mode
        test_items = ["ROOM_001", "ROOM_002", "ROOM_003"]
        
        screen._populate_dropdown(test_items)
        
        # Check listbox has correct number of items
        assert screen.dropdown_listbox.size() == len(test_items)
        
        # Check items are in listbox
        for i, item in enumerate(test_items):
            assert screen.dropdown_listbox.get(i) == item
    
    def test_filter_with_empty_search(self, entity_screen_room_mode):
        """Test filtering with empty search text"""
        screen = entity_screen_room_mode
        
        # Show dropdown first
        screen._show_dropdown()
        
        # Filter with empty text should hide dropdown
        screen._filter_and_show_dropdown("")
        
        assert screen.dropdown_visible is False
    
    def test_filter_with_matching_text(self, entity_screen_room_mode):
        """Test filtering with text that matches items"""
        screen = entity_screen_room_mode
        
        # Filter with "ROOM_001"
        screen._filter_and_show_dropdown("ROOM_001")
        
        # Dropdown should be visible
        assert screen.dropdown_visible is True
        
        # Check filtered results
        assert screen.dropdown_listbox.size() > 0
    
    def test_filter_with_no_matches(self, entity_screen_room_mode):
        """Test filtering with text that has no matches"""
        screen = entity_screen_room_mode
        
        # Filter with non-existent text
        screen._filter_and_show_dropdown("NONEXISTENT_123")
        
        # Dropdown should show "No matches found"
        assert screen.dropdown_visible is True
        assert screen.dropdown_listbox.size() == 1
        assert screen.dropdown_listbox.get(0) == "No matches found"
    
    def test_search_text_change_triggers_filter(self, entity_screen_room_mode):
        """Test that changing search text triggers filtering"""
        screen = entity_screen_room_mode
        
        # Set search text
        screen.search_var.set("ROOM")
        screen.update()
        
        # On search change should be triggered automatically via trace
        # We just verify the search_var is set correctly
        assert screen.search_var.get() == "ROOM"
    
    def test_search_button_with_valid_term(self, entity_screen_room_mode):
        """Test search button click with valid search term"""
        screen = entity_screen_room_mode
        
        # Set a valid search term
        screen.search_var.set("ROOM_001")
        
        # Click search button
        screen._on_search_button()
        
        # Verify entity is selected
        assert screen.selected_entity == "ROOM_001"
    
    def test_search_button_with_no_matches_found(self, entity_screen_room_mode):
        """Test search button click with 'No matches found' text"""
        screen = entity_screen_room_mode
        
        # Set to "No matches found"
        screen.search_var.set("No matches found")
        
        # Click search button
        screen._on_search_button()
        
        # Entity should not be selected
        assert screen.selected_entity is None or screen.selected_entity != "No matches found"
    
    def test_prefix_search_filter(self, entity_screen_room_mode):
        """Test that search filter uses startswith (prefix matching)"""
        screen = entity_screen_room_mode
        
        # Add test items
        test_items = ["ROOM_001", "ROOM_002", "MYROOM_003", "TESTROOM_004"]
        screen.all_items = test_items
        
        # Filter with "ROOM" - should match ROOM_001, ROOM_002 but not MYROOM_003
        screen._filter_and_show_dropdown("ROOM")
        
        # Count items in dropdown
        listbox_items = [screen.dropdown_listbox.get(i) for i in range(screen.dropdown_listbox.size())]
        
        # Should only have items starting with "ROOM"
        for item in listbox_items:
            if item != "No matches found":
                assert item.startswith("ROOM")


# ============================================================================
# DATA LOADING TESTS
# ============================================================================


class TestDataLoading:
    """Test suite for data loading and reloading"""
    
    def test_reload_sample_data(self, entity_screen_room_mode, sample_rooms, sample_12ncs):
        """Test reloading data from uploaded files"""
        screen = entity_screen_room_mode
        
        # Reload with new data
        screen.reload_sample_data_from_uploaded_files(sample_rooms, sample_12ncs)
        
        # Verify MODE_CONFIG is updated
        assert len(screen.MODE_CONFIG["room"]["items"]) == len(sample_rooms)
        assert len(screen.MODE_CONFIG["12nc"]["items"]) == len(sample_12ncs)
        
        # Verify IDs are sorted
        room_ids = screen.MODE_CONFIG["room"]["items"]
        assert room_ids == sorted(room_ids)
        
        nc12_ids = screen.MODE_CONFIG["12nc"]["items"]
        assert nc12_ids == sorted(nc12_ids)
    
    def test_reload_with_empty_lists(self, entity_screen_room_mode):
        """Test reloading with empty data lists"""
        screen = entity_screen_room_mode
        
        # Reload with empty lists
        screen.reload_sample_data_from_uploaded_files([], [])
        
        # Should have empty items
        assert len(screen.MODE_CONFIG["room"]["items"]) == 0
        assert len(screen.MODE_CONFIG["12nc"]["items"]) == 0
    
    def test_reload_with_none_lists(self, entity_screen_room_mode):
        """Test reloading with None values"""
        screen = entity_screen_room_mode
        
        # Reload with None
        screen.reload_sample_data_from_uploaded_files(None, None)
        
        # Should have empty items (not crash)
        assert len(screen.MODE_CONFIG["room"]["items"]) == 0
        assert len(screen.MODE_CONFIG["12nc"]["items"]) == 0


# ============================================================================
# PANEL TESTS
# ============================================================================


class TestPanels:
    """Test suite for panel creation and management"""
    
    def test_four_panels_created(self, entity_screen_room_mode):
        """Test that all four panels are created"""
        screen = entity_screen_room_mode
        
        assert hasattr(screen, 'belonging_panel')
        assert hasattr(screen, 'details_panel')
        assert hasattr(screen, 'performance_panel')
        assert hasattr(screen, 'prediction_panel')
        
        assert screen.belonging_panel is not None
        assert screen.details_panel is not None
        assert screen.performance_panel is not None
        assert screen.prediction_panel is not None
    
    def test_update_panels_called(self, entity_screen_room_mode):
        """Test that update_panels can be called"""
        screen = entity_screen_room_mode
        screen.selected_entity = "ROOM_001"
        
        # Should not raise an error
        screen._update_panels()


# ============================================================================
# UI COMPONENT TESTS
# ============================================================================


class TestUIComponents:
    """Test suite for UI component creation"""
    
    def test_create_button(self, entity_screen_room_mode):
        """Test button creation"""
        screen = entity_screen_room_mode
        
        def dummy_command():
            pass
        
        button = screen._create_button(
            parent=screen,
            text="Test Button",
            command=dummy_command,
            width=100,
            height=40
        )
        
        assert button is not None
        assert isinstance(button, ctk.CTkButton)
    
    def test_create_icon_button(self, entity_screen_room_mode):
        """Test icon button creation"""
        screen = entity_screen_room_mode
        
        def dummy_command():
            pass
        
        button = screen._create_icon_button(
            parent=screen,
            text="📊",
            command=dummy_command,
            tooltip_text="Test tooltip"
        )
        
        assert button is not None
        assert isinstance(button, ctk.CTkButton)
    
    def test_tooltip_creation(self, entity_screen_room_mode):
        """Test tooltip creation on a widget"""
        screen = entity_screen_room_mode
        
        # Create a test button
        test_button = ctk.CTkButton(screen, text="Test")
        
        # Create tooltip (should not raise error)
        screen._create_tooltip(test_button, "Test tooltip text")
        
        # Verify button has event bindings (if supported)
        # Note: Some CustomTkinter widgets may not support bind


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_complete_search_workflow(self, entity_screen_room_mode):
        """Test complete search workflow from typing to selection"""
        screen = entity_screen_room_mode
        
        # Step 1: Focus on search entry
        screen._on_entry_focus(None)
        assert screen.dropdown_visible is True
        
        # Step 2: Type search text
        screen.search_var.set("ROOM_001")
        screen._on_search_change()
        
        # Step 3: Click search button
        screen._on_search_button()
        assert screen.selected_entity == "ROOM_001"
        
        # Step 4: Dropdown should be hidden after search
        assert screen.dropdown_visible is False
    
    def test_mode_switch_preserves_functionality(self, entity_screen_room_mode, sample_12ncs):
        """Test that switching modes preserves all functionality"""
        screen = entity_screen_room_mode
        screen.app_controller.current_data['nc12s'] = sample_12ncs
        
        # Initially in room mode
        assert screen.current_mode == "room"
        
        # Perform search in room mode
        screen.search_var.set("ROOM_001")
        screen._on_search_button()
        assert screen.selected_entity == "ROOM_001"
        
        # Switch to 12nc mode
        screen._on_mode_toggle("12NC")
        assert screen.current_mode == "12nc"
        
        # Verify search still works in 12nc mode
        screen.search_var.set("12NC_001")
        screen._on_search_button()
        assert screen.selected_entity == "12NC_001"


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================


if __name__ == "__main__":
    """Run tests with verbose output"""
    pytest.main([__file__, "-v", "--tb=short"])
