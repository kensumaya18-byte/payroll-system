import csv
import os
import uuid
import smtplib
import warnings
from datetime import datetime
from email.message import EmailMessage
from typing import Optional

warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    console = None
    RICH_AVAILABLE = False

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False

try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "employees2.csv")
LOG_FILE = os.path.join(BASE_DIR, "history2.log")
PAYSLIP_DIR = os.path.join(BASE_DIR, "payslips")
EXPORT_DIR  = os.path.join(BASE_DIR, "exports")
MIN_NAME_WIDTH = 30

DEFAULT_COMPANY_NAME    = "Sawi sa Pag-IBIG Inc."
DEFAULT_COMPANY_ADDRESS = "Brgy. Dila, sa loob ng Asiatech, Room 4A1"

DEPARTMENT_MARKERS = {
    "IT":         {"prefix": "IT",  "marker": "[IT]",  "color": "Tech"},
    "HR":         {"prefix": "HR",  "marker": "[HR]",  "color": "People"},
    "Finance":    {"prefix": "FIN", "marker": "[FIN]", "color": "Money"},
    "Marketing":  {"prefix": "MKT", "marker": "[MKT]", "color": "Brand"},
    "Sales":      {"prefix": "SLS", "marker": "[SLS]", "color": "Revenue"},
    "Operations": {"prefix": "OPS", "marker": "[OPS]", "color": "Logistics"},
}


def get_department_marker(department: str) -> str:
    info = DEPARTMENT_MARKERS.get(department.strip().title())
    return info["marker"] if info else "[GEN]"


def get_department_prefix(department: str) -> str:
    info = DEPARTMENT_MARKERS.get(department.strip().title())
    return info["prefix"] if info else "GEN"


def generate_employee_id(department: str) -> str:
    prefix = get_department_prefix(department)
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


ANNUAL_TAX_EXEMPTION = 250000

SSS_MSC_FLOOR = 5000
SSS_MSC_CEILING = 35000
SSS_EMPLOYEE_RATE = 0.05
SSS_EMPLOYER_RATE = 0.10
SSS_EC_THRESHOLD = 14500
SSS_EC_LOW = 10.0
SSS_EC_HIGH = 30.0

PHILHEALTH_SALARY_FLOOR = 10000
PHILHEALTH_SALARY_CEILING = 100000
PHILHEALTH_TOTAL_RATE = 0.05
PHILHEALTH_EMPLOYEE_RATE = 0.025
PHILHEALTH_EMPLOYER_RATE = 0.025

PAGIBIG_MFS_CEILING = 10000
PAGIBIG_EMPLOYEE_RATE = 0.02
PAGIBIG_EMPLOYER_RATE = 0.02


def compute_sss_employee(salary: float) -> float:
    msc = max(SSS_MSC_FLOOR, min(salary, SSS_MSC_CEILING))
    return round(msc * SSS_EMPLOYEE_RATE, 2)


def compute_philhealth_employee(salary: float) -> float:
    base = max(PHILHEALTH_SALARY_FLOOR, min(salary, PHILHEALTH_SALARY_CEILING))
    return round(base * PHILHEALTH_EMPLOYEE_RATE, 2)


def compute_pagibig_employee(salary: float) -> float:
    base = min(salary, PAGIBIG_MFS_CEILING)
    return round(base * PAGIBIG_EMPLOYEE_RATE, 2)


def compute_sss_employer(salary: float) -> float:
    msc = max(SSS_MSC_FLOOR, min(salary, SSS_MSC_CEILING))
    return round(msc * SSS_EMPLOYER_RATE, 2)


def compute_ec_employer(salary: float) -> float:
    msc = max(SSS_MSC_FLOOR, min(salary, SSS_MSC_CEILING))
    return SSS_EC_HIGH if msc > SSS_EC_THRESHOLD else SSS_EC_LOW


def compute_philhealth_employer(salary: float) -> float:
    base = max(PHILHEALTH_SALARY_FLOOR, min(salary, PHILHEALTH_SALARY_CEILING))
    return round(base * PHILHEALTH_EMPLOYER_RATE, 2)


def compute_pagibig_employer(salary: float) -> float:
    base = min(salary, PAGIBIG_MFS_CEILING)
    return round(base * PAGIBIG_EMPLOYER_RATE, 2)


def compute_taxable_income(gross, sss_mandatory, philhealth, pagibig, voluntary_excess=0.0) -> float:
    mandatory = sss_mandatory + philhealth + pagibig
    return max(0.0, gross - mandatory)


def compute_monthly_tax(taxable_monthly: float) -> float:
    annual = taxable_monthly * 12

    if annual <= 250000:
        annual_tax = 0.0
    elif annual <= 400000:
        annual_tax = (annual - 250000) * 0.15
    elif annual <= 800000:
        annual_tax = 22500 + (annual - 400000) * 0.20
    elif annual <= 2000000:
        annual_tax = 102500 + (annual - 800000) * 0.25
    elif annual <= 8000000:
        annual_tax = 402500 + (annual - 2000000) * 0.30
    else:
        annual_tax = 2202500 + (annual - 8000000) * 0.35

    return round(annual_tax / 12, 2)


def log_action(action: str, details: str = "") -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {action}"
    if details:
        line += f" - {details}"
    try:
        with open(LOG_FILE, mode="a", encoding="utf-8") as f:
            f.write(line + "\n")
    except PermissionError:
        print(f"Warning: Could not write to {LOG_FILE} (file locked?).")


def view_history_log() -> None:
    print("\n--- History Log ---")
    if not os.path.isfile(LOG_FILE):
        print("No history yet. Actions will appear here as you use the program.")
        return
    try:
        with open(LOG_FILE, mode="r", encoding="utf-8") as f:
            lines = f.readlines()
    except PermissionError:
        print(f"Could not read {LOG_FILE} (file locked?).")
        return

    if not lines:
        print("History log is empty.")
        return

    print(f"Log file: {LOG_FILE}")
    print(f"Total entries: {len(lines)}\n")
    for line in lines:
        print(line.rstrip())


def clear_history_log() -> None:
    if not os.path.isfile(LOG_FILE):
        print("No history to clear.")
        return
    confirm = input("This will DELETE all history. Continue? (y/n): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Cancelled.")
        return
    try:
        os.remove(LOG_FILE)
        print("History log cleared.")
        log_action("CLEAR_HISTORY", "Log was cleared by user")
    except PermissionError:
        print(f"Could not delete {LOG_FILE} (file locked?).")


class MaxHeap:
    def __init__(self):
        self.heap = []

    def insert(self, employee: dict) -> None:
        self.heap.append(employee)
        self.sift_up(len(self.heap) - 1)

    def sift_up(self, index: int) -> None:
        while index > 0:
            parent = (index - 1) // 2
            if self.heap[index]["salary"] > self.heap[parent]["salary"]:
                self.heap[index], self.heap[parent] = self.heap[parent], self.heap[index]
                index = parent
            else:
                break

    def heapify(self, index: int) -> None:
        while True:
            largest = index
            left = 2 * index + 1
            right = 2 * index + 2

            if left < len(self.heap) and self.heap[left]["salary"] > self.heap[largest]["salary"]:
                largest = left
            if right < len(self.heap) and self.heap[right]["salary"] > self.heap[largest]["salary"]:
                largest = right

            if largest != index:
                self.heap[index], self.heap[largest] = self.heap[largest], self.heap[index]
                index = largest
            else:
                break

    def build_heap(self, employees: list) -> None:
        self.heap = employees.copy()
        start = (len(self.heap) // 2) - 1
        for i in range(start, -1, -1):
            self.heapify(i)

    def extract_max(self) -> Optional[dict]:
        if not self.heap:
            return None
        maximum = self.heap[0]
        last = self.heap.pop()
        if self.heap:
            self.heap[0] = last
            self.heapify(0)
        return maximum

    def is_empty(self) -> bool:
        return len(self.heap) == 0

    def size(self) -> int:
        return len(self.heap)


def merge_sort(data: list, field: str, reverse: bool = False) -> list:
    if len(data) <= 1:
        return data
    middle = len(data) // 2
    left = merge_sort(data[:middle], field, reverse)
    right = merge_sort(data[middle:], field, reverse)
    return merge(left, right, field, reverse)


def merge(left: list, right: list, field: str, reverse: bool) -> list:
    result = []
    i = j = 0

    while i < len(left) and j < len(right):
        left_value = left[i][field]
        right_value = right[j][field]

        if isinstance(left_value, str):
            left_value = left_value.lower()
        if isinstance(right_value, str):
            right_value = right_value.lower()

        condition = left_value >= right_value if reverse else left_value <= right_value

        if condition:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    result.extend(left[i:])
    result.extend(right[j:])
    return result


class Employee:
    FIELDNAMES = [
        "id", "name", "department", "salary", "overtime", "overtime_pay",
        "sss", "philhealth", "pagibig", "voluntary_sss", "deductions",
        "sss_employer", "ec_employer", "philhealth_employer",
        "pagibig_employer", "employer_cost",
        "gross", "taxable_income", "tax_withheld", "net",
    ]

    HOURLY_DIVISOR = 160
    OVERTIME_MULTIPLIER = 1.25

    def __init__(self, name, department, salary, overtime=0.0,
                 deductions=0.0, voluntary_sss=0.0, emp_id=None):
        self.id = emp_id or generate_employee_id(department)
        self.name = name
        self.department = department
        self.salary = salary
        self.overtime = overtime
        self.deductions = deductions
        self.voluntary_sss = voluntary_sss

        self.sss = compute_sss_employee(salary)
        self.philhealth = compute_philhealth_employee(salary)
        self.pagibig = compute_pagibig_employee(salary)

        self.sss_employer = compute_sss_employer(salary)
        self.ec_employer = compute_ec_employer(salary)
        self.philhealth_employer = compute_philhealth_employer(salary)
        self.pagibig_employer = compute_pagibig_employer(salary)

        self.overtime_pay = self._compute_overtime_pay()
        self.gross = self.salary + self.overtime_pay

        self.taxable_income = compute_taxable_income(
            self.gross, self.sss, self.philhealth, self.pagibig, self.voluntary_sss,
        )
        self.tax_withheld = compute_monthly_tax(self.taxable_income)
        self.net = (
            self.gross - self.sss - self.philhealth - self.pagibig
            - self.voluntary_sss - self.tax_withheld - self.deductions
        )
        self.employer_cost = (
            self.gross + self.sss_employer + self.ec_employer
            + self.philhealth_employer + self.pagibig_employer
        )

    def _compute_overtime_pay(self) -> float:
        hourly_rate = self.salary / self.HOURLY_DIVISOR
        return self.overtime * hourly_rate * self.OVERTIME_MULTIPLIER

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "department": self.department,
            "salary": self.salary, "overtime": self.overtime,
            "overtime_pay": self.overtime_pay,
            "sss": self.sss, "philhealth": self.philhealth, "pagibig": self.pagibig,
            "voluntary_sss": self.voluntary_sss, "deductions": self.deductions,
            "sss_employer": self.sss_employer, "ec_employer": self.ec_employer,
            "philhealth_employer": self.philhealth_employer,
            "pagibig_employer": self.pagibig_employer,
            "employer_cost": self.employer_cost,
            "gross": self.gross, "taxable_income": self.taxable_income,
            "tax_withheld": self.tax_withheld, "net": self.net,
        }

    def save_to_csv(self, filename: str = CSV_FILE) -> None:
        write_header = not os.path.isfile(filename)
        with open(filename, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self.FIELDNAMES)
            if write_header:
                writer.writeheader()
            writer.writerow(self.to_dict())


def load_employees(filename: str = CSV_FILE) -> list:
    if not os.path.isfile(filename):
        return []
    with open(filename, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return []
        fields = reader.fieldnames
        required = set(Employee.FIELDNAMES)
        missing = required - set(fields)
        if missing:
            print(f"Warning: CSV is missing columns {missing}.")
            print(f"Found columns: {fields}")
            print(f"File: {filename}")
            print("Use option 8 (Restore default employees) or delete the file to re-seed.")
            return []
        rows = list(reader)

    numeric_fields = (
        "salary", "overtime", "overtime_pay",
        "sss", "philhealth", "pagibig", "voluntary_sss", "deductions",
        "sss_employer", "ec_employer", "philhealth_employer",
        "pagibig_employer", "employer_cost",
        "gross", "taxable_income", "tax_withheld", "net",
    )
    for r in rows:
        for num_field in numeric_fields:
            try:
                r[num_field] = float(r.get(num_field, 0) or 0)
            except ValueError:
                r[num_field] = 0.0
    return rows


def load_employees_df(filename: str = CSV_FILE):
    if pd is None:
        return None
    if not os.path.isfile(filename):
        return pd.DataFrame()
    try:
        df = pd.read_csv(filename, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        return pd.DataFrame()

    numeric_cols = [
        "salary", "overtime", "overtime_pay",
        "sss", "philhealth", "pagibig", "voluntary_sss", "deductions",
        "sss_employer", "ec_employer", "philhealth_employer",
        "pagibig_employer", "employer_cost",
        "gross", "taxable_income", "tax_withheld", "net",
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def rewrite_csv(rows: list, filename: str = CSV_FILE) -> None:
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=Employee.FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


DEFAULT_EMPLOYEES = [
    ("Yvonne Escobido", "IT", 30000, 5, 2000),
    ("Rizzel Disquitado", "HR", 28000, 8, 1800),
    ("Bryan Carias", "Finance", 35000, 6, 2500),
    ("Bowee Maano", "Marketing", 32000, 4, 2200),
    ("Kenshin Abesamis", "IT", 40000, 10, 3000),
    ("Marvin Camat", "Sales", 27000, 7, 1700),
    ("Ryan Napire", "Operations", 31000, 5, 2100),
    ("Prince Ripalda", "HR", 29000, 3, 1900),
    ("Rhian De Torres", "IT", 38000, 9, 2800),
    ("Aldrin Billano", "Finance", 33000, 4, 2300),
    ("Cjay Mapa", "Sales", 26000, 6, 1600),
    ("Patrick Ferrer", "Marketing", 30000, 5, 2000),
    ("Gian Gonzales", "Operations", 36000, 8, 2600),
    ("Gian Mendoza", "HR", 27500, 4, 1750),
    ("Hazel Docil", "IT", 42000, 12, 3200),
    ("Jasfer Leonor", "Finance", 34000, 5, 2400),
    ("Jaymiel Piedragosa", "Sales", 28500, 7, 1850),
    ("Ken Sumaya", "Marketing", 31500, 6, 2150),
    ("Yaj Manimtim", "Operations", 37000, 9, 2700),
    ("Koyl Salvick", "IT", 39000, 5, 2900),
]


def seed_default_employees(filename: str = CSV_FILE, announce: bool = True) -> None:
    if os.path.isfile(filename):
        return
    if announce:
        print(f"No employees file found. Seeding defaults into {filename}...")
    rows = []
    for name, dept, salary, ot, ded in DEFAULT_EMPLOYEES:
        emp = Employee(name, dept, salary, ot, ded)
        rows.append(emp.to_dict())
    rewrite_csv(rows, filename)
    if announce:
        print(f"Added {len(DEFAULT_EMPLOYEES)} default employees.")
    log_action("SEED_DEFAULTS", f"Created {filename} with {len(DEFAULT_EMPLOYEES)} employees")


def restore_default_employees(filename: str = CSV_FILE) -> None:
    confirm = input("This will ERASE all employees. Continue? (y/n): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Cancelled.")
        log_action("RESTORE_DEFAULTS", "Cancelled by user")
        return
    try:
        if os.path.isfile(filename):
            os.remove(filename)
    except PermissionError:
        print(f"Could not delete {filename} - it may be open in Excel or locked by OneDrive.")
        log_action("RESTORE_DEFAULTS", "FAILED (file locked)")
        return
    seed_default_employees(filename, announce=False)
    print(f"Restored {len(DEFAULT_EMPLOYEES)} default employees.")
    log_action("RESTORE_DEFAULTS", f"Restored {len(DEFAULT_EMPLOYEES)} default employees")


def get_number(message: str) -> float:
    while True:
        try:
            value = float(input(message))
            if value < 0:
                print("Please enter a positive number.")
            else:
                return value
        except ValueError:
            print("Please enter a valid number.")


def get_text(message: str) -> str:
    while True:
        value = input(message).strip()
        if value:
            return value
        print("This field cannot be empty.")


def peso(value: float) -> str:
    return f"P{value:,.2f}"


def print_table(rows: list, title: str = "Employees") -> None:
    if not rows:
        print(f"\n--- {title} (0) ---")
        print("No records.")
        return

    if TABULATE_AVAILABLE:
        table_data = []
        for r in rows:
            table_data.append([
                r.get("id", "?"),
                get_department_marker(r.get("department", "")),
                r.get("name", "?"),
                r.get("department", "?"),
                peso(r.get("gross", 0)),
                peso(r.get("tax_withheld", 0)),
                peso(r.get("net", 0)),
                peso(r.get("employer_cost", 0)),
            ])

        headers = ["ID", "", "Name", "Department", "Gross", "Tax", "Net", "Employer Cost"]

        print(f"\n=== {title} ({len(rows)}) ===")
        print(tabulate(table_data, headers=headers, tablefmt="fancy_grid",
                       colalign=("left", "left", "left", "left",
                                 "right", "right", "right", "right")))
        return

    if RICH_AVAILABLE:
        table = Table(title=f"{title} ({len(rows)})", box=box.SIMPLE_HEAVY)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("", style="yellow", no_wrap=True)
        table.add_column("Name", style="white")
        table.add_column("Department", style="magenta")
        table.add_column("Gross", justify="right", style="green")
        table.add_column("Tax", justify="right", style="red")
        table.add_column("Net", justify="right", style="bright_green")
        table.add_column("Employer Cost", justify="right", style="blue")
        for r in rows:
            marker = get_department_marker(r.get("department", ""))
            table.add_row(
                str(r.get("id", "?")), marker, str(r.get("name", "?")),
                str(r.get("department", "?")), peso(r.get("gross", 0)),
                peso(r.get("tax_withheld", 0)), peso(r.get("net", 0)),
                peso(r.get("employer_cost", 0)),
            )
        console.print(table)
        return

    name_width = max(MIN_NAME_WIDTH, max(len(r.get("name") or "") for r in rows) + 2)
    print(f"\n--- {title} ({len(rows)}) ---")
    header = (f"{'ID':<16}{'':<6}{'Name':<{name_width}}{'Department':<18}"
              f"{'Gross':>15}{'Tax':>12}{'Net':>15}{'Employer Cost':>18}")
    print(header)
    print("-" * len(header))
    for r in rows:
        marker = get_department_marker(r.get("department", ""))
        print(
            f"{r.get('id', '?'):<16}{marker:<6}{r.get('name', '?'):<{name_width}}"
            f"{r.get('department', '?'):<18}{peso(r.get('gross', 0)):>15}"
            f"{peso(r.get('tax_withheld', 0)):>12}{peso(r.get('net', 0)):>15}"
            f"{peso(r.get('employer_cost', 0)):>18}"
        )


def show_department_markers() -> None:
    print("\n--- Department Markers (Palatandaan) ---")
    print(f"{'Department':<15}{'Prefix':<10}{'Marker':<10}{'Group'}")
    print("-" * 50)
    for dept, info in DEPARTMENT_MARKERS.items():
        print(f"{dept:<15}{info['prefix']:<10}{info['marker']:<10}{info['color']}")
    print("-" * 50)
    print("Unknown departments fall back to prefix 'GEN' and marker [GEN].")
    log_action("VIEW_MARKERS", "Displayed department markers")


def linear_search(employees: list, field: str, query: str) -> list:
    results = []
    for employee in employees:
        value = str(employee.get(field, "")).lower()
        if query in value:
            results.append(employee)
    return results


def linear_search_menu() -> None:
    print("\n--- Linear Search ---")
    print("Search by which field?")
    print("  1. Name")
    print("  2. Employee ID")
    print("  3. Department")
    choice = input("Choice: ").strip()
    field_map = {"1": "name", "2": "id", "3": "department"}
    field = field_map.get(choice)
    if not field:
        print("Invalid choice.")
        return
    query = input(f"Search {field}: ").strip().lower()
    if not query:
        print("Empty query.")
        return
    rows = load_employees()
    if not rows:
        print("No employees yet.")
        return
    results = linear_search(rows, field, query)
    _show_linear_results(results, field, query)


def _show_linear_results(results: list, field: str, query: str) -> None:
    if not results:
        print(f"\nNo matches for '{query}' in field '{field}'.")
        log_action("LINEAR_SEARCH", f"field={field}, query='{query}' -> 0 matches")
        return
    print_table(results, title=f"Linear Search: {field} contains '{query}'")
    log_action("LINEAR_SEARCH", f"field={field}, query='{query}' -> {len(results)} matches")


def print_payslip(emp: dict) -> None:
    marker = get_department_marker(emp.get("department", ""))
    print("\n================================")
    print(f"         EMPLOYEE {marker}")
    print("================================")
    print("Employee ID   :", emp.get("id", "?"))
    print("Name          :", emp.get("name", "?"))
    print("Department    :", f"{marker} {emp.get('department', '?')}")
    print("--------------------------------")
    print("Basic Salary  :", peso(emp.get("salary", 0)))
    print("Overtime Hrs  :", f"{emp.get('overtime', 0):.2f}")
    print("Overtime Pay  :", peso(emp.get("overtime_pay", 0)))
    print("GROSS PAY     :", peso(emp.get("gross", 0)))
    print("--------------------------------")
    print("EMPLOYEE DEDUCTIONS (mandatory, tax-exempt):")
    print("  SSS         :", peso(emp.get("sss", 0)))
    print("  PhilHealth  :", peso(emp.get("philhealth", 0)))
    print("  Pag-IBIG    :", peso(emp.get("pagibig", 0)))
    print("EMPLOYEE DEDUCTIONS (voluntary / other):")
    print("  SSS excess  :", peso(emp.get("voluntary_sss", 0)))
    print("  Other Deduct:", peso(emp.get("deductions", 0)))
    print("--------------------------------")
    print("TAXABLE INCOME:", peso(emp.get("taxable_income", 0)))
    print("TAX WITHHELD  :", peso(emp.get("tax_withheld", 0)))
    print("NET PAY       :", peso(emp.get("net", 0)))
    print("--------------------------------")
    print("EMPLOYER CONTRIBUTIONS (cost to company):")
    print("  SSS         :", peso(emp.get("sss_employer", 0)))
    print("  SSS EC      :", peso(emp.get("ec_employer", 0)))
    print("  PhilHealth  :", peso(emp.get("philhealth_employer", 0)))
    print("  Pag-IBIG    :", peso(emp.get("pagibig_employer", 0)))
    print("TOTAL EMPLOYER COST:", peso(emp.get("employer_cost", 0)))
    print("================================")


def _print_deduction_summary(emp: dict) -> None:
    marker = get_department_marker(emp.get("department", ""))
    gross = emp.get("gross", 0)
    basic = emp.get("salary", 0)
    ot_pay = emp.get("overtime_pay", 0)
    sss = emp.get("sss", 0)
    philhealth = emp.get("philhealth", 0)
    pagibig = emp.get("pagibig", 0)
    voluntary_sss = emp.get("voluntary_sss", 0)
    other_deduct = emp.get("deductions", 0)
    tax = emp.get("tax_withheld", 0)
    taxable = emp.get("taxable_income", 0)
    net = emp.get("net", 0)

    mandatory_total = sss + philhealth + pagibig
    total_employee_deduct = mandatory_total + voluntary_sss + tax + other_deduct
    annual_taxable = taxable * 12

    print("\n" + "=" * 62)
    print(f"          WHERE YOUR SALARY WENT  {marker}")
    print("=" * 62)
    print(f"Employee : {emp.get('name', '?')}")
    print(f"ID       : {emp.get('id', '?')}")
    print("=" * 62)

    print("\n[A] MONEY IN (Earnings)")
    print(f"    Basic Salary            : {peso(basic):>14}")
    print(f"    Overtime Pay            : {peso(ot_pay):>14}")
    print(f"    -----------------------------------------")
    print(f"    GROSS PAY               : {peso(gross):>14}")

    print("\n[B] MANDATORY CONTRIBUTIONS (tax-exempt)")
    print(f"    SSS       (5% of MSC)   : {peso(sss):>14}")
    print(f"    PhilHealth(2.5% salary) : {peso(philhealth):>14}")
    print(f"    Pag-IBIG  (2% of MFS)   : {peso(pagibig):>14}")
    print(f"    -----------------------------------------")
    print(f"    Subtotal                : {peso(mandatory_total):>14}")

    print("\n[C] TAX (TRAIN Law)")
    print(f"    Taxable Income (month)  : {peso(taxable):>14}")
    print(f"    Taxable Income (annual) : {peso(annual_taxable):>14}")
    print(f"    Tax Withheld            : {peso(tax):>14}")

    print("\n[D] OTHER DEDUCTIONS (not tax-exempt)")
    print(f"    Voluntary SSS           : {peso(voluntary_sss):>14}")
    print(f"    Other Deductions        : {peso(other_deduct):>14}")

    print("\n[E] WHERE THE SALARY WENT")
    print(f"    Gross Pay               : {peso(gross):>14}")
    print(f"    - Mandatory contribs    : {peso(mandatory_total):>14}")
    print(f"    - Tax withheld          : {peso(tax):>14}")
    print(f"    - Voluntary SSS         : {peso(voluntary_sss):>14}")
    print(f"    - Other deductions      : {peso(other_deduct):>14}")
    print(f"    -----------------------------------------")
    print(f"    Total Deducted          : {peso(total_employee_deduct):>14}")
    print(f"    NET PAY (take-home)     : {peso(net):>14}")

    if gross > 0:
        print("\n[F] PERCENTAGE OF GROSS")
        print(f"    SSS                     : {(sss/gross)*100:>13.2f}%  -> {peso(sss)}")
        print(f"    PhilHealth              : {(philhealth/gross)*100:>13.2f}%  -> {peso(philhealth)}")
        print(f"    Pag-IBIG                : {(pagibig/gross)*100:>13.2f}%  -> {peso(pagibig)}")
        print(f"    Tax                     : {(tax/gross)*100:>13.2f}%  -> {peso(tax)}")
        if voluntary_sss:
            print(f"    Voluntary SSS           : {(voluntary_sss/gross)*100:>13.2f}%  -> {peso(voluntary_sss)}")
        if other_deduct:
            print(f"    Other Deductions        : {(other_deduct/gross)*100:>13.2f}%  -> {peso(other_deduct)}")
        print(f"    -----------------------------------------")
        print(f"    Total Deducted          : {(total_employee_deduct/gross)*100:>13.2f}%")
        print(f"    NET PAY                 : {(net/gross)*100:>13.2f}%  -> {peso(net)}")

    print("=" * 62)


def _get_tax_bracket(annual_taxable: float) -> str:
    if annual_taxable <= 250000:
        return "Exempt (<=250k)"
    elif annual_taxable <= 400000:
        return "15% (250k-400k)"
    elif annual_taxable <= 800000:
        return "20% + 22.5k (400k-800k)"
    elif annual_taxable <= 2000000:
        return "25% + 102.5k (800k-2M)"
    elif annual_taxable <= 8000000:
        return "30% + 402.5k (2M-8M)"
    else:
        return "35% + 2.2M (>8M)"


def advanced_analytics() -> None:
    if pd is not None:
        _analytics_with_pandas()
    else:
        _analytics_pure_python()


def _analytics_with_pandas() -> None:
    df = load_employees_df()
    if df is None or df.empty:
        print("\nNo employee records found.")
        return

    print("\n" + "=" * 78)
    print("               ADVANCED PAYROLL ANALYTICS (pandas)")
    print("=" * 78)

    n = len(df)
    total_salary = df["salary"].sum()
    total_ot_pay = df["overtime_pay"].sum()
    total_gross = df["gross"].sum()
    total_sss = df["sss"].sum()
    total_ph = df["philhealth"].sum()
    total_pi = df["pagibig"].sum()
    total_mandatory = total_sss + total_ph + total_pi
    total_tax = df["tax_withheld"].sum()
    total_voluntary = df["voluntary_sss"].sum()
    total_other_ded = df["deductions"].sum()
    total_net = df["net"].sum()
    total_er_sss = df["sss_employer"].sum()
    total_er_ec = df["ec_employer"].sum()
    total_er_ph = df["philhealth_employer"].sum()
    total_er_pi = df["pagibig_employer"].sum()
    total_er_contrib = total_er_sss + total_er_ec + total_er_ph + total_er_pi
    total_er_cost = df["employer_cost"].sum()

    print("\n[1] COMPANY-WIDE TOTALS (this month)")
    print(f"    {'Employees':<28}: {n:>20}")
    print(f"    {'Total Basic Salary':<28}: {peso(total_salary):>20}")
    print(f"    {'Total Overtime Pay':<28}: {peso(total_ot_pay):>20}")
    print(f"    {'-' * 28}-{'-' * 20}-")
    print(f"    {'Total GROSS PAY':<28}: {peso(total_gross):>20}")
    print(f"    {'Total Mandatory (EE)':<28}: {peso(total_mandatory):>20}")
    print(f"    {'Total Tax Withheld':<28}: {peso(total_tax):>20}")
    print(f"    {'-' * 28}-{'-' * 20}-")
    print(f"    {'Total NET PAY':<28}: {peso(total_net):>20}")
    print(f"    {'-' * 28}-{'-' * 20}-")
    print(f"    {'Total Employer Contributions':<28}: {peso(total_er_contrib):>20}")
    print(f"    {'TOTAL EMPLOYER COST':<28}: {peso(total_er_cost):>20}")

    avg_tax_rate = (total_tax / total_gross * 100) if total_gross else 0
    avg_net_rate = (total_net / total_gross * 100) if total_gross else 0

    print("\n[2] AVERAGES PER EMPLOYEE")
    print(f"    {'Avg Basic Salary':<28}: {peso(df['salary'].mean()):>20}")
    print(f"    {'Avg Gross Pay':<28}: {peso(df['gross'].mean()):>20}")
    print(f"    {'Avg Tax Withheld':<28}: {peso(df['tax_withheld'].mean()):>20}")
    print(f"    {'Avg Net Pay':<28}: {peso(df['net'].mean()):>20}")
    print(f"    {'Avg Employer Cost':<28}: {peso(df['employer_cost'].mean()):>20}")
    print(f"    {'Avg Tax / Gross':<28}: {avg_tax_rate:>19.2f}%")
    print(f"    {'Avg Net / Gross':<28}: {avg_net_rate:>19.2f}%")

    top_sal = df.loc[df["salary"].idxmax()]
    low_sal = df.loc[df["salary"].idxmin()]
    top_net = df.loc[df["net"].idxmax()]
    low_net = df.loc[df["net"].idxmin()]

    print("\n[3] HIGHEST / LOWEST EARNERS")
    print(f"    {'Highest Basic Salary':<22}: {top_sal['name']:<26} {peso(top_sal['salary'])}")
    print(f"    {'Lowest  Basic Salary':<22}: {low_sal['name']:<26} {peso(low_sal['salary'])}")
    print(f"    {'Highest NET Pay':<22}: {top_net['name']:<26} {peso(top_net['net'])}")
    print(f"    {'Lowest  NET Pay':<22}: {low_net['name']:<26} {peso(low_net['net'])}")

    dept_group = df.groupby("department").agg(
        count=("id", "count"),
        gross=("gross", "sum"),
        tax=("tax_withheld", "sum"),
        net=("net", "sum"),
        er_cost=("employer_cost", "sum"),
    ).sort_index()

    print("\n[4] DEPARTMENT BREAKDOWN")
    print(f"    {'Department':<14}{'Count':>7}{'Avg Gross':>15}{'Avg Tax':>12}"
          f"{'Avg Net':>14}{'Total ER Cost':>18}")
    print("    " + "-" * 78)
    for dept, row in dept_group.iterrows():
        c = int(row["count"])
        print(
            f"    {dept:<14}{c:>7}{peso(row['gross'] / c):>15}"
            f"{peso(row['tax'] / c):>12}{peso(row['net'] / c):>14}"
            f"{peso(row['er_cost']):>18}"
        )

    df["bracket"] = (df["taxable_income"] * 12).apply(_get_tax_bracket)
    bracket_group = df["bracket"].value_counts().sort_index()

    print("\n[5] TAX BRACKET DISTRIBUTION")
    print(f"    {'Bracket':<30}{'Count':>8}{'Share':>10}")
    print("    " + "-" * 48)
    for b, c in bracket_group.items():
        share = (c / n) * 100
        print(f"    {b:<30}{c:>8}{share:>9.1f}%")

    print("\n[6] WHERE THE COMPANY'S MONEY GOES (% of total employer cost)")
    if total_er_cost > 0:
        slices = [
            ("Employee NET pay", total_net),
            ("Employee Tax (BIR)", total_tax),
            ("Employee Contributions", total_mandatory),
            ("Employee Voluntary/Other", total_voluntary + total_other_ded),
            ("Employer Contributions", total_er_contrib),
        ]
        print(f"    {'Category':<30}{'Amount':>18}{'Share':>12}")
        print("    " + "-" * 60)
        for label, amount in slices:
            pct = (amount / total_er_cost) * 100
            print(f"    {label:<30}{peso(amount):>18}{pct:>11.2f}%")
        print("    " + "-" * 60)
        print(f"    {'TOTAL EMPLOYER COST':<30}{peso(total_er_cost):>18}{100.0:>11.2f}%")

    print("\n" + "=" * 78)
    log_action("ADVANCED_ANALYTICS", f"pandas dashboard across {n} employees")


def _analytics_pure_python() -> None:
    rows = load_employees()
    if not rows:
        print("\nNo employee records found.")
        return

    print("\n" + "=" * 78)
    print("               ADVANCED PAYROLL ANALYTICS (pure python)")
    print("=" * 78)

    n = len(rows)
    total_gross = sum(r.get("gross", 0) for r in rows)
    total_net = sum(r.get("net", 0) for r in rows)
    total_tax = sum(r.get("tax_withheld", 0) for r in rows)
    total_er_cost = sum(r.get("employer_cost", 0) for r in rows)

    print(f"    Employees: {n}")
    print(f"    Total Gross: {peso(total_gross)}")
    print(f"    Total Net: {peso(total_net)}")
    print(f"    Total Tax: {peso(total_tax)}")
    print(f"    Total ER Cost: {peso(total_er_cost)}")

    log_action("ADVANCED_ANALYTICS", f"pure-python dashboard across {n} employees")


def generate_payslip_pdf(emp, output_path, company_name=DEFAULT_COMPANY_NAME,
                         company_address=DEFAULT_COMPANY_ADDRESS,
                         title="PAYSLIP", pay_period="") -> bool:
    if not FPDF_AVAILABLE:
        print("fpdf2 not installed - skipping PDF generation.")
        return False

    try:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=False)
        pdf.set_margins(10, 10, 10)
        pdf.add_page()

        NAVY, LIGHT, GRAY, LINE = (31, 56, 100), (234, 239, 247), (110, 110, 110), (190, 198, 210)

        def text(x, y, w, h, s, style="", size=10, color=(0, 0, 0), align="L"):
            pdf.set_xy(x, y)
            pdf.set_font("Helvetica", style, size)
            pdf.set_text_color(*color)
            pdf.cell(w, h, s, align=align)

        def money_table(x, y, w, heading, rows, total_label, total_value):
            row_h = 7
            pdf.set_xy(x, y)
            pdf.set_fill_color(*NAVY)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(w, 8, f"  {heading}", border=0, fill=True)
            y += 8

            pdf.set_draw_color(*LINE)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 10)
            for label, amount in rows:
                pdf.set_xy(x, y)
                pdf.cell(w * 0.55, row_h, f"  {label}", border="LB")
                pdf.cell(w * 0.45, row_h, peso(amount) + "  ", border="RB", align="R")
                y += row_h

            pdf.set_xy(x, y)
            pdf.set_fill_color(*LIGHT)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(w * 0.55, 8, f"  {total_label}", border="LB", fill=True)
            pdf.cell(w * 0.45, 8, peso(total_value) + "  ", border="RB", fill=True, align="R")
            return y + 8

        pdf.set_fill_color(*NAVY)
        pdf.rect(0, 0, 210, 32, style="F")
        text(10, 8, 120, 8, company_name, style="B", size=16, color=(255, 255, 255))
        text(10, 17, 120, 6, company_address, size=9, color=(220, 226, 240))
        text(120, 8, 80, 10, title, style="B", size=22, color=(255, 255, 255), align="R")
        if pay_period:
            text(120, 19, 80, 6, f"Pay Period: {pay_period}", size=9, color=(220, 226, 240), align="R")

        y = 40
        pdf.set_draw_color(*LINE)
        pdf.rect(10, y, 190, 28)
        pdf.set_fill_color(*LIGHT)
        pdf.rect(10, y, 190, 8, style="DF")
        text(12, y + 1, 100, 6, "EMPLOYEE INFORMATION", style="B", size=9, color=NAVY)

        def info(x, y, label, value):
            text(x, y, 30, 6, label, size=9, color=GRAY)
            text(x + 30, y, 60, 6, str(value), style="B", size=10)

        info(12, y + 11, "Employee ID:", emp.get("id", "?"))
        info(12, y + 18, "Name:", emp.get("name", "?"))
        info(108, y + 11, "Department:", emp.get("department", "?"))
        info(108, y + 18, "Date Issued:", datetime.now().strftime("%b %d, %Y"))

        y = 76
        earnings = [("Basic Salary", emp.get("salary", 0)), ("Overtime Pay", emp.get("overtime_pay", 0))]
        deductions = [
            ("SSS", emp.get("sss", 0)),
            ("PhilHealth", emp.get("philhealth", 0)),
            ("Pag-IBIG", emp.get("pagibig", 0)),
            ("Withholding Tax", emp.get("tax_withheld", 0)),
        ]
        if emp.get("voluntary_sss", 0):
            deductions.append(("Voluntary SSS", emp["voluntary_sss"]))
        if emp.get("deductions", 0):
            deductions.append(("Other Deductions", emp["deductions"]))

        total_deductions = sum(a for _, a in deductions)

        end_left = money_table(10, y, 92, "EARNINGS", earnings, "GROSS PAY", emp.get("gross", 0))
        end_right = money_table(108, y, 92, "DEDUCTIONS", deductions, "TOTAL DEDUCTIONS", total_deductions)

        y = max(end_left, end_right) + 8
        pdf.set_fill_color(*NAVY)
        pdf.rect(10, y, 190, 16, style="F")
        text(14, y + 3, 90, 10, "NET PAY", style="B", size=14, color=(255, 255, 255))
        text(100, y + 3, 96, 10, peso(emp.get("net", 0)), style="B", size=16, color=(255, 255, 255), align="R")

        y += 36
        pdf.set_draw_color(*GRAY)
        pdf.line(15, y, 80, y)
        pdf.line(130, y, 195, y)
        text(15, y + 1, 65, 5, "Employee Signature", size=8, color=GRAY, align="C")
        text(130, y + 1, 65, 5, "Authorized Signatory", size=8, color=GRAY, align="C")

        pdf.set_draw_color(*LINE)
        pdf.line(10, 280, 200, 280)
        text(10, 282, 190, 5,
             f"This is a system-generated payslip and is confidential. Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             style="I", size=8, color=GRAY, align="C")

        pdf.output(output_path)
        return True
    except Exception as e:
        print(f"PDF generation failed: {e}")
        return False


def send_payslip_email(to_email, emp, pdf_path=None) -> bool:
    if not DOTENV_AVAILABLE and not os.getenv("SMTP_USER"):
        print("No SMTP credentials configured (missing .env or python-dotenv).")
        return False

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    from_name = os.getenv("SMTP_FROM_NAME", "Payroll Department")

    if not smtp_user or not smtp_pass:
        print("SMTP_USER or SMTP_PASS not set in .env")
        return False

    msg = EmailMessage()
    msg["Subject"] = f"Payslip - {emp.get('name', 'Employee')}"
    msg["From"] = f"{from_name} <{smtp_user}>"
    msg["To"] = to_email
    msg["Reply-To"] = smtp_user
    msg.set_content(
        f"Hi {emp.get('name', 'Employee')},\n\n"
        f"Gross Pay: {peso(emp.get('gross', 0))}\n"
        f"Tax: {peso(emp.get('tax_withheld', 0))}\n"
        f"Net Pay: {peso(emp.get('net', 0))}\n"
    )

    if pdf_path and os.path.isfile(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        msg.add_attachment(pdf_data, maintype="application", subtype="pdf",
                           filename=os.path.basename(pdf_path))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"[OK] Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"[X] Failed to send email: {e}")
        return False


def email_payslip_flow() -> None:
    print("\n---------- EMAIL PAYSLIP ----------")
    rows = load_employees()
    if not rows:
        print("No employee records found.")
        return

    emp_id = input("Enter Employee ID: ").strip()
    if not emp_id:
        print("Employee ID cannot be empty.")
        return

    employee = next((r for r in rows if r["id"].lower() == emp_id.lower()), None)
    if employee is None:
        print("Employee ID not found.")
        return

    to_email = input("Send payslip to (email): ").strip()
    if "@" not in to_email:
        print("Invalid email address.")
        return

    print_payslip(employee)
    period = input("Pay period (e.g., Oct 1-15, 2025) [blank for none]: ").strip()

    pdf_path = os.path.join(PAYSLIP_DIR, f"payslip_{employee['id']}.pdf")
    pdf_ok = generate_payslip_pdf(employee, pdf_path, pay_period=period)
    if pdf_ok:
        print(f"PDF saved to: {pdf_path}")

    ok = send_payslip_email(to_email, employee, pdf_path if pdf_ok else None)
    log_action("EMAIL_PAYSLIP", f"{employee['name']} -> {to_email} ({'OK' if ok else 'FAILED'})")


def generate_payslip_pdf_flow() -> None:
    print("\n---------- GENERATE PDF PAYSLIP ----------")
    rows = load_employees()
    if not rows:
        print("No employee records found.")
        return

    emp_id = input("Enter Employee ID: ").strip()
    if not emp_id:
        print("Employee ID cannot be empty.")
        return

    employee = next((r for r in rows if r["id"].lower() == emp_id.lower()), None)
    if employee is None:
        print("Employee ID not found.")
        return

    period = input("Pay period (e.g., Oct 1-15, 2025) [blank for none]: ").strip()
    pdf_path = os.path.join(PAYSLIP_DIR, f"payslip_{employee['id']}.pdf")
    if generate_payslip_pdf(employee, pdf_path, pay_period=period):
        print(f"[OK] PDF generated: {pdf_path}")
        log_action("PDF_PAYSLIP", f"{employee['name']} -> {pdf_path}")
    else:
        print("[X] PDF generation failed.")


def batch_generate_all_payslips() -> None:
    print("\n---------- BATCH GENERATE ALL PAYSLIPS ----------")
    rows = load_employees()
    if not rows:
        print("No employee records found.")
        return

    period = input("Pay period (e.g., Oct 1-15, 2025) [blank for none]: ").strip()
    confirm = input(f"Generate PDF payslips for ALL {len(rows)} employees? (y/n): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Cancelled.")
        return

    os.makedirs(PAYSLIP_DIR, exist_ok=True)
    ok, failed = 0, 0
    for emp in rows:
        pdf_path = os.path.join(PAYSLIP_DIR, f"payslip_{emp['id']}.pdf")
        if generate_payslip_pdf(emp, pdf_path, pay_period=period):
            ok += 1
            print(f"  [OK]  {emp['name']:<28} -> {os.path.basename(pdf_path)}")
        else:
            failed += 1
            print(f"  [X]   {emp['name']:<28} -> FAILED")

    print(f"\nDone. {ok} generated, {failed} failed.")
    print(f"All PDFs saved to: {PAYSLIP_DIR}")
    log_action("BATCH_PDF", f"{ok} OK, {failed} failed")


def export_excel() -> None:
    if pd is None:
        print("pandas not installed - cannot export Excel.")
        return

    df = load_employees_df()
    if df.empty:
        print("No data to export.")
        return

    os.makedirs(EXPORT_DIR, exist_ok=True)

    filename = f"payroll_export_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    output = os.path.join(EXPORT_DIR, filename)

    try:
        with pd.ExcelWriter(output) as writer:
            df.to_excel(writer, sheet_name="Employees", index=False)

            dept = df.groupby("department").agg(
                count=("id", "count"),
                total_gross=("gross", "sum"),
                total_net=("net", "sum"),
                total_tax=("tax_withheld", "sum"),
                total_er_cost=("employer_cost", "sum"),
            )
            dept.to_excel(writer, sheet_name="By Department")

            df["bracket"] = (df["taxable_income"] * 12).apply(_get_tax_bracket)
            brackets = df["bracket"].value_counts().sort_index().to_frame("count")
            brackets.to_excel(writer, sheet_name="Tax Brackets")

        print(f"[OK] Excel exported: {output}")
        log_action("EXPORT_EXCEL", output)
    except PermissionError:
        print(f"Could not write {output} - the file may be open in Excel.")
        log_action("EXPORT_EXCEL_FAILED", "file locked")
    except Exception as e:
        print(f"Export failed: {e}")
        log_action("EXPORT_EXCEL_FAILED", str(e))


def add_employee() -> None:
    print("\n---------- ADD EMPLOYEE ----------")
    name = get_text("Employee Name: ")
    department = get_text("Department: ")
    salary = get_number("Basic Salary: P")
    overtime_hours = get_number("Overtime Hours: ")
    deductions = get_number("Other Deductions (non-statutory): P")
    voluntary_sss = get_number("Voluntary SSS in excess of mandatory (P0 if none): P")

    rows = load_employees()
    new_name = name.strip().lower()

    duplicates = [r for r in rows if str(r.get("name", "")).strip().lower() == new_name]

    if duplicates:
        print(f"\n[!] WARNING: Duplicate name detected!")
        for d in duplicates:
            marker = get_department_marker(d.get("department", ""))
            print(f"     - ID: {d.get('id', '?'):<16} Dept: {marker} {d.get('department', '?'):<12} Net: {peso(d.get('net', 0))}")

        confirm = input("\nDo you want to duplicate the name? (y/n): ").strip().lower()
        if confirm not in ("y", "yes"):
            print("\n[X] Add cancelled.")
            log_action("ADD_CANCELLED", f"Duplicate name '{name}'")
            return

        print("\n--- Choose Department for the duplicated name ---")
        dept_list = list(DEPARTMENT_MARKERS.keys())
        for i, dept in enumerate(dept_list, start=1):
            print(f"  {i}. {DEPARTMENT_MARKERS[dept]['marker']} {dept}")
        print(f"  {len(dept_list) + 1}. Other (type your own)")

        while True:
            choice = input("Enter choice number: ").strip()
            if not choice.isdigit():
                print("Please enter a valid number.")
                continue
            choice_num = int(choice)
            if 1 <= choice_num <= len(dept_list):
                department = dept_list[choice_num - 1]
                break
            elif choice_num == len(dept_list) + 1:
                department = get_text("Enter department name: ")
                break
            else:
                print(f"Invalid choice. Please select 1-{len(dept_list) + 1}.")

    new_id = generate_employee_id(department)
    existing_ids = {r["id"].lower() for r in rows}
    while new_id.lower() in existing_ids:
        new_id = generate_employee_id(department)

    employee = Employee(name, department, salary, overtime_hours, deductions, voluntary_sss, emp_id=new_id)

    try:
        employee.save_to_csv(CSV_FILE)
    except PermissionError:
        print(f"Could not write {CSV_FILE}.")
        log_action("ADD_FAILED", f"{name}: file locked")
        return

    marker = get_department_marker(department)
    print(f"\nEmployee added successfully! {marker}")
    print_payslip(employee.to_dict())
    log_action("ADD", f"{employee.name} (ID {employee.id}, dept {employee.department})")


def view_payroll() -> None:
    rows = load_employees()
    if not rows:
        print("\nNo employee records found.")
        return
    print_table(rows, title="Payroll Report")
    total_employer = sum(r.get("employer_cost", 0) for r in rows)
    print(f"\nTotal Employees: {len(rows)}")
    print(f"Total Employer Cost (this month): {peso(total_employer)}")
    log_action("VIEW_PAYROLL", f"{len(rows)} employees displayed")
    advanced_analytics()


def sort_employees() -> None:
    print("\n---------- SORT EMPLOYEES ----------")
    rows = load_employees()
    if not rows:
        print("No employee records found.")
        return

    print("Sort by which field?")
    print("  1. Name (A-Z)")
    print("  2. Department (A-Z)")
    print("  3. Salary (Highest First)")
    print("  0. Cancel")

    choice = input("Choice: ").strip()
    if choice == "0":
        print("Cancelled.")
        return

    if choice == "1":
        rows = merge_sort(rows, "name"); title = "Sorted by Name (A-Z)"
    elif choice == "2":
        rows = merge_sort(rows, "department"); title = "Sorted by Department (A-Z)"
    elif choice == "3":
        rows = merge_sort(rows, "salary", reverse=True); title = "Sorted by Salary (Highest First)"
    else:
        print("Invalid choice.")
        return

    print_table(rows, title=title)
    log_action("SORT", title)


def show_top_5() -> None:
    rows = load_employees()
    if not rows:
        print("\nNo employee records found.")
        return

    heap = MaxHeap()
    heap.build_heap(rows)

    print("\n========================================")
    print("       TOP 5 HIGHEST-PAID EMPLOYEES")
    print("========================================")
    for i in range(min(5, len(rows))):
        employee = heap.extract_max()
        marker = get_department_marker(employee["department"])
        print(f"{i + 1}. {marker} {employee['name']} - {employee['department']} - Salary: {peso(employee['salary'])}")
    print("========================================")
    log_action("TOP5", f"top {min(5, len(rows))}")


def search_employee() -> None:
    rows = load_employees()
    if not rows:
        print("\nNo employee records found.")
        return
    search = input("Enter Employee ID or Name: ").strip().lower()
    if not search:
        print("Search cannot be empty.")
        return

    found = None
    for emp in rows:
        if search == emp["id"].lower() or search == emp["name"].lower():
            found = emp
            break

    if not found:
        print("\nEmployee not found.")
        log_action("SEARCH", f"query='{search}' -> 0 matches")
        return

    print_payslip(found)
    _print_deduction_summary(found)
    log_action("SEARCH", f"query='{search}' -> found {found['name']}")


def update_salary() -> None:
    print("\n---------- UPDATE SALARY ----------")
    rows = load_employees()
    if not rows:
        print("No employee records found.")
        return

    emp_id = input("Enter Employee ID to update salary: ").strip()
    if not emp_id:
        print("Employee ID cannot be empty.")
        return

    employee = next((r for r in rows if str(r.get("id", "")).lower() == emp_id.lower()), None)
    if employee is None:
        print("Employee ID not found.")
        log_action("UPDATE_SALARY_FAILED", f"ID {emp_id} not found")
        return

    marker = get_department_marker(employee.get("department", ""))
    print(f"\nMatched record:")
    print(f"  ID         : {employee.get('id', '?')}")
    print(f"  Name       : {employee.get('name', '?')}")
    print(f"  Department : {marker} {employee.get('department', '?')}")
    print(f"  Salary     : {peso(employee.get('salary', 0))}")
    print(f"  Net Pay    : {peso(employee.get('net', 0))}")

    new_salary = get_number("\nEnter New Basic Salary: P")
    confirm = input(f"Update ONLY this record (ID {employee['id']}) to {peso(new_salary)}? (y/n): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Salary update cancelled.")
        log_action("UPDATE_SALARY_CANCELLED", f"{employee['name']}")
        return

    updated = Employee(
        name=employee["name"], department=employee["department"],
        salary=new_salary, overtime=float(employee.get("overtime", 0)),
        deductions=float(employee.get("deductions", 0)),
        voluntary_sss=float(employee.get("voluntary_sss", 0)),
        emp_id=employee["id"],
    ).to_dict()

    updated_count = 0
    for index, row in enumerate(rows):
        if str(row.get("id", "")).lower() == emp_id.lower():
            rows[index] = updated
            updated_count += 1
            break

    if updated_count == 0:
        print("Unexpected: record disappeared.")
        return

    try:
        rewrite_csv(rows)
    except PermissionError:
        print(f"Could not write {CSV_FILE}.")
        log_action("UPDATE_SALARY_FAILED", f"{employee['name']}: file locked")
        return

    print("\nSalary updated successfully! (1 record only)")
    print_payslip(updated)
    log_action("UPDATE_SALARY", f"{employee['name']}: {employee.get('salary', 0)} -> {new_salary}")


def delete_employee() -> None:
    rows = load_employees()
    if not rows:
        print("\nNo employee records found.")
        return

    emp_id = input("Enter Employee ID to delete: ").strip()
    if not emp_id:
        print("Employee ID cannot be empty.")
        return

    matches = [r for r in rows if r["id"].lower() == emp_id.lower()]
    if not matches:
        print("Employee ID not found.")
        log_action("DELETE_FAILED", f"ID {emp_id} not found")
        return

    target_name = matches[0].get("name", "?")
    print(f"About to delete: {target_name} (ID {emp_id})")
    confirm = input("Confirm? (y/n): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Cancelled.")
        return

    filtered = [r for r in rows if r["id"].lower() != emp_id.lower()]
    try:
        rewrite_csv(filtered)
    except PermissionError:
        print(f"Could not write {CSV_FILE}.")
        return

    print(f"Deleted employee {emp_id}.")
    log_action("DELETE", f"{target_name} (ID {emp_id})")


def print_menu() -> None:
    print("\n========================================")
    print("        EMPLOYEE PAYROLL SORTER")
    print("========================================")
    print("1.  Add Employee")
    print("2.  View Payroll (with analytics)")
    print("3.  Sort Employees")
    print("4.  Top 5 Highest-Paid Employees")
    print("5.  Search Employee")
    print("6.  Delete Employee")
    print("7.  Update Salary")
    print("8.  Restore Default Employees")
    print("9.  Linear Search (by field)")
    print("10. View History Log")
    print("11. Clear History Log")
    print("12. Show Department Markers")
    print("13. Generate PDF Payslip")
    print("14. Email Payslip")
    print("15. Export Excel Report")
    print("16. Batch Generate All Payslips")
    print("17. Exit")


def main() -> None:
    seed_default_employees()
    log_action("SESSION_START", "Program started")

    actions = {
        "1": add_employee,
        "2": view_payroll,
        "3": sort_employees,
        "4": show_top_5,
        "5": search_employee,
        "6": delete_employee,
        "7": update_salary,
        "8": restore_default_employees,
        "9": linear_search_menu,
        "10": view_history_log,
        "11": clear_history_log,
        "12": show_department_markers,
        "13": generate_payslip_pdf_flow,
        "14": email_payslip_flow,
        "15": export_excel,
        "16": batch_generate_all_payslips,
    }

    while True:
        print_menu()
        choice = input("Choose an option: ").strip()

        if choice == "17":
            print("\nThank you for using Employee Payroll Sorter!")
            log_action("SESSION_END", "Program exited normally")
            break

        action = actions.get(choice)
        if action:
            action()
        else:
            print("\nInvalid choice. Please select 1-17.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_action("SESSION_END", "Interrupted by Ctrl+C")
        print("\nInterrupted. Goodbye!")