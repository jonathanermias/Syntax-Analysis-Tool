# Jonathan Ermias
import tkinter as tk
from tkinter import filedialog, messagebox
from SyntaxAnalyzer import analyze_code
import re

def analyze_input_code():
    """
    retrieve the code from the input widget, analyze it, display the results, and highlight any issues.
    """
    input_code = code_input.get("1.0", tk.END).rstrip()
    if not input_code.strip():
        messagebox.showerror("ERROR", "Please enter or upload code for analysis.")
        return

    results = analyze_code(input_code)
    display_results(results)
    highlight_issues(results)

def upload_file():
    """
    open a file dialog to upload a python file for analysis.
    """
    file_path = filedialog.askopenfilename(
        filetypes=[("python files", "*.py"), ("all files", "*.*")]
    )
    if not file_path:
        return

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            code = file.read()
        code_input.delete("1.0", tk.END)
        code_input.insert(tk.END, code)
        update_line_numbers()
    except Exception as e:
        messagebox.showerror("error", f"failed to open file: {e}")

def display_results(results):
    """
    display the analysis results in the gui's output text box.
    """
    result_output.config(state=tk.NORMAL)
    result_output.delete("1.0", tk.END)

    if results:
        result_output.insert(tk.END, "\n".join(results))
    else:
        result_output.insert(tk.END, "no issues found!")

    result_output.config(state=tk.DISABLED)

def highlight_issues(results):
    """
    highlight the lines in the code input where issues were found.
    """
    code_input.tag_remove('highlight', '1.0', tk.END)
    for issue in results:
        match = re.search(r'line (\d+)', issue)
        if match:
            line_num = int(match.group(1))
            start = f"{line_num}.0"
            end = f"{line_num}.0 lineend"
            code_input.tag_add('highlight', start, end)
    code_input.tag_configure('highlight', background='#FDFF78')

def update_line_numbers(event=None):
    """
    update the line numbers in the line_numbers canvas widget.
    """
    line_numbers_canvas.delete('all')
    i = code_input.index('@0,0')
    while True:
        dline = code_input.dlineinfo(i)
        if dline is None:
            break
        y = dline[1]
        line_number = str(i).split('.')[0]
        color = '#D3D3D3' if int(line_number) % 2 == 0 else '#FFFFFF'
        # draw the background rectangle
        line_numbers_canvas.create_rectangle(
            0, y, line_numbers_canvas.winfo_width(), y + dline[3],
            fill=color, outline=''
        )
        # draw the line number text
        line_numbers_canvas.create_text(
            2, y, anchor='nw', text=line_number, fill=fg_color,
            font=('Consolas', 12)
        )
        i = code_input.index(f"{i}+1line")

def on_scroll(*args):
    """
    scroll the code_input and line_numbers widgets together.
    """
    code_input.yview(*args)
    line_numbers_canvas.yview(*args)
    update_line_numbers()

def on_change(event):
    """
    handle scroll events to keep line numbers and code input synchronized.
    """
    code_input.yview_scroll(int(-1*(event.delta/120)), "units")
    line_numbers_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    update_line_numbers()

# create the main application window
root = tk.Tk()
root.title("static analysis tool")
root.geometry("900x700")
bg_color = '#808080'  # grey background
root.configure(bg=bg_color)

# define color variables
fg_color = '#000000'          # black text color
button_color = '#FDFF78'      # yellow button color
button_text_color = '#000000' # black text on buttons
text_box_color = '#FFFFFF'    # white background for text box
text_box_fg_color = '#000000' # black text color

# input frame for code entry and buttons
input_frame = tk.Frame(root, bg=bg_color)
input_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

# label for code input
input_label = tk.Label(
    input_frame,
    text="Enter or Upload Python Code:",
    bg=bg_color,
    fg=fg_color,
    font=('Helvetica', 12, 'bold')
)
input_label.pack(anchor='w', padx=5, pady=5)

# frame for line numbers and code input
code_frame = tk.Frame(input_frame)
code_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

# scrollbar for code input and line numbers
scrollbar = tk.Scrollbar(code_frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# canvas widget for line numbers
line_numbers_canvas = tk.Canvas(
    code_frame,
    width=40,
    bg=text_box_color,
    highlightthickness=0
)
line_numbers_canvas.pack(side=tk.LEFT, fill=tk.Y)

# text box for direct code input
code_input = tk.Text(
    code_frame,
    height=15,
    wrap='none',
    bg=text_box_color,
    fg=text_box_fg_color,
    insertbackground=text_box_fg_color,
    font=('Consolas', 12),
    undo=True,
    yscrollcommand=scrollbar.set
)
code_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.config(command=on_scroll)

# bind events for updating line numbers and scrolling
code_input.bind('<KeyRelease>', update_line_numbers)
code_input.bind('<MouseWheel>', on_change)  # windows and macos
code_input.bind('<Button-4>', on_change)    # linux scroll up
code_input.bind('<Button-5>', on_change)    # linux scroll down
code_input.bind('<FocusIn>', update_line_numbers)
code_input.bind('<Configure>', update_line_numbers)
line_numbers_canvas.bind('<MouseWheel>', on_change)

# buttons for file upload and analysis
button_frame = tk.Frame(input_frame, bg=bg_color)
button_frame.pack(fill=tk.X, padx=5, pady=5)

upload_button = tk.Button(
    button_frame,
    text="UPLOAD",
    command=upload_file,
    bg=button_color,
    fg=button_text_color,
    font=('Helvetica', 10, 'bold')
)
upload_button.pack(side=tk.LEFT, padx=5)

analyze_button = tk.Button(
    button_frame,
    text="ANALYZE",
    command=analyze_input_code,
    bg=button_color,
    fg=button_text_color,
    font=('Helvetica', 10, 'bold')
)
analyze_button.pack(side=tk.RIGHT, padx=5)

# output frame for displaying results
output_frame = tk.Frame(root, bg=bg_color)
output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

# label for analysis results
output_label = tk.Label(
    output_frame,
    text="Result of Analysis:",
    bg=bg_color,
    fg=fg_color,
    font=('Helvetica', 12, 'bold')
)
output_label.pack(anchor='w', padx=5, pady=5)

# text widget for displaying analysis results
result_output = tk.Text(
    output_frame,
    height=15,
    wrap='word',
    bg=text_box_color,
    fg=text_box_fg_color,
    state=tk.DISABLED,
    font=('Consolas', 12),
    highlightthickness=1,
    highlightbackground='black',
    relief='solid',
    borderwidth=1
)
result_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

# start the main event loop
root.mainloop()
