# Employee Payroll Sorter

A command-line payroll system for Philippine employees. It keeps employee records in a CSV file, computes government contributions and withholding tax for each employee, and produces payslips, reports, and analytics. It also uses a max-heap, merge sort, and linear search on the employee data.

This README explains how the program works and shows the output of every menu option. All sample output below uses the 20 default employees the program creates on its first run.

> **About the sample output:** Employee IDs are random (for example `IT-a1b2c3d4`), so yours will differ. Every peso amount is computed from the program's own formulas, so the numbers match what you will see.

---

## 1. How the System Is Organized

The program is one file, built in layers. Each layer only uses the ones above it.

| Layer | What it contains | Purpose |
|---|---|---|
| **Constants** | `SSS_*`, `PHILHEALTH_*`, `PAGIBIG_*`, `DEPARTMENT_MARKERS` | All rates, ceilings, and department codes in one place |
| **Computation functions** | `compute_sss_employee`, `compute_philhealth_employee`, `compute_pagibig_employee`, the employer versions, `compute_taxable_income`, `compute_monthly_tax` | Pure math, no printing or file access |
| **`Employee` class** | `__init__`, `to_dict`, `save_to_csv` | Takes basic inputs and calculates every payroll figure automatically |
| **Data layer** | `load_employees`, `rewrite_csv`, `seed_default_employees`, `load_employees_df` | Reads and writes `employees2.csv` |
| **Algorithms** | `MaxHeap`, `merge_sort`, `linear_search` | Top 5, sorting, and searching |
| **Output functions** | `print_table`, `print_payslip`, `_print_deduction_summary`, analytics | Everything you see on screen |
| **File outputs** | `generate_payslip_pdf`, `export_excel`, `send_payslip_email`, `log_action` | PDFs, Excel, email, history log |
| **Menu** | `print_menu`, `main` | Shows the menu and calls the right function |

### How the menu works

`main()` keeps a dictionary that maps each menu number to a function:

```python
actions = {"1": add_employee, "2": view_payroll, "3": sort_employees, ...}
```

When you type a number, the program looks it up in the dictionary and runs that function. Typing `17` exits. Anything else prints "Invalid choice". To add a new feature, you write a function and add one line to this dictionary and one line to `print_menu()`.

### What happens when an employee is created

When you create `Employee(name, department, salary, overtime, deductions, voluntary_sss)`, the constructor does all the math in this order:

1. Generates an ID like `IT-3f9a1c2b` (department prefix + 8 random hex characters)
2. Computes the employee's SSS, PhilHealth, and Pag-IBIG
3. Computes the employer's SSS, EC, PhilHealth, and Pag-IBIG
4. Computes overtime pay, then gross pay
5. Computes taxable income, then withholding tax
6. Computes net pay and total employer cost

`to_dict()` turns the object into a dictionary with 20 fields, and that dictionary is what gets saved to the CSV and passed to every print function.

---

## 2. How the Payroll Is Computed

All amounts are monthly. The salary you enter is treated as the monthly basic salary.

**Overtime and gross pay**

```
overtime_pay = overtime_hours x (salary / 160) x 1.25
gross        = salary + overtime_pay
```

**Employee contributions (deducted from the employee)**

| Item | Rule |
|---|---|
| SSS | 5% of MSC (salary clamped between P5,000 and P35,000) |
| PhilHealth | 2.5% of salary (salary clamped between P10,000 and P100,000) |
| Pag-IBIG | 2% of salary, salary capped at P10,000 (max P200) |

**Employer contributions (paid by the company)**

| Item | Rule |
|---|---|
| SSS | 10% of MSC |
| SSS EC | P10 if MSC is P14,500 or below, otherwise P30 |
| PhilHealth | 2.5%, same clamp |
| Pag-IBIG | 2%, same cap |

**Tax (TRAIN Law, annualized)**

```
taxable_income = gross - SSS - PhilHealth - Pag-IBIG      (monthly)
annual_taxable = taxable_income x 12
monthly_tax    = annual_tax / 12
```

| Annual taxable income | Annual tax |
|---|---|
| up to P250,000 | 0 |
| P250,000 to P400,000 | 15% of the excess over P250,000 |
| P400,000 to P800,000 | P22,500 + 20% of the excess over P400,000 |
| P800,000 to P2,000,000 | P102,500 + 25% of the excess over P800,000 |
| P2,000,000 to P8,000,000 | P402,500 + 30% of the excess over P2,000,000 |
| over P8,000,000 | P2,202,500 + 35% of the excess over P8,000,000 |

**Net pay and employer cost**

```
net           = gross - SSS - PhilHealth - Pag-IBIG - voluntary_SSS - tax - other_deductions
employer_cost = gross + employer SSS + EC + employer PhilHealth + employer Pag-IBIG
```

Voluntary SSS and other deductions reduce take-home pay but do **not** reduce taxable income. Only the three mandatory contributions do.

### Worked example: Kenshin Abesamis (IT, P40,000, 10 overtime hours, P3,000 other deductions)

| Step | Computation | Result |
|---|---|---|
| Overtime pay | 10 x (40,000 / 160) x 1.25 | P3,125.00 |
| Gross | 40,000 + 3,125 | P43,125.00 |
| SSS | 5% x 35,000 (MSC capped) | P1,750.00 |
| PhilHealth | 2.5% x 40,000 | P1,000.00 |
| Pag-IBIG | 2% x 10,000 (capped) | P200.00 |
| Taxable income | 43,125 - 1,750 - 1,000 - 200 | P40,175.00 |
| Annual taxable | 40,175 x 12 | P482,100.00 |
| Annual tax | 22,500 + 20% x (482,100 - 400,000) | P38,920.00 |
| Monthly tax | 38,920 / 12 | P3,243.33 |
| Net pay | 43,125 - 1,750 - 1,000 - 200 - 3,243.33 - 3,000 | **P33,931.67** |

---

## 3. Menu Options and Their Results

### Option 1: Add Employee

**What it does:** Asks for the employee's details, checks for a duplicate name, builds an `Employee` object, saves it to the CSV, and prints the new payslip.

```
---------- ADD EMPLOYEE ----------
Employee Name: Juan Dela Cruz
Department: IT
Basic Salary: P30000
Overtime Hours: 5
Other Deductions (non-statutory): P2000
Voluntary SSS in excess of mandatory (P0 if none): P0

Employee added successfully! [IT]
```

The payslip is then printed (see Option 5 for the layout).

**Duplicate name handling:** If the name already exists, the program lists the matching records and asks if you want to continue. If you say yes, it makes you pick a different department from a numbered list so the two records can be told apart.

```
[!] WARNING: Duplicate name detected!
     - ID: HR-7c21e0aa       Dept: [HR] HR           Net: P23,557.35

Do you want to duplicate the name? (y/n):
```

The new ID is checked against all existing IDs so two employees never share one.

---

### Option 2: View Payroll (with analytics)

**What it does:** Prints a table of all employees, the totals, and then the full analytics dashboard. Output comes from `print_table()` followed by `advanced_analytics()`.

**Part A: Employee table** (shown here in plain-text form; with `tabulate` or `rich` installed it is drawn as a boxed or colored table)

```
--- Payroll Report (20) ---
ID              [IT]  Name              Department     Gross        Tax       Net      Employer Cost
IT-a1b2c3d4     [IT]  Yvonne Escobido   IT        P31,171.88  P1,183.28  P25,538.60     P35,151.88
HR-b3c4d5e6     [HR]  Rizzel Disquitado HR        P29,750.00    P992.50  P24,657.50     P33,480.00
FIN-c5d6e7f8    [FIN] Bryan Carias      Finance   P36,640.62  P1,971.46  P29,344.17     P41,245.62
...

Total Employees: 20
Total Employer Cost (this month): P772,396.09
```

The small marker column (`[IT]`, `[HR]`, `[FIN]`) comes from `get_department_marker()`.

**Part B: Analytics dashboard** (this is the pandas version)

```
[1] COMPANY-WIDE TOTALS (this month)
    Employees                   :                   20
    Total Basic Salary          :          P654,500.00
    Total Overtime Pay          :           P33,683.59
    Total GROSS PAY             :          P688,183.59
    Total Mandatory (EE)        :           P51,987.50
    Total Tax Withheld          :           P34,483.98
    Total NET PAY               :          P556,262.11
    Total Employer Contributions:           P84,212.50
    TOTAL EMPLOYER COST         :          P772,396.09

[2] AVERAGES PER EMPLOYEE
    Avg Basic Salary            :           P32,725.00
    Avg Gross Pay               :           P34,409.18
    Avg Tax Withheld            :            P1,724.20
    Avg Net Pay                 :           P27,813.11
    Avg Employer Cost           :           P38,619.80
    Avg Tax / Gross             :                5.01%
    Avg Net / Gross             :               80.83%

[3] HIGHEST / LOWEST EARNERS
    Highest Basic Salary  : Hazel Docil     P42,000.00
    Lowest  Basic Salary  : Cjay Mapa       P26,000.00
    Highest NET Pay       : Hazel Docil     P35,941.67
    Lowest  NET Pay       : Cjay Mapa       P22,833.44

[4] DEPARTMENT BREAKDOWN
    Department     Count      Avg Gross     Avg Tax       Avg Net     Total ER Cost
    Finance            3     P35,333.33   P1,770.54    P28,412.79       P119,440.00
    HR                 3     P29,263.02     P917.58    P24,216.28        P99,041.56
    IT                 5     P40,285.94   P2,742.63    P31,918.30       P224,304.69
    Marketing          3     P32,382.81   P1,351.80    P26,376.85       P109,525.94
    Operations         3     P36,687.50   P2,056.62    P29,414.21       P123,452.50
    Sales              3     P28,584.64     P827.07    P23,803.40        P96,631.41

[5] TAX BRACKET DISTRIBUTION
    Bracket                          Count     Share
    15% (250k-400k)                     13     65.0%
    20% + 22.5k (400k-800k)              7     35.0%

[6] WHERE THE COMPANY'S MONEY GOES (% of total employer cost)
    Category                              Amount       Share
    Employee NET pay                 P556,262.11      72.02%
    Employee Tax (BIR)                P34,483.98       4.46%
    Employee Contributions            P51,987.50       6.73%
    Employee Voluntary/Other          P45,450.00       5.88%
    Employer Contributions            P84,212.50      10.90%
    TOTAL EMPLOYER COST              P772,396.09     100.00%
```

**How to read it:**

- **[1]** adds up each money column across all employees.
- **[2]** divides the totals by the number of employees. "Avg Tax / Gross" is the total tax divided by the total gross.
- **[3]** finds the top and bottom by basic salary and by net pay.
- **[4]** groups employees by department and averages each group. Total ER Cost is a sum, not an average.
- **[5]** annualizes each employee's taxable income and counts how many fall in each bracket. In the sample data, nobody is tax-exempt and nobody is above the P400k to P800k bracket.
- **[6]** splits the total employer cost into where the money goes. The five slices add up to exactly 100%.

If pandas is not available, option 2 shows a shorter summary (employees, total gross, net, tax, employer cost).

---

### Option 3: Sort Employees

**What it does:** Sorts all employees with your own `merge_sort` function and prints the result with `print_table()`.

```
---------- SORT EMPLOYEES ----------
Sort by which field?
  1. Name (A-Z)
  2. Department (A-Z)
  3. Salary (Highest First)
  0. Cancel
Choice: 3
```

Result for option 3 (first rows):

```
--- Sorted by Salary (Highest First) (20) ---
Hazel Docil          IT           P45,937.50  P3,795.83  P35,941.67
Kenshin Abesamis     IT           P43,125.00  P3,243.33  P33,931.67
Koyl Salvick         IT           P40,523.44  P2,728.02  P31,970.42
Rhian De Torres      IT           P40,671.88  P2,762.71  P32,209.17
Yaj Manimtim         Operations   P39,601.56  P2,553.65  P31,472.91
...
```

Sorting is by **basic salary**, not gross pay. That is why Koyl Salvick (salary P39,000) appears above Rhian De Torres (P38,000) even though Rhian's gross is higher after overtime.

**How merge sort works here:** The list is split in half again and again until each piece has one item. The pieces are then merged back together in order. Text fields are compared in lowercase so "alice" and "Alice" sort together. Option 1 sorts A-Z by name (first rows: Aldrin Billano, Bowee Maano, Bryan Carias, Cjay Mapa, Gian Gonzales...). Option 2 sorts A-Z by department.

---

### Option 4: Top 5 Highest-Paid Employees

**What it does:** Builds a max-heap from all employees, then removes the largest five times.

```
========================================
       TOP 5 HIGHEST-PAID EMPLOYEES
========================================
1. [IT] Hazel Docil - IT - Salary: P42,000.00
2. [IT] Kenshin Abesamis - IT - Salary: P40,000.00
3. [IT] Koyl Salvick - IT - Salary: P39,000.00
4. [IT] Rhian De Torres - IT - Salary: P38,000.00
5. [OPS] Yaj Manimtim - Operations - Salary: P37,000.00
========================================
```

**How the heap works:** `build_heap()` arranges the list so every parent has a salary at least as large as its children, which puts the highest salary at position 0. `extract_max()` takes that top item, moves the last item to the top, and calls `heapify()` to push it back down to its correct place. Repeating this five times returns the top five in order, without sorting the whole list.

---

### Option 5: Search Employee

**What it does:** Looks for an **exact** match on employee ID or full name (not case-sensitive). When found, it prints two things: the payslip, then a "where your salary went" breakdown.

```
Enter Employee ID or Name: kenshin abesamis
```

**Part A: Payslip** (`print_payslip()`)

```
================================
         EMPLOYEE [IT]
================================
Employee ID   : IT-e9f0a1b2
Name          : Kenshin Abesamis
Department    : [IT] IT
--------------------------------
Basic Salary  : P40,000.00
Overtime Hrs  : 10.00
Overtime Pay  : P3,125.00
GROSS PAY     : P43,125.00
--------------------------------
EMPLOYEE DEDUCTIONS (mandatory, tax-exempt):
  SSS         : P1,750.00
  PhilHealth  : P1,000.00
  Pag-IBIG    : P200.00
EMPLOYEE DEDUCTIONS (voluntary / other):
  SSS excess  : P0.00
  Other Deduct: P3,000.00
--------------------------------
TAXABLE INCOME: P40,175.00
TAX WITHHELD  : P3,243.33
NET PAY       : P33,931.67
--------------------------------
EMPLOYER CONTRIBUTIONS (cost to company):
  SSS         : P3,500.00
  SSS EC      : P30.00
  PhilHealth  : P1,000.00
  Pag-IBIG    : P200.00
TOTAL EMPLOYER COST: P47,855.00
================================
```

The payslip has three parts: what the employee earns, what is taken from them (the net pay is what is left), and what the company pays on top.

**Part B: Salary breakdown** (`_print_deduction_summary()`)

```
==============================================================
          WHERE YOUR SALARY WENT  [IT]
==============================================================
Employee : Kenshin Abesamis
ID       : IT-e9f0a1b2

[A] MONEY IN (Earnings)
    Basic Salary            :     P40,000.00
    Overtime Pay            :      P3,125.00
    GROSS PAY               :     P43,125.00

[B] MANDATORY CONTRIBUTIONS (tax-exempt)
    SSS       (5% of MSC)   :      P1,750.00
    PhilHealth(2.5% salary) :      P1,000.00
    Pag-IBIG  (2% of MFS)   :        P200.00
    Subtotal                :      P2,950.00

[C] TAX (TRAIN Law)
    Taxable Income (month)  :     P40,175.00
    Taxable Income (annual) :    P482,100.00
    Tax Withheld            :      P3,243.33

[D] OTHER DEDUCTIONS (not tax-exempt)
    Voluntary SSS           :          P0.00
    Other Deductions        :      P3,000.00

[E] WHERE THE SALARY WENT
    Gross Pay               :     P43,125.00
    - Mandatory contribs    :      P2,950.00
    - Tax withheld          :      P3,243.33
    - Voluntary SSS         :          P0.00
    - Other deductions      :      P3,000.00
    Total Deducted          :      P9,193.33
    NET PAY (take-home)     :     P33,931.67

[F] PERCENTAGE OF GROSS
    SSS                     :          4.06%  -> P1,750.00
    PhilHealth              :          2.32%  -> P1,000.00
    Pag-IBIG                :          0.46%  -> P200.00
    Tax                     :          7.52%  -> P3,243.33
    Other Deductions        :          6.96%  -> P3,000.00
    Total Deducted          :         21.32%
    NET PAY                 :         78.68%  -> P33,931.67
```

**How to read it:** [A] is income, [B] and [C] are the legal deductions, [D] is everything else, and [E] subtracts all of it from gross to reach take-home pay. [F] shows each deduction as a share of gross, so Kenshin keeps 78.68% of his gross pay. Voluntary SSS only appears in [F] if it is above zero.

---

### Option 6: Delete Employee

**What it does:** Finds the employee by ID, asks for confirmation, then rewrites the CSV without that record.

```
Enter Employee ID to delete: IT-a1b2c3d4
About to delete: Yvonne Escobido (ID IT-a1b2c3d4)
Confirm? (y/n): y
Deleted employee IT-a1b2c3d4.
```

If the ID does not exist, it prints `Employee ID not found.` and logs a `DELETE_FAILED` entry.

---

### Option 7: Update Salary

**What it does:** Shows the matched record, asks for a new basic salary and a confirmation, then builds a **new** `Employee` object. Because the object is rebuilt, every dependent value (contributions, tax, net, employer cost) is recalculated automatically. Only that one record is replaced.

```
Matched record:
  ID         : IT-a1b2c3d4
  Name       : Yvonne Escobido
  Department : [IT] IT
  Salary     : P30,000.00
  Net Pay    : P25,538.60

Enter New Basic Salary: P35000
Update ONLY this record (ID IT-a1b2c3d4) to P35,000.00? (y/n): y

Salary updated successfully! (1 record only)
```

The updated payslip is printed afterward. The employee's ID, overtime hours, other deductions, and voluntary SSS are kept from the old record. The log records the change as `30000.0 -> 35000.0`.

---

### Option 8: Restore Default Employees

**What it does:** Deletes the CSV and re-creates it with the 20 built-in employees.

```
This will ERASE all employees. Continue? (y/n): y
Restored 20 default employees.
```

This is destructive: any employees you added are lost. The seed list is `DEFAULT_EMPLOYEES` in the code. The same seeding happens automatically on the first run if the CSV does not exist.

---

### Option 9: Linear Search (by field)

**What it does:** Checks every record one by one, and returns every record where the chosen field **contains** your text (not case-sensitive).

```
--- Linear Search ---
Search by which field?
  1. Name
  2. Employee ID
  3. Department
Choice: 1
Search name: gian
```

```
=== Linear Search: name contains 'gian' (2) ===
ID             Name            Department     Gross        Tax        Net     Employer Cost
OPS-5d6e7f80   Gian Gonzales   Operations  P38,250.00  P2,288.33  P30,511.67    P42,880.00
HR-6e7f8091    Gian Mendoza    HR          P28,359.38    P789.53  P23,557.35    P32,026.88
```

Unlike option 5, this finds **partial** matches and can return several results. Searching department `it` returns all five IT employees. If nothing matches, it prints `No matches for 'xyz' in field 'name'.`

---

### Option 10: View History Log

**What it does:** Prints every line of `history2.log`. Each important action in the program calls `log_action()`, which appends a timestamped line.

```
--- History Log ---
Log file: .../history2.log
Total entries: 5

[2026-10-15 14:30:02] SESSION_START - Program started
[2026-10-15 14:30:15] VIEW_PAYROLL - 20 employees displayed
[2026-10-15 14:30:15] ADVANCED_ANALYTICS - pandas dashboard across 20 employees
[2026-10-15 14:31:40] SEARCH - query='kenshin abesamis' -> found Kenshin Abesamis
[2026-10-15 14:32:10] UPDATE_SALARY - Yvonne Escobido: 30000.0 -> 35000.0
```

Logged actions include `ADD`, `DELETE`, `UPDATE_SALARY`, `SEARCH`, `SORT`, `TOP5`, `LINEAR_SEARCH`, `PDF_PAYSLIP`, `EMAIL_PAYSLIP`, `EXPORT_EXCEL`, `BATCH_PDF`, and failed or cancelled versions of these.

---

### Option 11: Clear History Log

**What it does:** Deletes the log file after confirmation, then writes one new entry saying the log was cleared.

```
This will DELETE all history. Continue? (y/n): y
History log cleared.
```

---

### Option 12: Show Department Markers

**What it does:** Prints the table that controls ID prefixes and the `[XX]` markers.

```
--- Department Markers (Palatandaan) ---
Department     Prefix    Marker    Group
--------------------------------------------------
IT             IT        [IT]      Tech
HR             HR        [HR]      People
Finance        FIN       [FIN]     Money
Marketing      MKT       [MKT]     Brand
Sales          SLS       [SLS]     Revenue
Operations     OPS       [OPS]     Logistics
--------------------------------------------------
Unknown departments fall back to prefix 'GEN' and marker [GEN].
```

A department you type that is not in this list (for example "Legal") still works. It gets the `GEN` prefix and the `[GEN]` marker.

---

### Option 13: Generate PDF Payslip

**What it does:** Finds one employee by ID, asks for a pay period, and builds a styled PDF with `generate_payslip_pdf()`.

```
---------- GENERATE PDF PAYSLIP ----------
Enter Employee ID: IT-e9f0a1b2
Pay period (e.g., Oct 1-15, 2025) [blank for none]: Oct 1-15, 2026
[OK] PDF generated: .../payslips/payslip_IT-e9f0a1b2.pdf
```

**What the PDF contains, top to bottom:**

1. **Header band:** company name and address on the left (from `DEFAULT_COMPANY_NAME` and `DEFAULT_COMPANY_ADDRESS`), "PAYSLIP" and the pay period on the right
2. **Employee information box:** ID, name, department, date issued
3. **Earnings table (left):** basic salary, overtime pay, gross pay
4. **Deductions table (right):** SSS, PhilHealth, Pag-IBIG, withholding tax, plus voluntary SSS and other deductions when they are not zero, then total deductions
5. **Net pay bar:** a highlighted box with the take-home amount
6. **Signature lines:** employee and authorized signatory
7. **Footer:** a note that the payslip is system-generated, with the date and time

The PDF layout is placed with fixed coordinates (`set_xy`, `rect`, `line`), which is why the two tables line up side by side.

---

### Option 14: Email Payslip

**What it does:** Finds the employee, asks for an email address and pay period, prints the payslip on screen, generates the PDF, then sends it as an attachment.

```
---------- EMAIL PAYSLIP ----------
Enter Employee ID: IT-e9f0a1b2
Send payslip to (email): kenshin@example.com
(payslip is printed here)
Pay period (e.g., Oct 1-15, 2025) [blank for none]: Oct 1-15, 2026
PDF saved to: .../payslips/payslip_IT-e9f0a1b2.pdf
[OK] Email sent to kenshin@example.com
```

The email has the subject `Payslip - Kenshin Abesamis`, a short body with gross, tax, and net pay, and the PDF attached. The email address is only checked for an `@`. If sending fails, it prints `[X] Failed to send email: ...` and the log records `FAILED`. If the PDF cannot be made, the email is still sent without an attachment.

---

### Option 15: Export Excel Report

**What it does:** Writes all payroll data to a new timestamped `.xlsx` file in the `exports/` folder.

```
[OK] Excel exported: .../exports/payroll_export_20261015_143500.xlsx
```

The workbook has three sheets:

| Sheet | Contents |
|---|---|
| **Employees** | Every column from the CSV, one row per employee |
| **By Department** | Per department: head count, total gross, total net, total tax, total employer cost |
| **Tax Brackets** | How many employees fall in each bracket |

Each export gets a new filename, so older exports are never overwritten.

---

### Option 16: Batch Generate All Payslips

**What it does:** Loops through every employee and creates a PDF for each, using the same pay period for all.

```
---------- BATCH GENERATE ALL PAYSLIPS ----------
Pay period (e.g., Oct 1-15, 2025) [blank for none]: Oct 1-15, 2026
Generate PDF payslips for ALL 20 employees? (y/n): y
  [OK]  Yvonne Escobido              -> payslip_IT-a1b2c3d4.pdf
  [OK]  Rizzel Disquitado            -> payslip_HR-b3c4d5e6.pdf
  [OK]  Bryan Carias                 -> payslip_FIN-c5d6e7f8.pdf
  ...

Done. 20 generated, 0 failed.
All PDFs saved to: .../payslips
```

The program counts successes and failures and shows `[X]` for any employee whose PDF failed.

---

### Option 17: Exit

```
Thank you for using Employee Payroll Sorter!
```

The program logs `SESSION_END` and stops. Pressing Ctrl+C also ends it cleanly, with an "Interrupted. Goodbye!" message and a log entry.

---

## 4. Data Storage

All employees are stored in `employees2.csv`. Each row has 20 columns:

`id, name, department, salary, overtime, overtime_pay, sss, philhealth, pagibig, voluntary_sss, deductions, sss_employer, ec_employer, philhealth_employer, pagibig_employer, employer_cost, gross, taxable_income, tax_withheld, net`

| Operation | How it touches the file |
|---|---|
| Add employee | Appends one row (`save_to_csv`) |
| Delete, update salary, restore defaults | Rewrites the whole file (`rewrite_csv`) |
| Every view, search, sort, report | Reads the file fresh (`load_employees`), converting number columns to floats |

Because the computed values (net, tax, and so on) are stored in the file, changing a salary by hand in the CSV will not recalculate them. Use option 7 so the `Employee` class recomputes everything.

Other files and folders the program creates next to the script:

| Path | Created by |
|---|---|
| `history2.log` | Every logged action |
| `payslips/` | Options 13, 14, 16 |
| `exports/` | Option 15 |

---

## 5. Things to Know About How It Behaves

- **Salary is monthly.** There is no semi-monthly or weekly mode.
- **Overtime uses one flat rate:** 160 hours per month and 125%.
- **Tax is annualized from a single month.** There are no year-to-date adjustments.
- **IDs are the real identifier.** Names may repeat (after confirmation), so delete, update, and PDF options all ask for the ID.
- **Option 5 is exact, option 9 is partial.** Use option 9 when you do not remember the full name.
- **The PDF shows `P` instead of the peso symbol,** because the built-in PDF font cannot print it.
- **Rates are fixed in the constants.** Government rates change, so update the constants at the top of the file if they do.

---

## License

None. This is a school project.
