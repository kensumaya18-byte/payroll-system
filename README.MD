# Employee Payroll Sorter

A command-line payroll system for Philippine employees, written in Python. It stores employee records in a CSV file, computes government contributions and withholding tax, and generates payslips (on screen, as PDF, or by email). It also includes sorting, searching, and analytics tools.

It was built as a learning project, so it also demonstrates classic data structures and algorithms (a max-heap, merge sort, and linear search) inside a practical app.

---

## Table of Contents

1. [Features](#features)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Running the Program](#running-the-program)
5. [Menu Guide](#menu-guide)
6. [How the Payroll Is Computed](#how-the-payroll-is-computed)
7. [Data Structures and Algorithms](#data-structures-and-algorithms)
8. [Files and Folders](#files-and-folders)
9. [Email Setup (Optional)](#email-setup-optional)
10. [Customizing](#customizing)
11. [Known Limitations](#known-limitations)
12. [Troubleshooting](#troubleshooting)

---

## Features

- Add, search, update, and delete employees
- Automatic computation of SSS, PhilHealth, Pag-IBIG, overtime, withholding tax, net pay, and employer cost
- Department-based employee IDs and markers (e.g. `IT-3f9a1c2b`, `[IT]`)
- Duplicate-name detection when adding employees
- Sorting by name, department, or salary
- Top 5 highest-paid employees
- Linear search by name, ID, or department
- Advanced analytics dashboard (company totals, averages, department breakdown, tax bracket distribution)
- Styled PDF payslips (single or batch for all employees)
- Email payslips with the PDF attached
- Excel export with multiple sheets
- Activity history log
- Works even if optional libraries are missing (graceful fallbacks)

---

## Requirements

- Python 3.8 or newer (the code uses `typing.Optional` and f-strings)

Every library is **optional**. The program runs on the standard library alone, but features are reduced without them:

| Package | Used for | If missing |
|---|---|---|
| `pandas` | Analytics dashboard, Excel export | Simplified analytics; Excel export disabled |
| `openpyxl` | Writing `.xlsx` files (used by pandas) | Excel export fails |
| `tabulate` | Pretty tables (first choice) | Falls back to `rich`, then plain text |
| `rich` | Colored tables (second choice) | Falls back to plain text |
| `fpdf2` | PDF payslips | PDF generation is skipped |
| `python-dotenv` | Loading SMTP credentials from `.env` | Email needs environment variables set manually |

---

## Installation

```bash
# 1. Put the script in a folder, e.g. payroll/
# 2. (Recommended) create a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Install the optional packages
pip install pandas openpyxl tabulate rich fpdf2 python-dotenv
```

---

## Running the Program

```bash
python payroll.py
```

(Use whatever your file is named.)

On the first run, if `employees2.csv` does not exist, the program creates it and seeds **20 default employees** so you can try everything right away.

---

## Menu Guide

| # | Option | What it does |
|---|---|---|
| 1 | Add Employee | Prompts for name, department, salary, overtime hours, other deductions, and voluntary SSS. Warns if the name already exists. |
| 2 | View Payroll (with analytics) | Shows all employees in a table, the total employer cost, then the full analytics dashboard. |
| 3 | Sort Employees | Sort by Name (A-Z), Department (A-Z), or Salary (highest first) using merge sort. |
| 4 | Top 5 Highest-Paid | Uses a max-heap to pull the 5 highest salaries. |
| 5 | Search Employee | Exact match on ID or full name. Shows the payslip and a "where your salary went" breakdown. |
| 6 | Delete Employee | Deletes by ID after confirmation. |
| 7 | Update Salary | Changes one employee's basic salary and recomputes everything. |
| 8 | Restore Default Employees | **Erases all employees** and re-seeds the 20 defaults. |
| 9 | Linear Search | Partial (substring) match on name, ID, or department. |
| 10 | View History Log | Prints everything in `history2.log`. |
| 11 | Clear History Log | Deletes the log after confirmation. |
| 12 | Show Department Markers | Lists department prefixes and markers. |
| 13 | Generate PDF Payslip | Creates a PDF for one employee by ID. |
| 14 | Email Payslip | Generates a PDF and emails it to an address you enter. |
| 15 | Export Excel Report | Writes a timestamped `.xlsx` file into `exports/`. |
| 16 | Batch Generate All Payslips | Creates a PDF for every employee. |
| 17 | Exit | Quits the program. |

### Search: option 5 vs option 9

- **Option 5** needs an *exact* ID or full name and shows the full payslip.
- **Option 9** matches *partial text* (typing `gian` finds both Gian Gonzales and Gian Mendoza) and shows results in a table.

---

## How the Payroll Is Computed

All amounts are **monthly**. The salary you enter is treated as the monthly basic salary. The constants are defined at the top of the script so they are easy to update.

### 1. Overtime

```
hourly_rate  = salary / 160
overtime_pay = overtime_hours x hourly_rate x 1.25
gross        = salary + overtime_pay
```

### 2. Mandatory contributions (employee share)

| Contribution | Rule |
|---|---|
| **SSS** | 5% of the Monthly Salary Credit (MSC). MSC is the salary clamped between P5,000 and P35,000. |
| **PhilHealth** | 2.5% of salary, with salary clamped between P10,000 and P100,000. |
| **Pag-IBIG** | 2% of salary, with salary capped at P10,000 (so the maximum is P200). |

### 3. Employer contributions (cost to the company)

| Contribution | Rule |
|---|---|
| **SSS** | 10% of MSC |
| **SSS EC** | P10 if MSC is P14,500 or below, otherwise P30 |
| **PhilHealth** | 2.5% (same clamp as the employee share) |
| **Pag-IBIG** | 2% (same P10,000 cap) |

```
employer_cost = gross + employer SSS + EC + employer PhilHealth + employer Pag-IBIG
```

### 4. Withholding tax

Mandatory contributions are tax-exempt, so:

```
taxable_income (monthly) = gross - SSS - PhilHealth - Pag-IBIG
annual_taxable           = taxable_income x 12
```

The annual tax uses the TRAIN Law brackets:

| Annual taxable income | Tax |
|---|---|
| Up to P250,000 | Exempt |
| P250,000 - P400,000 | 15% of the excess over P250,000 |
| P400,000 - P800,000 | P22,500 + 20% of the excess over P400,000 |
| P800,000 - P2,000,000 | P102,500 + 25% of the excess over P800,000 |
| P2,000,000 - P8,000,000 | P402,500 + 30% of the excess over P2,000,000 |
| Over P8,000,000 | P2,202,500 + 35% of the excess over P8,000,000 |

`monthly_tax = annual_tax / 12`

### 5. Net pay

```
net = gross - SSS - PhilHealth - Pag-IBIG - voluntary_SSS - tax - other_deductions
```

> **Note:** Voluntary SSS and "other deductions" are subtracted from take-home pay but do **not** reduce taxable income.

> **Important:** Contribution rates, salary ceilings, and tax brackets are set by the government and change over time. Verify the constants against current SSS, PhilHealth, Pag-IBIG, and BIR circulars before relying on the output for real payroll.

---

## Data Structures and Algorithms

| Feature | Implementation |
|---|---|
| Top 5 highest-paid | `MaxHeap` class (build heap, sift up, heapify, extract max), keyed on salary |
| Sorting (option 3) | Recursive `merge_sort`, case-insensitive for text, supports ascending/descending |
| Linear search (option 9) | Simple loop with substring matching |
| Storage | Flat CSV file read and written with the `csv` module |

---

## Files and Folders

Created next to the script automatically:

```
payroll/
├── payroll.py            # the program
├── employees2.csv        # employee database
├── history2.log          # activity log
├── .env                  # SMTP credentials (you create this, optional)
├── payslips/             # generated PDF payslips
│   └── payslip_<ID>.pdf
└── exports/              # Excel reports
    └── payroll_export_YYYYMMDD_HHMMSS.xlsx
```

### Employee IDs

IDs follow `<DEPT PREFIX>-<8 random hex characters>`:

| Department | Prefix | Marker |
|---|---|---|
| IT | `IT` | `[IT]` |
| HR | `HR` | `[HR]` |
| Finance | `FIN` | `[FIN]` |
| Marketing | `MKT` | `[MKT]` |
| Sales | `SLS` | `[SLS]` |
| Operations | `OPS` | `[OPS]` |
| Anything else | `GEN` | `[GEN]` |

ID lookups are case-insensitive.

### CSV columns

`id, name, department, salary, overtime, overtime_pay, sss, philhealth, pagibig, voluntary_sss, deductions, sss_employer, ec_employer, philhealth_employer, pagibig_employer, employer_cost, gross, taxable_income, tax_withheld, net`

If you edit the CSV by hand and a required column is missing, the program prints a warning and loads nothing. Use option 8 or delete the file to re-seed. Computed columns (like `net`) are stored values, so editing salary directly in the CSV will **not** recalculate them. Use option 7 instead.

### History log

Every important action (add, delete, search, export, email, and so on) is appended to `history2.log` with a timestamp:

```
[2026-10-15 14:32:10] ADD - Juan Dela Cruz (ID IT-3f9a1c2b, dept IT)
```

---

## Email Setup (Optional)

Option 14 sends the payslip as a PDF attachment over SMTP. Create a `.env` file next to the script:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
SMTP_FROM_NAME=Payroll Department
```

**Gmail users:** you need a Google *App Password* (requires 2-Step Verification). Your normal password will not work.

**Security tips:**
- Never commit `.env` to Git. Add it to `.gitignore`.
- Payslips and the CSV contain personal and salary data. Keep them private.

---

## Customizing

| What | Where |
|---|---|
| Company name and address on PDFs | `DEFAULT_COMPANY_NAME`, `DEFAULT_COMPANY_ADDRESS` |
| PDF colors | `NAVY`, `LIGHT`, `GRAY`, `LINE` inside `generate_payslip_pdf` |
| Contribution rates and ceilings | Constants near the top (`SSS_*`, `PHILHEALTH_*`, `PAGIBIG_*`) |
| Tax brackets | `compute_monthly_tax` and `_get_tax_bracket` (update both) |
| Overtime formula | `Employee.HOURLY_DIVISOR` (160) and `Employee.OVERTIME_MULTIPLIER` (1.25) |
| Departments and prefixes | `DEPARTMENT_MARKERS` |
| Default sample employees | `DEFAULT_EMPLOYEES` |
| Add a company logo to PDFs | Uncomment/add `pdf.image("logo.png", x=10, y=6, h=20)` in `generate_payslip_pdf` |

To add a new menu option: write the function, add it to the `actions` dictionary in `main()`, add a line in `print_menu()`, and update the exit number.

---

## Known Limitations

- **Single user, no login.** Anyone who can run the script can view or change all data.
- **CSV storage.** Fine for dozens or hundreds of employees, not for large-scale use. Opening the CSV in Excel while the program runs can cause "file locked" errors.
- **Monthly only.** There is no semi-monthly payroll, no 13th-month pay, no leave, and no holiday or night-shift differentials.
- **Simplified overtime.** One flat rate (125%) is applied to all overtime.
- **Simplified tax.** Tax is computed by annualizing one month's taxable income, with no year-to-date adjustments.
- **Peso sign.** The code uses `P` instead of the peso symbol because the built-in PDF font (Helvetica) cannot print the peso symbol.
- **Duplicate names** are allowed after confirmation. Employees are always uniquely identified by ID.
- **Not certified payroll software.** Use it for learning and prototyping, and verify results before using it for real payroll.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `fpdf2 not installed - skipping PDF generation` | `pip install fpdf2` |
| `pandas not installed - cannot export Excel` | `pip install pandas openpyxl` |
| Excel export fails with an openpyxl error | `pip install openpyxl` |
| `SMTP_USER or SMTP_PASS not set in .env` | Create the `.env` file as shown above |
| Email fails to authenticate on Gmail | Use an App Password, not your regular password |
| `Could not write ... file locked` | Close the CSV or Excel file, or pause OneDrive sync |
| `CSV is missing columns` warning | Delete `employees2.csv` or use option 8 to re-seed |
| Tables look plain | Install `tabulate` or `rich` |
| Everything got erased | Option 8 deletes all employees by design. Back up `employees2.csv` first. |

---

## License

No license just school project