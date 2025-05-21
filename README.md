# 🧑‍💻 Syntax Analysis Tool

A static analysis tool for Python code, featuring a Tkinter-based GUI. This tool analyzes Python scripts for common style, naming, and logical issues, providing feedback similar to popular linters.

---

## ✨ Features

- **Graphical User Interface:**  
  Easily input or upload Python code for analysis.

- **PEP 8 & Common Issue Detection:**  
  - Naming convention checks for variables, functions, classes, and constants  
  - Detection of unused variables and imports  
  - Checks for undefined variables  
  - Warnings for redefining built-ins  
  - Detection of mutable default arguments  
  - Checks for inconsistent return statements  
  - Division by zero detection  
  - Infinite loop and deeply nested loop warnings  
  - Try/except anti-patterns (bare except, empty except, broad exception catching)  
  - File resource leak detection (using `open` outside a `with` statement)  
  - And more!

- **Result Highlighting:**  
  Highlights problematic lines in the code input area.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.x

### Installation

Clone the repository:

```bash
git clone https://github.com/your-username/syntax-analysis-tool.git
cd syntax-analysis-tool
```

### Usage

Run the GUI:

```bash
python AnalyzerGUI.py
```

- **Enter or upload** your Python code.
- Click **ANALYZE** to see detected issues.
- Problematic lines will be highlighted.

---

## 🗂️ Project Structure

```
.
├── AnalyzerGUI.py      # Tkinter GUI for code input, file upload, and result display
├── SyntaxAnalyzer.py   # Core static analysis logic using Python's AST
```

---

## 📝 Example Checks

- Variable/function/class naming conventions
- Unused variables/imports
- Undefined variables
- Mutable default arguments
- Inconsistent return statements
- Division by zero
- Infinite loops
- Bare/empty except blocks
- File resource leaks

## ENJOY (WILL PERIODICALLY UPDATE)

---

## 📄 License

[MIT License](LICENSE) (or specify your license here)
