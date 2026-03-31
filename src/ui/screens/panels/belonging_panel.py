"""Belonging Panel - Shows related entities (12NCs for rooms, rooms for 12NCs)"""

import customtkinter as ctk
from typing import Callable, Optional


class BelongingPanel:
    """Manages the Belonging List panel content and updates"""
    
    def __init__(self, panel_widget, colors, font_sizes, get_font_func, navigate_callback: Optional[Callable] = None, get_description_callback: Optional[Callable] = None):
        """Initialize the belonging panel manager
        
        Args:
            panel_widget: The CTkFrame panel widget
            colors: Dictionary of color constants
            font_sizes: Dictionary of font sizes
            get_font_func: Function to get cached fonts
            navigate_callback: Function to navigate to another entity (entity_id, mode)
            get_description_callback: Function to get entity description (entity_id, mode)
        """
        self.panel = panel_widget
        self.COLORS = colors
        self.FONT_SIZES = font_sizes
        self._get_font = get_font_func
        self.navigate_callback = navigate_callback
        self.get_description_callback = get_description_callback
        self.content_frame = None
    
    def update(self, entity_obj, mode):
        """Update panel with related entities
        Args:
            entity_obj: Room or TwelveNC object
            mode: Current mode ('room' or '12nc')
        """
        # Find the content frame in the panel
        self.content_frame = self._find_content_frame()
        
        if not self.content_frame:
            return
        
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Create scrollable frame for belonging list
        scroll_frame = ctk.CTkScrollableFrame(
            self.content_frame,
            fg_color="transparent",
            corner_radius=0
        )
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Mode-specific content
        if mode == "room":
            self._show_room_components(scroll_frame, entity_obj)
        else:  # 12nc mode
            self._show_12nc_rooms(scroll_frame, entity_obj)
    
    def _find_content_frame(self):
        """Find the content frame within the panel widget
        Args: None
        Returns: The content frame widget or None if not found
        """
        # Look for the content frame at grid row=1
        for child in self.panel.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                try:
                    grid_info = child.grid_info()
                    if grid_info and grid_info.get('row') == 1:
                        return child
                except:
                    continue
        return None
    
    def _show_room_components(self, parent, room_obj):
        """Show 12NC components in the room
        
        Args:
            parent: Parent widget
            room_obj: Room object
        
        Does:
            Creates interactive list of 12NC components with quantities.
            Highlights the component with maximum quantity in pastel green (if unique).
        """
        # Header
        header_label = ctk.CTkLabel(
            parent,
            text=f"Components in {room_obj.id}",
            font=self._get_font(size=self.FONT_SIZES["title"], weight="bold"),
            text_color=self.COLORS["text_dark"]
        )
        header_label.pack(pady=(0, 15))
        
        # Check if there are components
        if not room_obj.components:
            no_data_label = ctk.CTkLabel(
                parent,
                text="No components found",
                font=self._get_font(size=self.FONT_SIZES["body"]),
                text_color=self.COLORS["text_light"]
            )
            no_data_label.pack(pady=20)
            return
        
        # Sort components by quantity (descending) - single iteration
        sorted_components = sorted(room_obj.components.items(), key=lambda x: x[1], reverse=True)
        
        # Highlight first item only if its quantity is unique (not tied with second)
        max_qty = sorted_components[0][1]
        has_unique_max = len(sorted_components) == 1 or sorted_components[1][1] < max_qty
        
        # Display all components
        for idx, (nc12_id, quantity) in enumerate(sorted_components):
            should_highlight = (idx == 0 and has_unique_max)
            self._add_belonging_item(parent, nc12_id, quantity, "12nc", should_highlight)
    
    def _show_12nc_rooms(self, parent, nc12_obj):
        """Show rooms containing this 12NC
        
        Args:
            parent: Parent widget
            nc12_obj: TwelveNC object
        
        Does:
            Creates interactive list of rooms containing the 12NC with quantities.
            Highlights the room with maximum quantity in pastel green (if unique).
        """
        # Header
        header_label = ctk.CTkLabel(
            parent,
            text=f"Rooms containing {nc12_obj.id}",
            font=self._get_font(size=self.FONT_SIZES["title"], weight="bold"),
            text_color=self.COLORS["text_dark"]
        )
        header_label.pack(pady=(0, 15))
        
        # Check if deployed in any rooms
        if not nc12_obj.components:
            no_data_label = ctk.CTkLabel(
                parent,
                text="Not deployed in any rooms",
                font=self._get_font(size=self.FONT_SIZES["body"]),
                text_color=self.COLORS["text_light"]
            )
            no_data_label.pack(pady=20)
            return
        
        # Sort rooms by quantity (descending) - single iteration
        sorted_rooms = sorted(nc12_obj.components.items(), key=lambda x: x[1], reverse=True)
        
        # Highlight first item only if its quantity is unique (not tied with second)
        max_qty = sorted_rooms[0][1]
        has_unique_max = len(sorted_rooms) == 1 or sorted_rooms[1][1] < max_qty
        
        # Display all rooms
        for idx, (room_id, quantity) in enumerate(sorted_rooms):
            should_highlight = (idx == 0 and has_unique_max)
            self._add_belonging_item(parent, room_id, quantity, "room", should_highlight)
    
    def _add_belonging_item(self, parent, item_id, quantity, target_mode, should_highlight=False):
        """Add an interactive belonging item row

        Args:
            parent: Parent widget
            item_id: ID of the item
            quantity: Quantity of this item
            target_mode: Mode to switch to when clicked ('12nc' or 'room')
            should_highlight: Whether to highlight with pastel green (max quantity)
        
        Does:
            Creates a clickable item card that navigates to the entity when clicked.
            Highlights in pastel green if it has the maximum unique quantity.
        """
        # Determine colors based on highlight status
        bg_color = "#C8E6C9" if should_highlight else self.COLORS["bg_white"]  # Pastel green
        hover_color = "#A5D6A7" if should_highlight else "#F0F4F8"  # Slightly darker green or light gray
        
        # Create a frame container (not button - buttons don't work well as containers)
        item_frame = ctk.CTkFrame(
            parent,
            fg_color=bg_color,
            corner_radius=8,
            border_width=1,
            border_color=self.COLORS["border"],
            height=60
        )
        item_frame.pack(fill="x", pady=5, padx=5)
        item_frame.pack_propagate(False)  # Maintain fixed height
        
        # Create inner container for proper layout
        inner_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        inner_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Left side container for ID and description
        left_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True)
        
        # Item ID with icon
        icon = "🔧" if target_mode == "12nc" else "🏠"
        id_label = ctk.CTkLabel(
            left_frame,
            text=f"{icon} {item_id}",
            font=self._get_font(size=self.FONT_SIZES["body"], weight="bold"),
            text_color=self.COLORS["text_dark"],
            anchor="w"
        )
        id_label.pack(side="left")
        
        # Description (if callback provided) - same line as ID
        desc_label = None
        if self.get_description_callback:
            description = self.get_description_callback(item_id, target_mode)
            if description:
                desc_label = ctk.CTkLabel(
                    left_frame,
                    text=f" - {description}",
                    font=self._get_font(size=self.FONT_SIZES["small"]),
                    text_color="#888888",
                    anchor="w"
                )
                desc_label.pack(side="left", padx=(5, 0))
        
        # Quantity badge (right side)
        qty_text = f"Qty: {quantity}"
        if should_highlight:
            qty_text += " ⭐"  # Add star for max quantity
        
        qty_badge = ctk.CTkLabel(
            inner_frame,
            text=qty_text,
            font=self._get_font(size=self.FONT_SIZES["small"], weight="bold"),
            text_color=self.COLORS["bg_white"],
            fg_color=self.COLORS["accent_teal"],
            corner_radius=6,
            padx=10,
            pady=4
        )
        qty_badge.pack(side="right")
        
        # Make entire card clickable by binding click events to all widgets
        click_handler = lambda e: self._navigate_to_entity(item_id, target_mode)
        widgets_to_bind = [item_frame, inner_frame, left_frame, id_label, qty_badge]
        if desc_label:
            widgets_to_bind.append(desc_label)
        
        for widget in widgets_to_bind:
            widget.bind("<Button-1>", click_handler)
            widget.configure(cursor="hand2")
        
        # Add hover effect
        def on_enter(e):
            item_frame.configure(fg_color=hover_color)
        
        def on_leave(e):
            item_frame.configure(fg_color=bg_color)
        
        for widget in widgets_to_bind:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
    
    def _navigate_to_entity(self, entity_id: str, target_mode: str):
        """Navigate to another entity
        
        Args:
            entity_id: ID of the entity to navigate to
            target_mode: Mode to switch to ('12nc' or 'room')
        
        Does:
            Calls the navigation callback to switch to the target entity's mode and display it.
        """
        if self.navigate_callback:
            self.navigate_callback(entity_id, target_mode)
        else:
            print(f"Navigation to {entity_id} in {target_mode} mode (no callback set)")
