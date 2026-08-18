# style.py
# Final UX rebuild for EGL314 Photobooth
# Designed for 7-inch Raspberry Pi touchscreen

# Main colours
BG_COLOR = "#0E0F13"
PANEL_COLOR = "#171A21"
PREVIEW_BG = "#1B1D24"

TEXT_COLOR = "#F5F5F5"
MUTED_TEXT_COLOR = "#9CA3AF"

# Buttons
BUTTON_DARK = "#252833"
BUTTON_TEXT = "#FFFFFF"

CAPTURE_COLOR = "#2ECC71"
CONFIRM_COLOR = "#2ECC71"
RETAKE_COLOR = "#F5C542"

# Gallery selection
SELECTED_COLOR = "#F5C542"

# Fonts
# Titles/secondary/updates - non-button text
TITLE_FONT = ("DejaVu Sans", 24, "bold")
SECONDARY_FONT = ("DejaVu Sans", 18, "bold")
LABEL_FONT = ("DejaVu Sans", 10)
# Buttons - CAPTURE is the one deliberately biggest button in the app;
# every other button (including gallery RETAKE, which is smaller by
# container size, not font) shares this same uniform text size. The
# SETTINGS button uses its own small size, set directly where it's built.
BUTTON_FONT = ("DejaVu Sans", 16, "bold")
BIG_BUTTON_FONT = ("DejaVu Sans", 20, "bold")