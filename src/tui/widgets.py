from __future__ import annotations
import curses
from typing import List, Optional
from dataclasses import dataclass
from config import MAX_WIDTH, PORTRAIT_MODE


@dataclass
class ClickRegion:
    """Defines a clickable area in the terminal"""
    y_start: int
    y_end: int
    x_start: int
    x_end: int
    action_id: int


def get_safe_width(stdscr, max_override: int = 0) -> int:
    """Get safe width for text, respecting portrait mode limits"""
    _, w = stdscr.getmaxyx()
    safe_width = min(w - 1, MAX_WIDTH) if PORTRAIT_MODE else w - 1
    if max_override > 0:
        safe_width = min(safe_width, max_override)
    return max(20, safe_width)


def draw_header(stdscr, title: str, subtitle: str = "") -> None:
    """Draw header with title and optional subtitle (portrait-optimized)"""
    h, w = stdscr.getmaxyx()
    safe_w = get_safe_width(stdscr)
    
    if safe_w <= 0:
        return
    
    stdscr.attron(curses.A_REVERSE | curses.A_BOLD)
    # Pad with spaces for full width coverage
    stdscr.addstr(0, 0, " " * (safe_w - 1))
    
    title_text = f" {title} "[:safe_w - 2]
    try:
        stdscr.addstr(0, 0, title_text)
    except curses.error:
        pass
    
    if subtitle:
        sub = f" {subtitle} "
        col_pos = safe_w - len(sub) - 2
        if col_pos > len(title_text) + 2:
            try:
                stdscr.addstr(0, col_pos, sub[:safe_w - col_pos])
            except curses.error:
                pass
    
    stdscr.attroff(curses.A_REVERSE | curses.A_BOLD)
    
    # Draw separator line
    try:
        stdscr.addstr(1, 0, "─" * (safe_w - 1) if safe_w > 1 else "")
    except curses.error:
        pass


def draw_footer(stdscr, text: str) -> None:
    """Draw footer with help text (portrait-optimized)"""
    h, w = stdscr.getmaxyx()
    safe_w = get_safe_width(stdscr)
    
    if safe_w <= 0 or h <= 0:
        return
    
    stdscr.attron(curses.A_REVERSE)
    try:
        stdscr.addstr(h - 1, 0, " " * (safe_w - 1))
        footer_text = f" {text} "[:safe_w - 1]
        stdscr.addstr(h - 1, 0, footer_text)
    except curses.error:
        pass
    stdscr.attroff(curses.A_REVERSE)


def menu(stdscr, y: int, x: int, width: int, items: List[str], selected: int, touch_mode: bool = False) -> List[ClickRegion]:
    """
    Draw a menu and return clickable regions (portrait-optimized).
    touch_mode: If True, uses larger tap areas for touchscreen
    Returns: List of ClickRegion for each menu item
    """
    h, w = stdscr.getmaxyx()
    
    # Limit menu width for portrait mode
    if PORTRAIT_MODE:
        width = min(width, MAX_WIDTH - 4)
    
    max_rows = h - y - 3
    visible = items[:max_rows]
    regions: List[ClickRegion] = []
    
    # Touch mode: use 2 lines per item for bigger tap targets
    item_height = 2 if touch_mode else 1

    for i, label in enumerate(visible):
        # Truncate label to fit width
        line = f"  {label}"[:width - 2]
        y_pos = y + (i * item_height)
        
        try:
            if i == selected:
                stdscr.attron(curses.A_REVERSE | curses.A_BOLD)
            
            # Draw item
            prefix = "▶ " if i == selected else "  "
            display_line = prefix + label
            display_line = display_line[:width - 2]
            stdscr.addstr(y_pos, x, display_line)
            
            if i == selected:
                stdscr.attroff(curses.A_REVERSE | curses.A_BOLD)
        except curses.error:
            pass
        
        # Store click region (larger in touch mode)
        regions.append(ClickRegion(
            y_start=y_pos,
            y_end=y_pos + (item_height - 1),
            x_start=x,
            x_end=x + width - 1,
            action_id=i
        ))
    
    return regions


def draw_separator(stdscr, y: int, width: int = 0) -> None:
    """Draw a horizontal separator line"""
    h, w = stdscr.getmaxyx()
    if width == 0:
        width = get_safe_width(stdscr)
    try:
        stdscr.addstr(y, 0, "─" * width)
    except curses.error:
        pass


def draw_section_header(stdscr, y: int, x: int, title: str) -> None:
    """Draw a section header with title"""
    header = f"▸ {title}"[:get_safe_width(stdscr) - 2]
    try:
        stdscr.attron(curses.A_BOLD)
        stdscr.addstr(y, x, header)
        stdscr.attroff(curses.A_BOLD)
    except curses.error:
        pass


def draw_text_block(stdscr, y: int, x: int, width: int, lines: List[str]) -> None:
    """Draw a block of text with proper formatting (portrait-optimized)"""
    h, w = stdscr.getmaxyx()
    
    # Adjust width for portrait mode
    if PORTRAIT_MODE:
        width = min(width, MAX_WIDTH - 2)
    
    max_rows = h - y - 3
    for i in range(min(len(lines), max_rows)):
        line = lines[i]
        
        # Handle section headers (lines starting with special chars)
        is_header = line.startswith("[") or line.startswith("▸") or line.startswith("═")
        
        if is_header:
            stdscr.attron(curses.A_BOLD)
        
        # Truncate to width
        s = line[:width - 1]
        
        try:
            stdscr.addstr(y + i, x, s)
        except curses.error:
            pass
        
        if is_header:
            stdscr.attroff(curses.A_BOLD)


def draw_touch_button_bar(stdscr, buttons: List[tuple]) -> List[ClickRegion]:
    """
    Draw a touchscreen-friendly button bar at the bottom (portrait-optimized).
    buttons: List of (label, action_id) tuples
    Returns: List of ClickRegion for each button
    """
    h, w = stdscr.getmaxyx()
    safe_w = get_safe_width(stdscr)
    
    if h <= 2 or len(buttons) == 0:
        return []
    
    button_row = h - 2  # Reserve 1 line for separator, 1 for buttons
    regions: List[ClickRegion] = []
    
    # Draw separator
    try:
        stdscr.addstr(button_row - 1, 0, "═" * (safe_w - 1))
    except curses.error:
        pass
    
    # Calculate button width
    button_width = max(8, (safe_w - 2) // min(len(buttons), 3))
    
    for i, (label, action_id) in enumerate(buttons):
        x_pos = 1 + (i * button_width)
        if x_pos + button_width > safe_w - 1:
            break
        
        try:
            # Draw button with reverse video
            stdscr.attron(curses.A_REVERSE | curses.A_BOLD)
            btn_text = f" {label} "[:button_width]
            btn_text = btn_text.ljust(button_width)[:button_width]
            stdscr.addstr(button_row, x_pos, btn_text)
            stdscr.attroff(curses.A_REVERSE | curses.A_BOLD)
        except curses.error:
            pass
        
        # Store clickable region
        regions.append(ClickRegion(
            y_start=button_row,
            y_end=button_row,
            x_start=x_pos,
            x_end=x_pos + button_width - 1,
            action_id=action_id
        ))
    
    return regions


def check_mouse_click(mouse_event, regions: List[ClickRegion]) -> Optional[int]:
    """
    Check if mouse click is in one of the regions.
    Returns: action_id if click in region, else None
    """
    try:
        _, mx, my, _, bstate = mouse_event
        
        # Check for left click
        if not (bstate & curses.BUTTON1_CLICKED):
            return None
        
        for region in regions:
            if region.y_start <= my <= region.y_end and region.x_start <= mx <= region.x_end:
                return region.action_id
    except:
        pass
    
    return None