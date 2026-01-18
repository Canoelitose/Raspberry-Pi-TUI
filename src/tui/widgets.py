from __future__ import annotations
import curses
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ClickRegion:
    """Defines a clickable area in the terminal"""
    y_start: int
    y_end: int
    x_start: int
    x_end: int
    action_id: int


def draw_header(stdscr, title: str, subtitle: str = "") -> None:
    """Draw header with title and optional subtitle"""
    h, w = stdscr.getmaxyx()
    if w <= 0:
        return
    stdscr.attron(curses.A_REVERSE | curses.A_BOLD)
    # Use w-1 to avoid curses overflow error
    stdscr.addstr(0, 0, " " * (w - 1))
    title_text = f" ➤ {title} "
    try:
        stdscr.addstr(0, 0, title_text[: w - 1])
    except curses.error:
        pass
    if subtitle:
        sub = f"{subtitle} "
        col_pos = w - len(sub) - 2
        if col_pos > len(title_text):
            try:
                stdscr.addstr(0, col_pos, sub[: w - col_pos - 1])
            except curses.error:
                pass
    stdscr.attroff(curses.A_REVERSE | curses.A_BOLD)
    
    # Draw separator line
    try:
        stdscr.addstr(1, 0, "─" * (w - 1) if w > 1 else "")
    except curses.error:
        pass


def draw_footer(stdscr, text: str) -> None:
    """Draw footer with help text"""
    h, w = stdscr.getmaxyx()
    if w <= 0 or h <= 0:
        return
    stdscr.attron(curses.A_REVERSE)
    # Use w-1 to avoid curses overflow error
    try:
        stdscr.addstr(h - 1, 0, " " * (w - 1))
        footer_text = f" {text} "
        stdscr.addstr(h - 1, 0, footer_text[: w - 1])
    except curses.error:
        pass
    stdscr.attroff(curses.A_REVERSE)


def menu(stdscr, y: int, x: int, width: int, items: List[str], selected: int, touch_mode: bool = False) -> List[ClickRegion]:
    """
    Draw a menu and return clickable regions.
    touch_mode: If True, uses larger tap areas for touchscreen
    Returns: List of ClickRegion for each menu item
    """
    h, w = stdscr.getmaxyx()
    max_rows = h - y - 3
    visible = items[:max_rows]
    regions: List[ClickRegion] = []
    
    # Touch mode: use 2 lines per item for bigger tap targets
    item_height = 2 if touch_mode else 1

    for i, label in enumerate(visible):
        line = f"  {label}"[: width - 2]
        y_pos = y + (i * item_height)
        
        try:
            if i == selected:
                stdscr.attron(curses.A_REVERSE | curses.A_BOLD)
            
            # Draw item without boxes
            stdscr.addstr(y_pos, x, "▶ " + line if i == selected else "  " + line)
            
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
        width = max(1, w - 1)
    try:
        stdscr.addstr(y, 0, "─" * width)
    except curses.error:
        pass


def draw_section_header(stdscr, y: int, x: int, title: str) -> None:
    """Draw a section header with title"""
    header = f"▸ {title}"
    try:
        stdscr.attron(curses.A_BOLD)
        stdscr.addstr(y, x, header)
        stdscr.attroff(curses.A_BOLD)
    except curses.error:
        pass


def draw_text_block(stdscr, y: int, x: int, width: int, lines: List[str]) -> None:
    """Draw a block of text with proper formatting"""
    h, w = stdscr.getmaxyx()
    max_rows = h - y - 3
    for i in range(min(len(lines), max_rows)):
        line = lines[i]
        # Handle section headers (lines starting with [SECTION])
        if line.startswith("["):
            stdscr.attron(curses.A_BOLD)
        
        s = line[: width - 1]
        try:
            stdscr.addstr(y + i, x, s)
        except curses.error:
            pass
        
        if line.startswith("["):
            stdscr.attroff(curses.A_BOLD)


def draw_button(stdscr, y: int, x: int, text: str, width: int, selected: bool = False) -> ClickRegion:
    """Draw a button and return its clickable region"""
    try:
        if selected:
            stdscr.attron(curses.A_REVERSE | curses.A_BOLD)
        
        button_text = f" [ {text} ] ".center(width)
        stdscr.addstr(y, x, button_text[:width])
        
        if selected:
            stdscr.attroff(curses.A_REVERSE | curses.A_BOLD)
    except curses.error:
        pass
    
    return ClickRegion(
        y_start=y,
        y_end=y,
        x_start=x,
        x_end=x + width - 1,
        action_id=0
    )


def draw_touch_button_bar(stdscr, buttons: List[tuple]) -> List[ClickRegion]:
    """
    Draw a touchscreen-friendly button bar at the bottom.
    buttons: List of (label, action_id) tuples
    Returns: List of ClickRegion for each button
    
    Example: draw_touch_button_bar(stdscr, [("Back", 0), ("Refresh", 1), ("Quit", 2)])
    """
    h, w = stdscr.getmaxyx()
    if h <= 2 or len(buttons) == 0:
        return []
    
    button_row = h - 2  # Reserve 1 line for separator, 1 for buttons
    regions: List[ClickRegion] = []
    
    # Draw separator
    try:
        stdscr.addstr(button_row - 1, 0, "═" * (w - 1))
    except curses.error:
        pass
    
    # Draw buttons
    button_width = max(10, (w - 2) // len(buttons))
    for i, (label, action_id) in enumerate(buttons):
        x_pos = 1 + (i * button_width)
        if x_pos + button_width > w - 1:
            break
        
        try:
            # Draw button with reverse video
            stdscr.attron(curses.A_REVERSE | curses.A_BOLD)
            btn_text = f" {label} "[:button_width]
            btn_text = btn_text.center(button_width)
            stdscr.addstr(button_row, x_pos, btn_text[:button_width])
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