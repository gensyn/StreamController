"""
Author: Core447
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

# Import Python modules
import cv2
import threading
from loguru import logger as log
from math import floor
from time import sleep

# Import globals
import globals as gl

# Import own modules
from src.backend.DeckManagement.ImageHelpers import image2pixbuf, is_transparent

class DeckGroup(Adw.PreferencesGroup):
    def __init__(self, settings_page):
        super().__init__(title="Deck Settings", description="Applies only to current page")

        self.add(Brightness(settings_page))
        self.add(Screensaver(settings_page))

class Brightness(Adw.PreferencesRow):
    def __init__(self, settings_page: "PageSettings", **kwargs):
        super().__init__()
        self.settings_page = settings_page
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.overwrite_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.overwrite_box)

        self.overwrite_label = Gtk.Label(label="overwrite deck's defaut brightness", hexpand=True, xalign=0)
        self.overwrite_box.append(self.overwrite_label)

        self.overwrite_switch = Gtk.Switch()
        self.overwrite_switch.connect("state-set", self.on_toggle_overwrite)
        self.overwrite_box.append(self.overwrite_switch)

        self.config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, visible=False)
        self.main_box.append(self.config_box)

        self.config_box.append(Gtk.Separator(hexpand=True, margin_top=10, margin_bottom=10))

        self.label = Gtk.Label(label="Brightness", hexpand=True, xalign=0)
        self.config_box.append(self.label)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min=0, max=100, step=1)
        self.scale.set_draw_value(True)
        self.set_scale_initial_value()
        self.scale.connect("value-changed", self.on_value_changed)
        self.config_box.append(self.scale)

    def set_scale_initial_value(self):
        # Load default scalar value
        current_page = None
        if hasattr(self.settings_page.deck_page.deck_controller, "active_page"):
            current_page = self.settings_page.deck_page.deck_controller.active_page

        self.load_defaults_from_page()

    def set_scale_from_page(self, page):
        if page == None:
            self.scale.set_sensitive(False)
            self.main_box.append(Gtk.Label(label="Error", hexpand=True, xalign=0, css_classes=["red-color"]))
            return

        brightness = page["brightness"]["value"]
        self.scale.set_value(brightness)

    def on_value_changed(self, scale):
        value = round(scale.get_value())
        # update value in page
        self.settings_page.deck_page.deck_controller.active_page["brightness"]["value"] = value
        self.settings_page.deck_page.deck_controller.active_page.save()
        # update deck without reload of page
        self.settings_page.deck_page.deck_controller.set_brightness(value)

    def on_toggle_overwrite(self, toggle_switch, state):
        self.config_box.set_visible(state)
        # Update page
        self.settings_page.deck_page.deck_controller.active_page["brightness"]["overwrite"] = state
        # Save
        self.settings_page.deck_page.deck_controller.active_page.save()
        self.settings_page.deck_page.deck_controller.reload_page(load_background=False, load_keys=False)

    def load_defaults_from_page(self):
        # Verify if page exists
        if not hasattr(self.settings_page.deck_page.deck_controller, "active_page"):
            return
        if self.settings_page.deck_page.deck_controller.active_page == None:
            return

        original_values = self.settings_page.deck_page.deck_controller.active_page.copy()
        
        # Set defaut values 
        self.settings_page.deck_page.deck_controller.active_page.setdefault("brightness", {})
        self.settings_page.deck_page.deck_controller.active_page["brightness"].setdefault("value", 50)
        self.settings_page.deck_page.deck_controller.active_page["brightness"].setdefault("overwrite", False)

        # Save if changed
        if original_values != self.settings_page.deck_page.deck_controller.active_page:
            self.settings_page.deck_page.deck_controller.active_page.save()

        # Update ui
        self.set_scale_from_page(self.settings_page.deck_page.deck_controller.active_page)
        self.overwrite_switch.set_active(self.settings_page.deck_page.deck_controller.active_page["brightness"]["overwrite"])

class Screensaver(Adw.PreferencesRow):
    def __init__(self, settings_page: "PageSettings", **kwargs):
        super().__init__(css_classes=["no-click"])
        self.settings_page = settings_page
        self.build()
    
    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.overwrite_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.overwrite_box)

        self.overwrite_label = Gtk.Label(label="overwrite deck's default screensaver settings", hexpand=True, xalign=0)
        self.overwrite_box.append(self.overwrite_label)

        self.overwrite_switch = Gtk.Switch()
        self.overwrite_switch.connect("state-set", self.on_toggle_overwrite)
        self.overwrite_box.append(self.overwrite_switch)

        self.config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, visible=False)
        self.main_box.append(self.config_box)

        self.config_box.append(Gtk.Separator(margin_top=10, margin_bottom=10))

        self.enable_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_bottom=15)
        self.config_box.append(self.enable_box)

        self.enable_label = Gtk.Label(label="Enable", hexpand=True, xalign=0)
        self.enable_box.append(self.enable_label)

        self.enable_switch = Gtk.Switch()
        self.enable_switch.connect("state-set", self.on_toggle_enable)
        self.enable_box.append(self.enable_switch)

        self.time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.config_box.append(self.time_box)

        self.time_label = Gtk.Label(label="Enable after (mins)", hexpand=True, xalign=0)
        self.time_box.append(self.time_label)

        self.time_spinner = Gtk.SpinButton.new_with_range(1, 60, 1)
        self.time_spinner.connect("value-changed", self.on_change_time)
        self.time_box.append(self.time_spinner)

        self.media_selector_label = Gtk.Label(label="Media to show:", hexpand=True, xalign=0)
        self.config_box.append(self.media_selector_label)

        self.media_selector_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.CENTER)
        self.config_box.append(self.media_selector_box)

        self.media_selector_button = Gtk.Button(label="Select", css_classes=["page-settings-media-selector"])
        self.media_selector_button.connect("clicked", self.choose_with_file_dialog)
        self.media_selector_box.append(self.media_selector_button)

        self.media_selector_image = Gtk.Image() # Will be bind to the button by self.set_thumbnail()

        self.loop_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_bottom=15)
        self.config_box.append(self.loop_box)

        self.loop_label = Gtk.Label(label="Loop", hexpand=True, xalign=0)
        self.loop_box.append(self.loop_label)

        self.loop_switch = Gtk.Switch()
        self.loop_switch.connect("state-set", self.on_toggle_loop)
        self.loop_box.append(self.loop_switch)

        self.fps_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.config_box.append(self.fps_box)

        self.fps_label = Gtk.Label(label="FPS", hexpand=True, xalign=0)
        self.fps_box.append(self.fps_label)

        self.fps_spinner = Gtk.SpinButton.new_with_range(1, 30, 1)
        self.fps_spinner.connect("value-changed", self.on_change_fps)
        self.fps_box.append(self.fps_spinner)

        self.brightness_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.config_box.append(self.brightness_box)

        self.brightness_label = Gtk.Label(label="Brightness", hexpand=True, xalign=0)
        self.brightness_box.append(self.brightness_label)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min=0, max=100, step=1)
        self.scale.connect("value-changed", self.on_change_brightness)
        self.brightness_box.append(self.scale)

        self.load_defaults_from_page()

    def load_defaults_from_page(self):
        # Verify if page exists
        if not hasattr(self.settings_page.deck_page.deck_controller, "active_page"):
            return
        if self.settings_page.deck_page.deck_controller.active_page == None:
            return

        original_values = None
        if hasattr(self.settings_page.deck_page.deck_controller.active_page, "screensaver"):
            original_values = self.settings_page.deck_page.deck_controller.active_page["screensaver"].copy()
        # Set default values
        self.settings_page.deck_page.deck_controller.active_page.setdefault("screensaver", {})
        overwrite = self.settings_page.deck_page.deck_controller.active_page["screensaver"].setdefault("overwrite", False)
        enable = self.settings_page.deck_page.deck_controller.active_page["screensaver"].setdefault("enable", False)
        path = self.settings_page.deck_page.deck_controller.active_page["screensaver"].setdefault("path", None)
        loop = self.settings_page.deck_page.deck_controller.active_page["screensaver"].setdefault("loop", False)
        fps = self.settings_page.deck_page.deck_controller.active_page["screensaver"].setdefault("fps", 30)
        time = self.settings_page.deck_page.deck_controller.active_page["screensaver"].setdefault("time-delay", 5)
        brightness = self.settings_page.deck_page.deck_controller.active_page["screensaver"].setdefault("brightness", 75)

        # Update ui
        self.overwrite_switch.set_active(overwrite)
        self.enable_switch.set_active(enable)
        self.loop_switch.set_active(loop)
        self.fps_spinner.set_value(fps)
        self.time_spinner.set_value(time)
        self.scale.set_value(brightness)
        self.set_thumbnail(path)

        self.config_box.set_visible(overwrite)

        # Save if changed
        if original_values != self.settings_page.deck_page.deck_controller.active_page["screensaver"]:
            self.settings_page.deck_page.deck_controller.active_page.save()


    def on_toggle_enable(self, toggle_switch, state):
        self.settings_page.deck_page.deck_controller.active_page["screensaver"]["enable"] = state
        self.settings_page.deck_page.deck_controller.active_page.save()

        self.settings_page.deck_page.deck_controller.screen_saver.set_enable(state)

        # Reload page
        self.settings_page.deck_page.deck_controller.reload_page(load_brightness=False, load_background=False, load_keys=False)


    def on_toggle_overwrite(self, toggle_switch, state):
        self.settings_page.deck_page.deck_controller.active_page["screensaver"]["overwrite"] = state
        # Save
        self.settings_page.deck_page.deck_controller.active_page.save()

        # Update screensaver config box's visibility
        self.config_box.set_visible(state)

        # Reload page
        self.settings_page.deck_page.deck_controller.reload_page(load_brightness=False, load_background=False, load_keys=False)

    def on_toggle_loop(self, toggle_switch, state):
        self.settings_page.deck_page.deck_controller.active_page["screensaver"]["loop"] = state
        self.settings_page.deck_page.deck_controller.active_page.save()
        self.settings_page.deck_page.deck_controller.screen_saver.loop = state

    def on_change_fps(self, spinner):
        self.settings_page.deck_page.deck_controller.active_page["screensaver"]["fps"] = spinner.get_value_as_int()
        self.settings_page.deck_page.deck_controller.active_page.save()
        self.settings_page.deck_page.deck_controller.screen_saver.fps = spinner.get_value_as_int()

    def on_change_time(self, spinner):
        self.settings_page.deck_page.deck_controller.active_page["screensaver"]["time-delay"] = spinner.get_value_as_int()
        self.settings_page.deck_page.deck_controller.active_page.save()
        self.settings_page.deck_page.deck_controller.screen_saver.set_time(spinner.get_value_as_int())

    def on_change_brightness(self, scale):
        self.settings_page.deck_page.deck_controller.active_page["screensaver"]["brightness"] = scale.get_value()
        self.settings_page.deck_page.deck_controller.active_page.save()
        self.settings_page.deck_page.deck_controller.screen_saver.set_brightness(scale.get_value())

    def set_thumbnail(self, file_path):
        if file_path == None:
            return
        image = gl.media_manager.get_thumbnail(file_path)
        pixbuf = image2pixbuf(image)
        self.media_selector_image.set_from_pixbuf(pixbuf)
        self.media_selector_button.set_child(self.media_selector_image)

    def choose_with_file_dialog(self, button):
        dialog = ChooseScreensaverDialog(self)

class ChooseScreensaverDialog(Gtk.FileDialog):
    def __init__(self, screensaver_row: Screensaver):
        super().__init__(title="Select Background",
                         accept_label="Select")
        self.screensaver_row = screensaver_row
        self.open(callback=self.callback)

    def callback(self, dialog, result):
        try:
            selected_file = self.open_finish(result)
            file_path = selected_file.get_path()
        except GLib.Error as err:
            log.error(err)
            return
        
        # Add image as asset to asset manager
        asset_id = gl.asset_manager.add(file_path)
        asset_path = gl.asset_manager.get_by_id(asset_id)["internal-path"]
        
        self.screensaver_row.set_thumbnail(asset_path)
        self.screensaver_row.settings_page.deck_page.deck_controller.active_page["screensaver"]["path"] = asset_path
        self.screensaver_row.settings_page.deck_page.deck_controller.active_page.save()