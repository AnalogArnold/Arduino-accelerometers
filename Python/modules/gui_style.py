##################################################################################################################
#
# Style module contains all style information for the GUI such as fonts, colors, paddings, etc. It can be thought of
# as something like a CSS sheet and some JS scripting for a HTML page.
#
# Version: 2.4 (July 2025)
# Author: Michael Darcy
# License: MIT
# Copyright (C) 2025 AnalogArnold
#
##################################################################################################################
import dearpygui.dearpygui as dpg

def setup_gui_theme():
    """Sets up the theme (colors, fonts, padding, etc.) for the GUI."""
    # Each tuple: (RGB color, [list of theme color constants])

    theme_col_groups = [
        ((44, 44, 46), [dpg.mvThemeCol_Text, dpg.mvThemeCol_TextDisabled]),
        ((242, 242, 247), [dpg.mvThemeCol_WindowBg]),
        ((229, 229, 234), [dpg.mvThemeCol_ChildBg, dpg.mvThemeCol_PopupBg, dpg.mvThemeCol_TableHeaderBg,
                           dpg.mvThemeCol_TableRowBg, dpg.mvThemeCol_HeaderHovered, dpg.mvThemeCol_HeaderActive]),
        ((210, 221, 219), [dpg.mvThemeCol_FrameBg, dpg.mvThemeCol_TitleBg, dpg.mvThemeCol_MenuBarBg,
                           dpg.mvThemeCol_ScrollbarBg, dpg.mvThemeCol_Button, dpg.mvThemeCol_Tab,
                           dpg.mvThemeCol_Header]),
        ((185, 197, 195), [dpg.mvThemeCol_FrameBgHovered, dpg.mvThemeCol_ScrollbarGrab, dpg.mvThemeCol_SliderGrab,
                           dpg.mvThemeCol_ButtonHovered, dpg.mvThemeCol_TabHovered]),
        ((163, 178, 175), [dpg.mvThemeCol_FrameBgActive, dpg.mvThemeCol_TitleBgActive,
                           dpg.mvThemeCol_ScrollbarGrabHovered, dpg.mvThemeCol_SliderGrabActive,
                           dpg.mvThemeCol_ButtonActive, dpg.mvThemeCol_TabActive, dpg.mvThemeCol_Separator,
                           dpg.mvThemeCol_SeparatorHovered, dpg.mvThemeCol_SeparatorActive]),
        ((154, 165, 163), [dpg.mvThemeCol_ScrollbarGrabActive, dpg.mvThemeCol_CheckMark]),
        ((217, 228, 226), [dpg.mvThemeCol_TitleBgCollapsed])
    ]
    style_var_groups = [
        (dpg.mvStyleVar_WindowPadding, 15, 10),
        (dpg.mvStyleVar_WindowRounding, 1),
        (dpg.mvStyleVar_FrameRounding, 5),
        (dpg.mvStyleVar_FramePadding, 5, 3),
        (dpg.mvStyleVar_ChildRounding, 5),
        (dpg.mvStyleVar_TabRounding, 6),
        (dpg.mvStyleVar_ItemSpacing, 8, 4),
        (dpg.mvStyleVar_ScrollbarSize, 13),
        (dpg.mvStyleVar_TabBarBorderSize, 1),
        (dpg.mvStyleVar_WindowTitleAlign, 0.50, 0.50),
        (dpg.mvStyleVar_ButtonTextAlign, 0.50, 0.50),
    ]
    # Add the above values to the global theme
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            for color, col_list in theme_col_groups:
                for col in col_list:
                    dpg.add_theme_color(col, color, category=dpg.mvThemeCat_Core)
            for style_var in style_var_groups:
                if len(style_var) == 2:
                    var, value = style_var
                    dpg.add_theme_style(var, value, category=dpg.mvThemeCat_Core)
                else:
                    var, x_val, y_val = style_var
                    dpg.add_theme_style(var, x_val, y_val, category=dpg.mvThemeCat_Core)

    # Define the item theme to make the connect/disconnect buttons stand out more
    with dpg.theme() as item_theme_connect:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (146, 209, 161), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (123, 198, 140), category=dpg.mvThemeCat_Core)

    with dpg.theme() as item_theme_disconnect:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (219, 98, 77), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (190, 90, 72), category=dpg.mvThemeCat_Core)

    # Change the default font to a bigger and more legible one
    with dpg.font_registry():
        default_font = dpg.add_font("fonts/SFPRODISPLAYREGULAR.OTF", 18)  # Default font
        header_font = dpg.add_font("fonts/SFPRODISPLAYBOLD.OTF", 30)  # Font for the header
        child_header_font = dpg.add_font("fonts/SFPRODISPLAYMEDIUM.OTF", 20)  # Font for the table headers

    child_header_font_group = ["data_log_header", "post_processing_header", "status_header", "detected_sensors_header"]
    for item in child_header_font_group:
        dpg.bind_item_font(item, child_header_font)

    # Bind the theme to the GUI
    dpg.bind_theme(global_theme)
    dpg.bind_font(default_font)
    dpg.bind_item_font("program_header", header_font)
    dpg.bind_item_font("data_log_header", child_header_font)
    dpg.bind_item_font("post_processing_header", child_header_font)
    dpg.bind_item_font("status_header", child_header_font)
    dpg.bind_item_font("detected_sensors_header", child_header_font)
    dpg.bind_item_theme("connect_button", item_theme_connect)
    dpg.bind_item_theme("disconnect_button", item_theme_disconnect)

def toggle_interval_box(sender):
    """Toggles on/off the visibility of the interval options depending on the processing choice - it is only
    relevant for the FFT."""
    if sender == "post":
        # Post-processing tab fields
        if dpg.get_value("processing_choice_post") == "Fast Fourier transform":
            dpg.configure_item("interval_box_post", show=True)
        else:
            # Hide everything, including the custom interval input.
            dpg.set_value("custom_interval_choice", False)
            toggle_custom_interval_input()
            dpg.configure_item("interval_box_post", show=False)
    else:
        # Processing in the "data acquisition" tab fields
        if dpg.get_value("processing_choice") == "Fast Fourier transform":
            dpg.configure_item("interval_box", show=True)
        else:
            dpg.configure_item("interval_box", show=False)

def toggle_custom_interval_input():
    """Toggles on/off the visibility of the custom interval input depending on the custom interval checkbox."""
    if dpg.get_value("custom_interval_choice"):
        dpg.configure_item("custom_interval_value", show=True)
    else:
        dpg.configure_item("custom_interval_value", show=False)
