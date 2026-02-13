import os
import json
import cv2
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from PIL import Image, ImageTk
import threading
import shutil
import sys
from datetime import datetime
from facerec import *
from register import *
from dbHandler import *

# ---------- RESOURCE PATH HELPER (for PyInstaller) ----------
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ---------- THEME ----------
# Tailwind‑like dark / neon palette for a modern look
APP_BG = "#050816"          # main app background (almost black with a hint of blue)
CARD_BG = "#020617"         # panels/cards
PANEL_BG = "#0F172A"        # inner panels
ACCENT = "#6366F1"          # primary accent (indigo)
ACCENT_ALT = "#22D3EE"      # secondary accent (cyan)
TEXT_PRIMARY = "#E5E7EB"    # main text
TEXT_MUTED = "#9CA3AF"      # secondary text
BORDER_COLOR = "#1F2937"    # subtle borders

# Path for storing simple user credentials
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

# Global variables initialization
active_page = 0
thread_event = None
left_frame = None
right_frame = None
heading = None
webcam = None
img_label = None
img_read = None
img_list = []
slide_caption = None
slide_control_panel = None
current_slide = -1
camera_index_var = None
available_cameras = []
recent_detections = []  # list of (name, timestamp_string)
recent_history_frame = None
detected_list_frame = None
users = {}

# Creating tkinter window
root = tk.Tk()
print("RUNNING FILE:", os.path.abspath(__file__))
print("PYTHON EXE:", sys.executable)
root.title("CRIMINAL DETECTION SYSTEM (UPDATED)")
root.configure(bg=APP_BG)

# --- Responsive sizing / window behavior ---
# On Windows, forcing "-fullscreen" often interacts badly with DPI scaling and can make
# widgets appear cut off. Default to maximized ("zoomed") and offer a fullscreen toggle.
try:
    root.state("zoomed")
except Exception:
    pass

# Toggle fullscreen with F11; exit fullscreen with Esc.
def _toggle_fullscreen(event=None):
    try:
        root.attributes("-fullscreen", not bool(root.attributes("-fullscreen")))
    except Exception:
        # If fullscreen isn't supported, ignore.
        return

root.bind("<F11>", _toggle_fullscreen)
root.bind("<Escape>", lambda e: root.attributes("-fullscreen", False))

_SW = max(root.winfo_screenwidth(), 800)
_SH = max(root.winfo_screenheight(), 600)
_SCALE = min(_SW / 1366.0, _SH / 768.0)  # baseline laptop-ish resolution

def scaled(px: int, min_px: int = 10, max_px: int | None = None) -> int:
    """Scale a pixel-ish value based on screen size to avoid overflow on small screens."""
    val = int(px * _SCALE)
    if max_px is not None:
        val = min(val, max_px)
    return max(min_px, val)


def load_users():
    """Load user credentials from USERS_FILE, creating a default admin if needed."""
    global users
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    users = data
                else:
                    users = {}
        except Exception:
            users = {}
    else:
        users = {}

    # Ensure default admin account exists
    if "admin@1234" not in users:
        users["admin@1234"] = "12345678"
    save_users()


def save_users():
    """Persist user credentials to USERS_FILE."""
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        print("Failed to save users:", e)


def add_recent_detection(name: str):
    """Record a newly detected criminal with the current timestamp, keeping only the last 5."""
    global recent_detections
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Insert at the front so newest is at top
    recent_detections.insert(0, (name, timestamp))
    # Keep only last 5 detections
    if len(recent_detections) > 5:
        recent_detections = recent_detections[:5]
    update_recent_history_ui()


def update_recent_history_ui():
    """Refresh the 'Recent Detections' column in the CCTV page, if visible."""
    global recent_history_frame
    if recent_history_frame is None:
        return

    for w in recent_history_frame.winfo_children():
        w.destroy()

    if not recent_detections:
        tk.Label(
            recent_history_frame,
            text="No detections yet.",
            bg=CARD_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", scaled(11, min_px=10, max_px=13)),
        ).pack(pady=6)
        return

    for name, ts in recent_detections:
        row = tk.Frame(recent_history_frame, bg=CARD_BG)
        row.pack(fill="x", padx=6, pady=4)

        name_lbl = tk.Label(
            row,
            text=name,
            bg=CARD_BG,
            fg=ACCENT_ALT,
            font=("Segoe UI", scaled(12, min_px=10, max_px=14), "bold"),
            cursor="hand2",
        )
        name_lbl.pack(side="left", anchor="w")
        # capture name with default arg
        name_lbl.bind("<Button-1>", lambda e, n=name: showCriminalProfile(n))

        time_lbl = tk.Label(
            row,
            text=ts,
            bg=CARD_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", scaled(10, min_px=9, max_px=12)),
        )
        time_lbl.pack(side="right", anchor="e")

# Create Pages (stacked full‑window frames)
pages = []
for i in range(4):
    pages.append(tk.Frame(root, bg=APP_BG))
    pages[i].pack(side="top", fill="both", expand=True)
    pages[i].place(x=0, y=0, relwidth=1, relheight=1)

# Function to go back to previous page
def goBack():
    global active_page, thread_event, webcam

    if (active_page == 3 and thread_event is not None and not thread_event.is_set()):
        thread_event.set()
        try:
            webcam.release()
        except Exception:
            pass

    for widget in pages[active_page].winfo_children():
        widget.destroy()

    pages[0].lift()
    active_page = 0


def logout():
    """Logout current user and return to the Login / Create Account screen."""
    global thread_event, webcam, auth_frame

    # Stop any running surveillance thread and release camera
    if thread_event is not None and not thread_event.is_set():
        thread_event.set()
        try:
            if webcam is not None:
                webcam.release()
        except Exception:
            pass

    # Rebuild the authentication UI overlay and show the auth choice screen
    try:
        if auth_frame is not None:
            auth_frame.destroy()
    except Exception:
        pass

    build_auth_ui()

# Function to set up basic page structure
def basicPageSetup(pageNo):
    global left_frame, right_frame, heading

    back_img = tk.PhotoImage(file=resource_path("back.png"))
    back_button = tk.Button(
        pages[pageNo],
        image=back_img,
        bg=APP_BG,
        bd=0,
        highlightthickness=0,
        activebackground=APP_BG,
        cursor="hand2",
        command=goBack,
    )
    back_button.image = back_img
    back_button.place(x=10, y=10)

    heading = tk.Label(
        pages[pageNo],
        fg=TEXT_PRIMARY,
        bg=APP_BG,
        font=("Segoe UI", scaled(22, min_px=16, max_px=30), "bold"),
        pady=scaled(10, min_px=6, max_px=16),
    )
    heading.pack()

    # Underline / separator for a dashboard‑like feel
    sep = tk.Frame(pages[pageNo], bg=BORDER_COLOR, height=2)
    sep.pack(fill="x", padx=scaled(40, min_px=20, max_px=60), pady=(0, scaled(10, min_px=6, max_px=14)))

    content = tk.Frame(pages[pageNo], bg=APP_BG, pady=20)
    content.pack(expand=True, fill="both", padx=scaled(30, min_px=16, max_px=48), pady=scaled(20, min_px=12, max_px=32))

    left_frame = tk.Frame(
        content,
        bg=CARD_BG,
        bd=0,
        highlightbackground=BORDER_COLOR,
        highlightthickness=1,
    )
    left_frame.grid(row=0, column=0, sticky="nsew")

    right_frame = tk.LabelFrame(
        content,
        text="Detected Criminals",
        bg=CARD_BG,
        font=("Segoe UI", scaled(18, min_px=14, max_px=24), "bold"),
        bd=0,
        fg=ACCENT_ALT,
        labelanchor="n",
        highlightbackground=BORDER_COLOR,
        highlightthickness=1,
    )
    right_frame.grid(row=0, column=1, sticky="nsew", padx=scaled(20, min_px=10, max_px=32), pady=scaled(10, min_px=6, max_px=20))

    content.grid_columnconfigure(0, weight=1, uniform="group1")
    content.grid_columnconfigure(1, weight=1, uniform="group1")
    content.grid_rowconfigure(0, weight=1)

# Function to show image on a frame
def showImage(frame, img_size):
    global img_label, left_frame

    if img_size <= 0:
        img_size = 200
    img = cv2.resize(frame, (img_size, img_size))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(img)
    img = ImageTk.PhotoImage(img)
    if (img_label is None):
        img_label = tk.Label(left_frame, image=img, bg=CARD_BG)
        img_label.image = img
        img_label.pack(padx=20)
    else:
        img_label.configure(image=img)
        img_label.image = img

# Function to move to the next or previous image in a slideshow
def getNewSlide(control):
    global img_list, current_slide

    if (len(img_list) > 1):
        if (control == "prev"):
            current_slide = (current_slide - 1) % len(img_list)
        else:
            current_slide = (current_slide + 1) % len(img_list)

        img_size = max(left_frame.winfo_height() - 200, 200)
        showImage(img_list[current_slide], img_size)

        slide_caption.configure(text="Image {} of {}".format(current_slide + 1, len(img_list)))

# Function to select multiple images
def selectMultiImage(opt_menu, menu_var):
    global img_list, current_slide, slide_caption, slide_control_panel

    filetype = [("images", "*.jpg *.jpeg *.png")]
    path_list = filedialog.askopenfilenames(title="Choose at least 5 images", filetypes=filetype)

    if (len(path_list) < 5):
        messagebox.showerror("Error", "Choose at least 5 images.")
    else:
        img_list = []
        current_slide = -1

        # Resetting slide control panel
        if (slide_control_panel != None):
            slide_control_panel.destroy()

        # Creating Image list
        for path in path_list:
            img_list.append(cv2.imread(path))

        # Creating choices for profile pic menu
        menu_var.set("")
        opt_menu['menu'].delete(0, 'end')

        for i in range(len(img_list)):
            ch = "Image " + str(i + 1)
            opt_menu['menu'].add_command(label=ch, command=tk._setit(menu_var, ch))
            menu_var.set("Image 1")

        # Creating slideshow of images
        img_size = max(left_frame.winfo_height() - 200, 200)
        current_slide += 1
        showImage(img_list[current_slide], img_size)

        slide_control_panel = tk.Frame(left_frame, bg="black", pady=20)
        slide_control_panel.pack()

        back_img = tk.PhotoImage(file=resource_path("previous.png"))
        next_img = tk.PhotoImage(file=resource_path("next.png"))

        prev_slide = tk.Button(slide_control_panel, image=back_img, bg="black", bd=0, highlightthickness=0,
                               activebackground="black", command=lambda: getNewSlide("prev"))
        prev_slide.image = back_img
        prev_slide.grid(row=0, column=0, padx=60)

        slide_caption = tk.Label(slide_control_panel, text="Image 1 of {}".format(len(img_list)), fg="#ff9800",
                                  bg="black", font="Arial 15 bold")
        slide_caption.grid(row=0, column=1)

        next_slide = tk.Button(slide_control_panel, image=next_img, bg="black", bd=0, highlightthickness=0,
                               activebackground="black", command=lambda: getNewSlide("next"))
        next_slide.image = next_img
        next_slide.grid(row=0, column=2, padx=60)

# Function to register criminals
def register(entries, required, menu_var):
    global img_list

    # Checking if no image selected
    if (len(img_list) == 0):
        messagebox.showerror("Error", "Select Images first.")
        return

    # Fetching data from entries
    entry_data = {}
    for i, entry in enumerate(entries):
        val = entry[1].get()

        if (len(val) == 0 and required[i] == 1):
            messagebox.showerror("Field Error", "Required field missing :\n\n%s" % (entry[0]))
            return
        else:
            entry_data[entry[0]] = val.lower()

    # Setting Directory
    path = os.path.join('face_samples', "temp_criminal")
    if not os.path.isdir(path):
        os.mkdir(path)

    no_face = []
    for i, img in enumerate(img_list):
        # Storing Images in directory
        id = registerCriminal(img, path, i + 1)
        if (id != None):
            no_face.append(id)

    # check if any image doesn't contain face
    if (len(no_face) > 0):
        no_face_st = ""
        for i in no_face:
            no_face_st += "Image " + str(i) + ", "
        messagebox.showerror("Registration Error", "Registration failed!\n\nFollowing images doesn't contain"
                                                    " face or Face is too small:\n\n%s" % (no_face_st))
        shutil.rmtree(path, ignore_errors=True)
    else:
        # Storing data in database
        rowId = insertData(entry_data)

        if (rowId > 0):
            messagebox.showinfo("Success", "Criminal Registered Successfully.")
            shutil.move(path, os.path.join('face_samples', entry_data["Name"]))

            # save profile pic
            profile_img_num = int(menu_var.get().split(' ')[1]) - 1
            if not os.path.isdir("profile_pics"):
                os.mkdir("profile_pics")
            cv2.imwrite("profile_pics/criminal %d.png" % rowId, img_list[profile_img_num])

            goBack()
        else:
            shutil.rmtree(path, ignore_errors=True)
            messagebox.showerror("Database Error", "Some error occurred while storing data.")

# Function to handle canvas scroll event (reused for other canvas)
def on_configure(event, canvas, win):
    canvas.configure(scrollregion=canvas.bbox('all'))
    canvas.itemconfig(win, width=event.width)

# Function to get the Register Page
def getPage1():
    global active_page, left_frame, right_frame, heading, img_label
    active_page = 1
    img_label = None
    opt_menu = None
    menu_var = tk.StringVar(root)
    pages[1].lift()

    basicPageSetup(1)
    heading.configure(text="Register Criminal", font=("Arial", scaled(30, min_px=18, max_px=34), "bold"), fg="#9C27B0")
    right_frame.configure(text="Enter Criminal Details", fg="#9C27B0")

    btn_grid = tk.Frame(left_frame, bg="black")
    btn_grid.pack()

    tk.Button(
        btn_grid,
        text="Select Images",
        command=lambda: selectMultiImage(opt_menu, menu_var),
        font=("Arial", scaled(15, min_px=12, max_px=18), "bold"),
        bg="#9C27B0",
              fg="white", pady=10, bd=0, highlightthickness=0, activebackground="#673AB7",
              activeforeground="white").grid(row=0, column=0, padx=25, pady=25)

    # Creating Scrollable Frame for right_frame
    canvas = tk.Canvas(right_frame, bg="black", highlightthickness=0)
    canvas.pack(side="left", fill="both", expand="true", padx=scaled(30, min_px=12, max_px=30))
    scrollbar = tk.Scrollbar(
        right_frame,
        command=canvas.yview,
        width=scaled(20, min_px=14, max_px=22),
        troughcolor="black",
        bd=0,
                             activebackground="#00bcd4", bg="#9C27B0", relief="raised")
    scrollbar.pack(side="left", fill="y")

    scroll_frame = tk.Frame(canvas, bg="black", pady=20)
    scroll_win = canvas.create_window((0, 0), window=scroll_frame, anchor='nw')

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind('<Configure>', lambda event, canvas=canvas, win=scroll_win: on_configure(event, canvas, win))

    tk.Label(
        scroll_frame,
        text="* Required Fields",
        bg=APP_BG,
        fg=TEXT_MUTED,
        font=("Segoe UI", scaled(12, min_px=10, max_px=14), "italic"),
    ).pack()
    # Adding Input Fields
    input_fields = ("Name", "Father's Name", "Mother's Name", "Gender", "DOB(yyyy-mm-dd)", "Blood Group",
                    "Identification Mark", "Nationality", "Religion", "Crimes Done", "Profile Image",)
    ip_len = len(input_fields)
    required = [1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0]

    entries = []
    for i, field in enumerate(input_fields):
        row = tk.Frame(scroll_frame, bg=CARD_BG)
        row.pack(side="top", fill="x", pady=15)

        label = tk.Text(
            row,
            width=20,
            height=1,
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
            font=("Segoe UI", scaled(13, min_px=11, max_px=15)),
            highlightthickness=0,
            bd=0,
        )
        label.insert("insert", field)
        label.pack(side="left")

        if (required[i] == 1):
            label.tag_configure(
                "star",
                foreground=ACCENT,
                font=("Segoe UI", scaled(13, min_px=11, max_px=15), "bold"),
            )
            label.insert("end", "  *", "star")
        label.configure(state="disabled")

        if (i != ip_len - 1):
            ent = tk.Entry(
                row,
                font=("Segoe UI", scaled(13, min_px=11, max_px=15)),
                selectbackground=ACCENT_ALT,
                bg=PANEL_BG,
                fg=TEXT_PRIMARY,
                insertbackground=TEXT_PRIMARY,
                relief="flat",
            )
            ent.pack(side="right", expand="true", fill="x", padx=10)
            entries.append((field, ent))
        else:
            menu_var.set("Image 1")
            choices = ["Image 1"]
            opt_menu = tk.OptionMenu(row, menu_var, *choices)
            opt_menu.pack(side="right", fill="x", expand=True, padx=10)
            opt_menu.configure(
                font=("Segoe UI", scaled(13, min_px=11, max_px=15)),
                bg=ACCENT,
                fg=TEXT_PRIMARY,
                bd=0,
                highlightthickness=0,
                activebackground=ACCENT_ALT,
                activeforeground=TEXT_PRIMARY,
            )
            menu = opt_menu.nametowidget(opt_menu.menuname)
            menu.configure(
                font=("Segoe UI", scaled(13, min_px=11, max_px=15)),
                bg=PANEL_BG,
                fg=TEXT_PRIMARY,
                activebackground=ACCENT_ALT,
                activeforeground=TEXT_PRIMARY,
                bd=0,
            )

    tk.Button(
        scroll_frame,
        text="Register Criminal",
        command=lambda: register(entries, required, menu_var),
        font=("Segoe UI", scaled(15, min_px=12, max_px=18), "bold"),
        bg=ACCENT,
        fg=TEXT_PRIMARY,
        pady=10,
        padx=30,
        bd=0,
        highlightthickness=0,
        activebackground="#4F46E5",
        activeforeground=TEXT_PRIMARY,
        cursor="hand2",
    ).pack(pady=25)

# Function to show criminal profile
def showCriminalProfile(name):
    top = tk.Toplevel(bg="black")
    top.title("Criminal Profile")
    # Size the profile window relative to the screen so it doesn't open off-screen.
    w = min(1500, int(_SW * 0.9))
    h = min(900, int(_SH * 0.85))
    top.geometry("%dx%d+%d+%d" % (w, h, root.winfo_x() + 10, root.winfo_y() + 10))

    tk.Label(
        top,
        text="Criminal Profile",
        fg=TEXT_PRIMARY,
        bg=APP_BG,
        font=("Segoe UI", scaled(22, min_px=16, max_px=28), "bold"),
        pady=scaled(10, min_px=6, max_px=16),
    ).pack()

    content = tk.Frame(top, bg=APP_BG, pady=20)
    content.pack(expand="true", fill="both")
    content.grid_columnconfigure(0, weight=3, uniform="group1")
    content.grid_columnconfigure(1, weight=5, uniform="group1")
    content.grid_rowconfigure(0, weight=1)

    (id, crim_data) = retrieveData(name)

    if id is not None:
        path = os.path.join("profile_pics", "criminal %d.png" % id)
        profile_img = cv2.imread(path)

        # Scale image to window size so it fits on smaller screens.
        img_side = min(500, int(min(_SW, _SH) * 0.35))
        profile_img = cv2.resize(profile_img, (img_side, img_side))
        img = cv2.cvtColor(profile_img, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img = ImageTk.PhotoImage(img)
        img_label = tk.Label(content, image=img, bg=APP_BG)
        img_label.image = img
        img_label.grid(row=0, column=0)

        info_frame = tk.Frame(content, bg=APP_BG)
        info_frame.grid(row=0, column=1, sticky='w')

        for i, item in enumerate(crim_data.items()):
            tk.Label(
                info_frame,
                text=item[0],
                pady=scaled(15, min_px=8, max_px=16),
                fg=TEXT_MUTED,
                font=("Segoe UI", scaled(14, min_px=12, max_px=18), "bold"),
                bg=APP_BG,
            ).grid(row=i, column=0,
                                                                                                           sticky='w')
            tk.Label(
                info_frame,
                text=":",
                fg=TEXT_MUTED,
                padx=scaled(50, min_px=18, max_px=50),
                font=("Segoe UI", scaled(14, min_px=12, max_px=18), "bold"),
                bg=APP_BG,
            ).grid(row=i, column=1)
            val = "---" if (item[1] == "") else item[1]
            tk.Label(
                info_frame,
                text=val.capitalize(),
                fg=TEXT_PRIMARY,
                font=("Segoe UI", scaled(14, min_px=12, max_px=18)),
                bg=APP_BG,
            ).grid(row=i, column=2, sticky='w')
    else:
        tk.Label(content, text="Error: Criminal data not found", fg="white", bg="black", font="Arial 15 bold").pack()

# Function to start recognition process
def startRecognition():
    global img_read, img_label

    if (img_label is None):
        messagebox.showerror("Error", "No image selected. ")
        return

    crims_found_labels = []
    for wid in right_frame.winfo_children():
        wid.destroy()

    frame = cv2.flip(img_read, 1, 0)
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    face_coords = detect_faces(gray_frame)

    if (len(face_coords) == 0):
        messagebox.showerror("Error", "Image doesn't contain any face or face is too small.")
    else:
        (model, names) = train_model()
        print('Training Successful. Detecting Faces')
        (frame, recognized) = recognize_face(model, frame, gray_frame, face_coords, names)

        img_size = max(left_frame.winfo_height() - 40, 200)
        frame = cv2.flip(frame, 1, 0)
        showImage(frame, img_size)

        if (len(recognized) == 0):
            messagebox.showerror("Error", "No criminal recognized.")
            return

        for i, crim in enumerate(recognized):
            crims_found_labels.append(tk.Label(right_frame, text=crim[0], bg="#9C27B0",
                                                font="Arial 15 bold", pady=20))
            crims_found_labels[i].pack(fill="x", padx=20, pady=10)
            crims_found_labels[i].bind("<Button-1>", lambda e, name=crim[0]: showCriminalProfile(name))
            # Also push into recent detections history
            add_recent_detection(crim[0])

# Function to select image
def selectImage():
    global left_frame, img_label, img_read
    for wid in right_frame.winfo_children():
        wid.destroy()

    filetype = [("images", "*.jpg *.jpeg *.png")]
    path = filedialog.askopenfilename(title="Choose a image", filetypes=filetype)

    if (len(path) > 0):
        img_read = cv2.imread(path)

        img_size = max(left_frame.winfo_height() - 40, 200)
        showImage(img_read, img_size)

# Function to get the Detection Page
def getPage2():
    global active_page, left_frame, right_frame, img_label, heading
    img_label = None
    active_page = 2
    pages[2].lift()

    basicPageSetup(2)
    heading.configure(
        text="Detect Criminal",
        fg=ACCENT_ALT,
        font=("Segoe UI", scaled(26, min_px=18, max_px=32), "bold"),
    )
    right_frame.configure(text="Detected Criminals", fg=ACCENT_ALT, bg=CARD_BG)

    btn_grid = tk.Frame(left_frame, bg=CARD_BG)
    btn_grid.pack()

    tk.Button(
        btn_grid,
        text="Select Image",
        command=selectImage,
        font=("Segoe UI", scaled(15, min_px=12, max_px=18), "bold"),
        padx=scaled(20, min_px=10, max_px=20),
        bg=ACCENT,
        fg=TEXT_PRIMARY,
        pady=10,
        bd=0,
        highlightthickness=0,
        activebackground="#4F46E5",
        activeforeground=TEXT_PRIMARY,
        cursor="hand2",
    ).grid(row=0, column=0, padx=25, pady=25)
    tk.Button(
        btn_grid,
        text="Recognize",
        command=startRecognition,
        font=("Segoe UI", scaled(15, min_px=12, max_px=18), "bold"),
        padx=scaled(20, min_px=10, max_px=20),
        bg=ACCENT_ALT,
        fg=APP_BG,
        pady=10,
        bd=0,
        highlightthickness=0,
        activebackground="#06B6D4",
        activeforeground=APP_BG,
        cursor="hand2",
    ).grid(row=0, column=1, padx=25, pady=25)

# Helper to detect available camera indices
def detect_cameras(max_devices: int = 5):
    cams = []
    for i in range(max_devices):
        cap = cv2.VideoCapture(i)
        if cap is not None and cap.isOpened():
            ret, _ = cap.read()
            if ret:
                cams.append(i)
        if cap is not None:
            cap.release()
    if not cams:
        cams = [0]
    return cams


# Function to handle video stream for recognition
def videoLoop(model, names, camera_index):
    global thread_event, left_frame, webcam, img_label, detected_list_frame
    webcam = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    old_recognized = []
    crims_found_labels = []
    img_label = None

    try:
        while not thread_event.is_set():
            # Loop until the camera is working
            while (True):
                # Put the image from the webcam into 'frame'
                (return_val, frame) = webcam.read()
                if (return_val == True):
                    break
                else:
                    print("Failed to open webcam. Trying again...")

            # Flip the image (optional)
            frame = cv2.flip(frame, 1, 0)
            # Convert frame to grayscale
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect Faces
            face_coords = detect_faces(gray_frame)
            (frame, recognized) = recognize_face(model, frame, gray_frame, face_coords, names)

            # Recognize Faces
            recog_names = [item[0] for item in recognized]
            if (recog_names != old_recognized):
                # Update the current detections panel (left side of right_frame on CCTV page)
                parent = detected_list_frame if detected_list_frame is not None else right_frame
                for wid in parent.winfo_children():
                    wid.destroy()
                del (crims_found_labels[:])

                for i, crim in enumerate(recognized):
                    name = crim[0]
                    crims_found_labels.append(
                        tk.Label(
                            parent,
                            text=name,
                            bg=PANEL_BG,
                            fg=TEXT_PRIMARY,
                            font=("Segoe UI", scaled(13, min_px=11, max_px=15), "bold"),
                            pady=10,
                            padx=12,
                            cursor="hand2",
                        )
                    )
                    crims_found_labels[i].pack(fill="x", padx=10, pady=6)
                    crims_found_labels[i].bind("<Button-1>", lambda e, n=name: showCriminalProfile(n))
                    # Record in recent history list
                    add_recent_detection(name)

                old_recognized = recog_names

            # Display Video stream
            img_size = min(left_frame.winfo_width(), left_frame.winfo_height()) - 20

            showImage(frame, max(img_size, 200))

    except RuntimeError:
        print("[INFO]Caught Runtime Error")
    except tk.TclError:
        print("[INFO]Caught Tcl Error")

# Start video surveillance with the selected camera
def startVideoSurveillance(model, names):
    global thread_event, camera_index_var

    # Avoid starting multiple threads accidentally
    if thread_event is not None and not thread_event.is_set():
        messagebox.showinfo("Info", "Surveillance is already running.")
        return

    try:
        camera_index = int(camera_index_var.get())
    except Exception:
        camera_index = 0

    thread_event = threading.Event()
    thread = threading.Thread(target=videoLoop, args=(model, names, camera_index))
    thread.daemon = True
    thread.start()


# Function to get the Video Surveillance Page
def getPage3():
    global active_page, video_loop, left_frame, right_frame, thread_event, heading, camera_index_var, available_cameras
    global detected_list_frame, recent_history_frame
    active_page = 3
    pages[3].lift()

    basicPageSetup(3)
    heading.configure(
        text="Live CCTV Surveillance",
        font=("Segoe UI", scaled(30, min_px=20, max_px=36), "bold"),
        fg=ACCENT,
    )
    right_frame.configure(text="Detected Criminals", fg=ACCENT_ALT, bg=CARD_BG)
    left_frame.configure(pady=40, bg=CARD_BG)

    # Inside right_frame, split into two columns: current detections and recent history
    right_frame.grid_columnconfigure(0, weight=1, uniform="rf")
    right_frame.grid_columnconfigure(1, weight=1, uniform="rf")
    right_frame.grid_rowconfigure(0, weight=1)

    detected_list_frame = tk.Frame(right_frame, bg=CARD_BG)
    detected_list_frame.grid(
        row=0,
        column=0,
        sticky="nsew",
        padx=(scaled(10, min_px=6, max_px=20), scaled(6, min_px=4, max_px=14)),
        pady=scaled(10, min_px=6, max_px=18),
    )

    recent_history_frame = tk.LabelFrame(
        right_frame,
        text="Recent Detections",
        bg=CARD_BG,
        fg=ACCENT_ALT,
        font=("Segoe UI", scaled(14, min_px=12, max_px=18), "bold"),
        bd=0,
        labelanchor="n",
        highlightbackground=BORDER_COLOR,
        highlightthickness=1,
    )
    recent_history_frame.grid(
        row=0,
        column=1,
        sticky="nsew",
        padx=(scaled(6, min_px=4, max_px=14), scaled(10, min_px=6, max_px=20)),
        pady=scaled(10, min_px=6, max_px=18),
    )
    update_recent_history_ui()

    (model, names) = train_model()
    print('Training Successful. Detecting Faces')

    # Camera selection controls
    camera_panel = tk.Frame(left_frame, bg=CARD_BG)
    camera_panel.pack(pady=10)

    tk.Label(
        camera_panel,
        text="Select Camera:",
        bg=CARD_BG,
        fg=TEXT_MUTED,
        font=("Segoe UI", scaled(13, min_px=11, max_px=15), "bold"),
    ).pack(side="left", padx=10)

    # Detect available cameras (0..4 by default)
    available_cameras = detect_cameras()

    camera_index_var = tk.IntVar(root)
    camera_index_var.set(available_cameras[0])

    cam_menu = tk.OptionMenu(camera_panel, camera_index_var, *available_cameras)
    cam_menu.configure(
        font=("Segoe UI", scaled(13, min_px=11, max_px=15)),
        bg=ACCENT,
        fg=TEXT_PRIMARY,
        bd=0,
        highlightthickness=0,
        activebackground=ACCENT_ALT,
        activeforeground=TEXT_PRIMARY,
    )
    cam_menu.pack(side="left", padx=10)

    # Button to start surveillance with the selected camera
    start_btn = tk.Button(
        left_frame,
        text="Start Surveillance",
        command=lambda: startVideoSurveillance(model, names),
        font=("Segoe UI", scaled(15, min_px=12, max_px=18), "bold"),
        bg=ACCENT,
        fg=TEXT_PRIMARY,
        pady=10,
        padx=30,
        bd=0,
        highlightthickness=0,
        activebackground="#4F46E5",
        activeforeground=TEXT_PRIMARY,
    )
    start_btn.pack(pady=20)

# Create canvas and vertical scrollbar on pages[0] (Home dashboard)
home_canvas = tk.Canvas(pages[0], bg=APP_BG, highlightthickness=0, bd=0)
home_canvas.pack(fill="both", expand=True, side="left")

home_scrollbar = tk.Scrollbar(
    pages[0],
    command=home_canvas.yview,
    width=scaled(16, min_px=12, max_px=20),
    bg=ACCENT,
    troughcolor=APP_BG,
    activebackground="#4F46E5",
)

home_scrollbar.pack(side="right", fill="y")

home_canvas.configure(yscrollcommand=home_scrollbar.set)

# Create a frame inside the canvas that will hold all home widgets
home_container = tk.Frame(home_canvas, bg=APP_BG)
home_window = home_canvas.create_window((0, 0), window=home_container, anchor="n")
home_container.bind(
    "<Configure>",
    lambda e: home_canvas.configure(scrollregion=home_canvas.bbox("all"))
)


# Ensure canvas scrollregion and window width update when resized
def home_on_configure(event):
    if event.width > 1:
        # center the inner frame horizontally
        home_canvas.coords(home_window, event.width // 2, 0)
        home_canvas.itemconfig(home_window, width=event.width)

    home_canvas.configure(scrollregion=home_canvas.bbox("all"))


home_canvas.bind("<Configure>", home_on_configure)

# Optional: mouse wheel scrolling (works on Windows)
def _on_mousewheel(event):
    # event.delta positive -> scroll up, negative -> scroll down
    home_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

home_canvas.bind_all("<MouseWheel>", _on_mousewheel)

# Put content centered inside home_container
content_frame = tk.Frame(
    home_container,
    bg=CARD_BG,
    bd=0,
    highlightbackground=BORDER_COLOR,
    highlightthickness=1,
)
content_frame.pack(
    padx=scaled(40, min_px=20, max_px=60),
    pady=scaled(40, min_px=20, max_px=60),
)

# Logout button in the top-right corner of the home card
logout_btn = tk.Button(
    content_frame,
    text="Logout",
    command=logout,
    font=("Segoe UI", scaled(11, min_px=10, max_px=14)),
    bg=ACCENT,
    fg=TEXT_PRIMARY,
    padx=scaled(12, min_px=8, max_px=16),
    pady=4,
    bd=0,
    highlightthickness=0,
    activebackground="#4F46E5",
    activeforeground=TEXT_PRIMARY,
    cursor="hand2",
)
logout_btn.pack(anchor="ne", pady=(scaled(4, min_px=2, max_px=8), 0), padx=scaled(6, min_px=4, max_px=10))

title_lbl = tk.Label(
    content_frame,
    text="CRIMINAL  DETECTION  SYSTEM",
    fg=ACCENT_ALT,
    bg=CARD_BG,
    font=("Segoe UI", scaled(30, min_px=20, max_px=40), "bold"),
)
title_lbl.pack(pady=scaled(10, min_px=6, max_px=14))

# Load logo and keep reference, but keep it relatively compact so buttons are visible
try:
    _logo_raw = Image.open(resource_path("logo.png"))
    _logo_side = min(360, int(min(_SW, _SH) * 0.25))
    _logo_raw = _logo_raw.resize((_logo_side, _logo_side), Image.LANCZOS)
    logo_img = ImageTk.PhotoImage(_logo_raw)
except Exception:
    # Fallback to PhotoImage if PIL resize fails for any reason.
    logo_img = tk.PhotoImage(file=resource_path("logo.png"))
    _max_side = int(min(_SW, _SH) * 0.28)
    if logo_img.width() > _max_side or logo_img.height() > _max_side:
        # subsample reduces size by integer factor; make sure it's not zero
        factor = max(1, int(max(logo_img.width() / _max_side, logo_img.height() / _max_side)) + 1)
        logo_img = logo_img.subsample(factor, factor)
logo_lbl = tk.Label(content_frame, image=logo_img, bg=CARD_BG)
logo_lbl.image = logo_img
logo_lbl.pack(pady=scaled(10, min_px=6, max_px=14))

btn_frame = tk.Frame(content_frame, bg=CARD_BG, pady=4)
btn_frame.pack(pady=scaled(8, min_px=6, max_px=14))

# Create buttons in btn_frame
b1 = tk.Button(btn_frame, text="Register Criminal", command=getPage1)
b2 = tk.Button(btn_frame, text="Scan Criminal", command=getPage2)
b3 = tk.Button(btn_frame, text="CCTV Surveillance", command=getPage3)

# Apply a consistent style and pack them; use smaller paddings than before so they fit nicely
for btn in (b1, b2, b3):
    btn.configure(
        font=("Segoe UI", scaled(18, min_px=14, max_px=24), "bold"),
        width=20,
        bg=ACCENT,
        fg=TEXT_PRIMARY,
        pady=scaled(12, min_px=8, max_px=14),
        bd=0,
        highlightthickness=0,
        activebackground="#4F46E5",
        activeforeground=TEXT_PRIMARY,
        cursor="hand2",
    )
    btn.pack(pady=scaled(10, min_px=7, max_px=12))

# Bring home page to front initially (will sit behind auth screens)
root.update_idletasks()
home_canvas.configure(scrollregion=home_canvas.bbox("all"))
root.after(80, lambda: home_canvas.configure(scrollregion=home_canvas.bbox("all")))
pages[0].lift()


# ----------------------- AUTHENTICATION SCREENS -----------------------
auth_frame = None
auth_choice_frame = None
login_frame = None
signup_frame = None
login_username_entry = None
login_password_entry = None
signup_username_entry = None
signup_password_entry = None
signup_confirm_entry = None


def _show_auth_subframe(frame_to_show):
    """Utility to raise the requested subframe inside auth_frame."""
    for f in (auth_choice_frame, login_frame, signup_frame):
        if f is not None:
            f.pack_forget()
    frame_to_show.pack(expand=True, fill="both")


def _show_auth_choice():
    _show_auth_subframe(auth_choice_frame)


def _show_login():
    # Clear previous text
    login_username_entry.delete(0, "end")
    login_password_entry.delete(0, "end")
    _show_auth_subframe(login_frame)


def _show_signup():
    signup_username_entry.delete(0, "end")
    signup_password_entry.delete(0, "end")
    signup_confirm_entry.delete(0, "end")
    _show_auth_subframe(signup_frame)


def _handle_signup():
    username = signup_username_entry.get().strip()
    password = signup_password_entry.get()
    confirm = signup_confirm_entry.get()

    if not username or not password or not confirm:
        messagebox.showerror("Error", "All fields are required.")
        return

    if password != confirm:
        messagebox.showerror("Error", "Passwords do not match.")
        return

    if len(password) < 4:
        messagebox.showerror("Error", "Password must be at least 4 characters long.")
        return

    if username in users:
        messagebox.showerror("Error", "Username already exists. Please choose another.")
        return

    users[username] = password
    save_users()

    messagebox.showinfo("Success", "Your account has been created successfully.")
    _show_login()


def _handle_login():
    username = login_username_entry.get().strip()
    password = login_password_entry.get()

    if not username or not password:
        messagebox.showerror("Error", "Please enter username and password.")
        return

    if users.get(username) == password:
        # Successful login – hide auth screens and show home
        if auth_frame is not None:
            auth_frame.destroy()
        pages[0].lift()
    else:
        messagebox.showerror("Error", "Invalid username or password.")


def build_auth_ui():
    """Create the full‑screen authentication overlay with Login / Create Account."""
    global auth_frame, auth_choice_frame, login_frame, signup_frame
    global login_username_entry, login_password_entry
    global signup_username_entry, signup_password_entry, signup_confirm_entry

    load_users()

    # Full‑window overlay
    auth_frame = tk.Frame(root, bg=APP_BG)
    auth_frame.place(x=0, y=0, relwidth=1, relheight=1)

    # Centered card
    card = tk.Frame(
        auth_frame,
        bg=CARD_BG,
        bd=0,
        highlightbackground=BORDER_COLOR,
        highlightthickness=1,
        padx=scaled(40, min_px=20, max_px=60),
        pady=scaled(40, min_px=20, max_px=60),
    )
    card.place(relx=0.5, rely=0.5, anchor="center")

    title = tk.Label(
        card,
        text="Welcome to Criminal Detection System",
        bg=CARD_BG,
        fg=ACCENT_ALT,
        font=("Segoe UI", scaled(22, min_px=16, max_px=28), "bold"),
    )
    title.pack(pady=(0, scaled(20, min_px=12, max_px=24)))

    subtitle = tk.Label(
        card,
        text="Please sign in to continue.",
        bg=CARD_BG,
        fg=TEXT_MUTED,
        font=("Segoe UI", scaled(12, min_px=10, max_px=14)),
    )
    subtitle.pack(pady=(0, scaled(20, min_px=10, max_px=18)))

    # Subframes inside the card
    auth_choice_frame = tk.Frame(card, bg=CARD_BG)
    login_frame = tk.Frame(card, bg=CARD_BG)
    signup_frame = tk.Frame(card, bg=CARD_BG)

    # -------- Choice Screen --------
    choice_label = tk.Label(
        auth_choice_frame,
        text="Choose an option",
        bg=CARD_BG,
        fg=TEXT_PRIMARY,
        font=("Segoe UI", scaled(16, min_px=12, max_px=20), "bold"),
    )
    choice_label.pack(pady=scaled(10, min_px=8, max_px=16))

    choice_btn_frame = tk.Frame(auth_choice_frame, bg=CARD_BG)
    choice_btn_frame.pack(pady=scaled(10, min_px=8, max_px=16))

    login_btn = tk.Button(
        choice_btn_frame,
        text="Login",
        command=_show_login,
        font=("Segoe UI", scaled(14, min_px=12, max_px=18), "bold"),
        bg=ACCENT,
        fg=TEXT_PRIMARY,
        padx=scaled(20, min_px=14, max_px=26),
        pady=scaled(10, min_px=8, max_px=14),
        bd=0,
        highlightthickness=0,
        activebackground="#4F46E5",
        activeforeground=TEXT_PRIMARY,
        cursor="hand2",
    )
    login_btn.grid(row=0, column=0, padx=scaled(10, min_px=8, max_px=16))

    create_btn = tk.Button(
        choice_btn_frame,
        text="Create Account",
        command=_show_signup,
        font=("Segoe UI", scaled(14, min_px=12, max_px=18), "bold"),
        bg=ACCENT_ALT,
        fg=APP_BG,
        padx=scaled(20, min_px=14, max_px=26),
        pady=scaled(10, min_px=8, max_px=14),
        bd=0,
        highlightthickness=0,
        activebackground="#06B6D4",
        activeforeground=APP_BG,
        cursor="hand2",
    )
    create_btn.grid(row=0, column=1, padx=scaled(10, min_px=8, max_px=16))

    # -------- Login Screen --------
    login_title = tk.Label(
        login_frame,
        text="Login",
        bg=CARD_BG,
        fg=ACCENT_ALT,
        font=("Segoe UI", scaled(18, min_px=14, max_px=22), "bold"),
    )
    login_title.pack(pady=(0, scaled(16, min_px=10, max_px=20)))

    login_form = tk.Frame(login_frame, bg=CARD_BG)
    login_form.pack()

    tk.Label(
        login_form,
        text="Username",
        bg=CARD_BG,
        fg=TEXT_PRIMARY,
        font=("Segoe UI", scaled(12, min_px=10, max_px=14)),
    ).grid(row=0, column=0, sticky="w", pady=4)
    login_username_entry = tk.Entry(
        login_form,
        bg=PANEL_BG,
        fg=TEXT_PRIMARY,
        insertbackground=TEXT_PRIMARY,
        relief="flat",
        font=("Segoe UI", scaled(12, min_px=10, max_px=14)),
        width=28,
    )
    login_username_entry.grid(row=1, column=0, pady=(0, 10), sticky="ew")

    tk.Label(
        login_form,
        text="Password",
        bg=CARD_BG,
        fg=TEXT_PRIMARY,
        font=("Segoe UI", scaled(12, min_px=10, max_px=14)),
    ).grid(row=2, column=0, sticky="w", pady=4)
    login_password_entry = tk.Entry(
        login_form,
        bg=PANEL_BG,
        fg=TEXT_PRIMARY,
        insertbackground=TEXT_PRIMARY,
        relief="flat",
        font=("Segoe UI", scaled(12, min_px=10, max_px=14)),
        show="*",
        width=28,
    )
    login_password_entry.grid(row=3, column=0, pady=(0, 10), sticky="ew")

    login_btn_row = tk.Frame(login_frame, bg=CARD_BG)
    login_btn_row.pack(pady=scaled(10, min_px=8, max_px=16))

    back_to_choice1 = tk.Button(
        login_btn_row,
        text="Back",
        command=_show_auth_choice,
        font=("Segoe UI", scaled(12, min_px=10, max_px=14)),
        bg=PANEL_BG,
        fg=TEXT_MUTED,
        padx=scaled(14, min_px=10, max_px=20),
        pady=6,
        bd=0,
        highlightthickness=0,
        activebackground=BORDER_COLOR,
        activeforeground=TEXT_PRIMARY,
        cursor="hand2",
    )
    back_to_choice1.grid(row=0, column=0, padx=scaled(8, min_px=6, max_px=12))

    do_login_btn = tk.Button(
        login_btn_row,
        text="Login",
        command=_handle_login,
        font=("Segoe UI", scaled(14, min_px=12, max_px=18), "bold"),
        bg=ACCENT,
        fg=TEXT_PRIMARY,
        padx=scaled(20, min_px=14, max_px=26),
        pady=scaled(8, min_px=6, max_px=12),
        bd=0,
        highlightthickness=0,
        activebackground="#4F46E5",
        activeforeground=TEXT_PRIMARY,
        cursor="hand2",
    )
    do_login_btn.grid(row=0, column=1, padx=scaled(8, min_px=6, max_px=12))

    # -------- Signup Screen --------
    signup_title = tk.Label(
        signup_frame,
        text="Create Account",
        bg=CARD_BG,
        fg=ACCENT_ALT,
        font=("Segoe UI", scaled(18, min_px=14, max_px=22), "bold"),
    )
    signup_title.pack(pady=(0, scaled(16, min_px=10, max_px=20)))

    signup_form = tk.Frame(signup_frame, bg=CARD_BG)
    signup_form.pack()

    tk.Label(
        signup_form,
        text="Username",
        bg=CARD_BG,
        fg=TEXT_PRIMARY,
        font=("Segoe UI", scaled(12, min_px=10, max_px=14)),
    ).grid(row=0, column=0, sticky="w", pady=4)
    signup_username_entry = tk.Entry(
        signup_form,
        bg=PANEL_BG,
        fg=TEXT_PRIMARY,
        insertbackground=TEXT_PRIMARY,
        relief="flat",
        font=("Segoe UI", scaled(12, min_px=10, max_px=14)),
        width=28,
    )
    signup_username_entry.grid(row=1, column=0, pady=(0, 10), sticky="ew")

    tk.Label(
        signup_form,
        text="Password",
        bg=CARD_BG,
        fg=TEXT_PRIMARY,
        font=("Segoe UI", scaled(12, min_px=10, max_px=14)),
    ).grid(row=2, column=0, sticky="w", pady=4)
    signup_password_entry = tk.Entry(
        signup_form,
        bg=PANEL_BG,
        fg=TEXT_PRIMARY,
        insertbackground=TEXT_PRIMARY,
        relief="flat",
        font=("Segoe UI", scaled(12, min_px=10, max_px=14)),
        show="*",
        width=28,
    )
    signup_password_entry.grid(row=3, column=0, pady=(0, 10), sticky="ew")

    tk.Label(
        signup_form,
        text="Confirm Password",
        bg=CARD_BG,
        fg=TEXT_PRIMARY,
        font=("Segoe UI", scaled(12, min_px=10, max_px=14)),
    ).grid(row=4, column=0, sticky="w", pady=4)
    signup_confirm_entry = tk.Entry(
        signup_form,
        bg=PANEL_BG,
        fg=TEXT_PRIMARY,
        insertbackground=TEXT_PRIMARY,
        relief="flat",
        font=("Segoe UI", scaled(12, min_px=10, max_px=14)),
        show="*",
        width=28,
    )
    signup_confirm_entry.grid(row=5, column=0, pady=(0, 10), sticky="ew")

    signup_btn_row = tk.Frame(signup_frame, bg=CARD_BG)
    signup_btn_row.pack(pady=scaled(10, min_px=8, max_px=16))

    back_to_choice2 = tk.Button(
        signup_btn_row,
        text="Back",
        command=_show_auth_choice,
        font=("Segoe UI", scaled(12, min_px=10, max_px=14)),
        bg=PANEL_BG,
        fg=TEXT_MUTED,
        padx=scaled(14, min_px=10, max_px=20),
        pady=6,
        bd=0,
        highlightthickness=0,
        activebackground=BORDER_COLOR,
        activeforeground=TEXT_PRIMARY,
        cursor="hand2",
    )
    back_to_choice2.grid(row=0, column=0, padx=scaled(8, min_px=6, max_px=12))

    do_signup_btn = tk.Button(
        signup_btn_row,
        text="Create Account",
        command=_handle_signup,
        font=("Segoe UI", scaled(14, min_px=12, max_px=18), "bold"),
        bg=ACCENT_ALT,
        fg=APP_BG,
        padx=scaled(20, min_px=14, max_px=26),
        pady=scaled(8, min_px=6, max_px=12),
        bd=0,
        highlightthickness=0,
        activebackground="#06B6D4",
        activeforeground=APP_BG,
        cursor="hand2",
    )
    do_signup_btn.grid(row=0, column=1, padx=scaled(8, min_px=6, max_px=12))

    # Default view: choice screen
    _show_auth_choice()


# Build authentication UI overlay (shown on startup)
build_auth_ui()

# Start mainloop
root.mainloop()
