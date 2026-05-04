ROOT_LIGHT_STYLESHEET = """
    QWidget {
        background-color: white;
        color: black;
    }
"""

TITLE_STYLESHEET = """
    QLabel {
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 30px;
        font-weight: 700;
        background-color: transparent;
        color: white;
    }
    .QFrame {
        background-color: #FF2C67;
    }
"""

SIDE_PANEL_STYLESHEET = """
    .QFrame {
        background-color: white;
    }
    QPushButton {
        padding: 10px;
        font-size: 16px;
        font-weight: 600;
        text-align: left;
        border-radius: 0;
        border: 1px solid gray;
        background-color: rgba(239, 104, 32, 0.4);
    }
    QPushButton:hover {
        background-color: rgba(239, 104, 32, 0.6);
    }
    QPushButton:pressed {
        background-color: rgba(239, 104, 32, 0.7);
    }
"""

SELECTED_WINDOW_BUTTON_STYLESHEET = """
    QPushButton, QPushButton:hover, QPushButton:pressed {
        background-color: rgba(239, 104, 32, 0.9);
    }
"""

PANEL_BORDER_STYLESHEET = """
    .QFrame {
        border: 1px solid #4A8F67;
        padding: 0;
    }
"""

DENOISE_PANEL_STYLESHEET = """
    QStackedWidget, QFrame {
        background-color: rgb(254, 246, 238);
    }
    QLabel {
        background-color: transparent;
    }
    QLabel#heading {
        color: #4D0000;
        font-size: 40px;
        font-weight: 700;
    }
    QPushButton {
        background-color: transparent;
    }
"""

DENOISE_PANEL_SUBFRAME_STYLESHEET = """
    .QFrame {
        margin: 10px 150px;
    }
"""

UPLOAD_CARD_STYLESHEET = """
    QFrame {
        padding: 5px 2px;
        border: 1px solid black;
        background-color: #E8EDF2;
    }
    QLabel {
        border: none;
        font-size: 13px;
        color: #406AAF;
    }
    QPushButton {
        padding: 8px;
        border: 1px solid black;
        background-color: rgb(239, 104, 32);
        color: white;
        font-family: "Source Sans", sans-serif;
        font-size: 20px;
    }
    QPushButton:hover {
        background-color: rgb(220, 100, 30);
    }
    QPushButton:pressed {
        background-color: rgb(210, 90, 20);
    }
"""

CONTROL_FRAME_STYLESHEET = """
    .QFrame {
        margin: 0px;
        background-color: white;
        font-family: monospace;
    }
    QSlider {
        background-color: transparent;
    }
    QSlider::groove:horizontal {
        border: 1px solid #bbb;
        height: 8px;
        background: #eee;
        margin: 2px 0;
        border-radius: 4px;
    }
    QSlider::sub-page:horizontal {
        background: #A492EE;
        height: 8px;
        border-radius: 4px;
    }
    QSlider::handle:horizontal {
        background: #6452E7; /* Slightly darker purple for contrast */
        border: 1px solid #6452E7;
        width: 18px;
        height: 18px;
        margin: -5px 0; /* This centers the handle over the 8px groove */
        border-radius: 9px;
    }
    QSlider::handle:horizontal:hover {
        background: #8473FF;
    }
"""

SAVE_ACKNOWLEDGE_STYLESHEET = """
    QPushButton {
        border: none;
        margin: 20px;
        font-family: monospace;
        font-size: 16px;
        background: transparent;
    }
"""

SUBMIT_BUTTON_STYLESHEET = """
    QPushButton {
        margin: 20px 0px;
        padding: 8px;
        border: 4px solid rgb(239, 104, 32);
        border-radius: 20px;
        background-color: rgb(239, 104, 32);
        color: white;
        font-family: "Source Sans", sans-serif;
        font-size: 16px;
    }
    QPushButton:hover {
        background-color: rgb(220, 100, 30);
        border: 4px solid rgb(220, 100, 30);
    }
    QPushButton:pressed {
        background-color: rgb(210, 90, 20);
        border: 4px solid rgb(210, 90, 20);
    }
"""

MEDIA_PLAYER_STYLESHEET = """
    .QFrame {
        border: 1px solid #406AAF;
        border-radius: 10px;
        margin: 10px 0px;
    }
"""

METRICS_FRAME_STYLESHEET = """
    QFrame {
        margin: 0px;
    }
"""