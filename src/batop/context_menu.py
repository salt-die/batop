"""A context menu gadget."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Self

from batgrl.gadgets.behaviors.button_behavior import ButtonBehavior
from batgrl.gadgets.grid_layout import GridLayout
from batgrl.gadgets.text import Point, Size, Text, new_cell, str_width
from batgrl.terminal.events import MouseEvent

from .colors import (
    MENU_FG,
    MENU_HOVER_BG,
    MENU_NORMAL_BG,
)

ItemCallback = Callable[[], None]
type MenuDict = dict[tuple[str, str], ItemCallback | MenuDict]
NESTED_SUFFIX = "▶"


class _MenuItem(ButtonBehavior, Text):
    def __init__(
        self,
        *,
        label: str,
        item_callback: ItemCallback | None = None,
        submenu: ContextMenu | None = None,
        size: Size,
    ):
        self.parent: ContextMenu | None
        self.label = label
        self.item_callback = item_callback
        self.submenu = submenu
        self._last_mouse_pos = Point(0, 0)

        super().__init__(
            default_cell=new_cell(fg_color=MENU_FG, bg_color=MENU_NORMAL_BG), size=size
        )

        self.add_str(label, pos=(0, 1))
        if self.submenu is not None:
            self.add_str(NESTED_SUFFIX, pos=(0, -2))

    def _repaint(self):
        self.canvas["bg_color"] = (
            MENU_HOVER_BG
            if (
                self.button_state == "hover"
                or (self.submenu is not None and self.submenu.is_enabled)
            )
            else MENU_NORMAL_BG
        )

    def update_hover(self):
        """Update parent menu and submenu on hover state."""
        self._repaint()

        index = self.parent.children.index(self)
        selected = self.parent._current_selection
        if selected != -1 and selected != index:
            self.parent.close_submenus()
            self.parent.children[selected].button_state = "normal"

        self.parent._current_selection = index
        if self.submenu is not None:
            self.submenu.open_menu()

    def update_normal(self):
        """Update parent menu and submenu on normal state."""
        self._repaint()
        if self.parent is None:
            return

        if self.submenu is None or not self.submenu.is_enabled:
            if self.parent._current_selection == self.parent.children.index(self):
                self.parent._current_selection = -1
        elif not self.submenu.collides_point(self._last_mouse_pos):
            self.submenu.close_menu()

    def on_mouse(self, mouse_event):
        """Save last mouse position."""
        self._last_mouse_pos = mouse_event.pos
        return super().on_mouse(mouse_event)

    def on_release(self):
        """Open submenu or call item callback on release."""
        if self.submenu is not None:
            self.submenu.open_menu()
        elif self.item_callback is not None:
            self.item_callback()
            self.parent.close_parents()


class ContextMenu(GridLayout):
    r"""
    A menu gadget.

    Menus are constructed with the class method :meth:`from_dict_of_dicts`. Each key of
    the dict should be a string label and each value should be a callable with no
    arguments or a dict (for a submenu).

    Once opened, a menu can be navigated with the mouse or arrow keys.

    Methods
    -------
    open_menu()
        Open menu.
    close_menu()
        Close menu.
    from_dict_of_dicts(...)
        Constructor to create a menu from a dict of dicts. This should be
        default way of constructing menus.
    """

    def __init__(self, size: Size):
        h, _ = size
        super().__init__(grid_rows=h, grid_columns=1, size=size)
        self._parent_menu: ContextMenu | None = None
        self._current_selection = -1
        self._submenus: list[ContextMenu] = []

    def open_menu(self):
        """Open the menu."""
        # Position menu so that its visible.
        if self._parent_menu is not None:
            y = self._parent_menu.y + self._parent_menu._current_selection
            x = self._parent_menu.right
            if x + self.width > self.parent.width:
                x = self._parent_menu.x - self.width

        else:
            y, x = self.pos
            if x + self.width > self.parent.width:
                x -= x + self.width - self.parent.width
        if y + self.height > self.parent.height:
            y -= y + self.height - self.parent.height
        if y < 0:
            y = 0
        if x < 0:
            x = 0

        self.pos = Point(y, x)
        self.is_enabled = True
        self.pull_to_front()

    def close_menu(self):
        """Close the menu."""
        self.is_enabled = False
        self._current_selection = -1
        self.close_submenus()

        for child in self.children:
            child.button_state = "normal"

    def close_submenus(self):
        """Close all submenus."""
        for menu in self._submenus:
            menu.close_menu()

    def close_parents(self):
        """Close all parent menus."""
        if self._parent_menu is None:
            self.close_menu()
        else:
            self._parent_menu.close_parents()

    def dispatch_mouse(self, mouse_event: MouseEvent) -> bool | None:
        """Close menu on non-colliding mouse-down event."""
        if (
            self._parent_menu is None
            and mouse_event.event_type == "mouse_down"
            and not any(
                child.collides_point(mouse_event.pos)
                for submenu in self._submenus
                if submenu.is_enabled
                for child in submenu.children
            )
        ):
            self.close_menu()
            return False
        return super().dispatch_mouse(mouse_event)

    def on_key(self, key_event):
        """Navigate menus with arrow keys and select menu items with enter."""
        for submenu in self._submenus:
            if submenu.is_enabled:
                if submenu.on_key(key_event):
                    return True
                else:
                    break

        if key_event.key == "up":
            i = self._current_selection
            if i == -1:
                i = len(self.children) - 1
            else:
                i = self._current_selection
                self.children[i].button_state = "normal"
                i = (i - 1) % len(self.children)

            for _ in self.children:
                if self.children[i].item_disabled:
                    i = (i - 1) % len(self.children)
                else:
                    self._current_selection = i
                    self.children[i]._hover()
                    self.close_submenus()
                    return True

            return False

        if key_event.key == "down":
            i = self._current_selection
            if i == -1:
                i = 0
            else:
                self.children[i].button_state = "normal"
                i = (i + 1) % len(self.children)

            for _ in self.children:
                if self.children[i].item_disabled:
                    i = (i + 1) % len(self.children)
                else:
                    self._current_selection = i
                    self.children[i]._hover()
                    self.close_submenus()
                    return True

            return False

        if key_event.key == "left":
            if self._current_selection != -1 and (
                (submenu := self.children[self._current_selection].submenu)
                and submenu.is_enabled
            ):
                submenu.close_menu()
                return True

        if key_event.key == "right":
            if self._current_selection != -1 and (
                (submenu := self.children[self._current_selection].submenu)
                and not submenu.is_enabled
            ):
                submenu.open_menu()
                if submenu.children:
                    submenu.children[0]._hover()
                    submenu.close_submenus()
                return True

        if key_event.key == "enter":
            if (
                self._current_selection != -1
                and (child := self.children[self._current_selection]).submenu is None
            ):
                child.on_release()
                return True

        return super().on_key(key_event)

    @classmethod
    def from_dict_of_dicts(cls, menu: MenuDict) -> Iterator[Self]:
        """
        Create and yield menus from a dict of dicts. Callables should either have no
        arguments for a normal menu item, or one argument for a toggle menu item.

        Parameters
        ----------
        menu : MenuDict
            The menu as a dict of dicts.

        Yields
        ------
        ContextMenu
            The menu or one of its submenus.
        """
        height = len(menu)
        width = max(
            (str_width(label) + 2 + isinstance(callable_or_dict, dict) * 2)
            for label, callable_or_dict in menu.items()
        )
        menu_gadget = cls(size=(height, width))

        for label, value in menu.items():
            if isinstance(value, Callable):
                menu_item = _MenuItem(label=label, item_callback=value, size=(1, width))
            elif isinstance(value, dict):
                submenus = ContextMenu.from_dict_of_dicts(value)
                for submenu in submenus:
                    menu_gadget._submenus.append(submenu)
                    submenu._parent_menu = menu_gadget
                    submenu.is_enabled = False
                    yield submenu

                menu_item = _MenuItem(label=label, submenu=submenu, size=(1, width))
            else:
                raise TypeError(f"expected Callable or dict, got {type(value)}")

            menu_gadget.add_gadget(menu_item)

        yield menu_gadget
