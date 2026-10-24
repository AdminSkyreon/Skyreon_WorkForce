export type Role = "super_admin" | "admin" | "employee";

export type User = {
  id: string;
  email: string;
  role: Role;
  is_active: boolean;
  must_change_password: boolean;
  employee_id: string | null;
  name: string | null;
  is_people_manager?: boolean;
  is_project_manager?: boolean;
};

export function isStaff(role?: Role | null) {
  return role === "admin" || role === "super_admin";
}

export type Employee = {
  id: string;
  user_id: string;
  name: string;
  phone: string;
  address: string;
  email: string;
  employee_code: string;
  designation: string;
  department: string;
  joining_date: string;
  reporting_manager_id: string | null;
  reporting_manager_name?: string | null;
  location_id: string | null;
  location_name: string | null;
  hourly_cost_rate: string;
  monthly_salary?: string;
  hourly_pay_rate?: string;
  pay_type: "fixed" | "hourly";
  engagement?: "staff" | "contractor";
  allow_leave?: boolean;
  contract_monthly_fee?: string;
  status: "active" | "inactive";
  is_active_user: boolean;
};

export type NamedOption = { id: string; name: string; is_active: boolean };

export type CompanyMonth = {
  year: number;
  month: number;
  period_label: string;
  received: string;
  staff_paid: string;
  contractors_paid: string;
  claims_paid: string;
  compliance: string;
  other_opex: string;
  leftover: string;
  invoiced_not_cash: string;
  receipts_against_earlier?: string;
  salaries_calculated: string;
  contractors_calculated: string;
};

export type ProjectPayment = {
  id: string;
  invoice_id?: string | null;
  invoice_no?: string | null;
  project_id: string;
  project_name: string | null;
  year: number;
  month: number;
  amount: string;
  received_date: string;
  note: string;
  against_earlier_invoice?: boolean;
};

export type ProjectInvoice = {
  id: string;
  invoice_no: string;
  project_id: string;
  project_name: string | null;
  invoice_date: string;
  year: number;
  month: number;
  taxable_amount: string;
  gst_percent: string;
  gst_amount: string;
  amount: string;
  received: string;
  outstanding: string;
  status: "open" | "partial" | "paid" | string;
  note: string;
};

export type InvoiceSuggest = {
  project_id: string;
  project_name: string | null;
  year: number;
  month: number;
  approved_hours: string;
  bill_rate: string | null;
  taxable_amount: string;
  gst_percent: string;
  gst_amount: string;
  total_amount: string;
  detail: string;
};

export type SalaryPayment = {
  id: string;
  employee_id: string;
  employee_name: string | null;
  year: number;
  month: number;
  amount: string;
  paid_date: string;
  reference: string;
  paid: boolean;
};

export type ContractorLine = {
  employee_id: string;
  name: string;
  employee_code: string;
  department: string;
  pay_type: string;
  hours: string;
  calculated: string;
  amount: string;
  deduction: string;
  paid: boolean;
  paid_date: string | null;
  reference: string;
};

export type ContractorRegister = {
  year: number;
  month: number;
  period_label: string;
  lines: ContractorLine[];
  total_calculated: string;
  total_paid: string;
};

export type VendorBill = {
  id: string;
  vendor_name: string;
  category: string;
  amount: string;
  gst_amount: string;
  bill_date: string;
  paid_date: string | null;
  year: number;
  month: number;
  note: string;
  recurring: boolean;
  status: "draft" | "approved" | "paid";
};

export type Job = {
  id: string;
  title: string;
  department: string;
  location_id?: string | null;
  is_open: boolean;
  opened_on: string;
  note: string;
  applicants: { id: string; name: string; email: string; stage: string; note: string }[];
};

export type EmployeeDocument = { requirement_id: string; name: string; provided: boolean; note: string };
export type AttendanceDay = { id: string; employee_id: string; employee_name: string | null; work_date: string; mark: string; note: string };
export type ReviewCycle = { id: string; name: string; start_date: string; end_date: string; is_open: boolean };
export type Review = { id: string; cycle_id: string; employee_id: string; employee_name: string | null; summary: string; acknowledged: boolean };
export type CompanyAsset = { id: string; name: string; asset_tag: string; category: string; status: string; assigned_to_id: string | null; assigned_to_name: string | null; acknowledged: boolean; note: string };
export type Location = {
  id: string;
  name: string;
  code: string;
  city: string;
  country: string;
  is_active: boolean;
};

export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type ProjectFinancials = {
  total_hours: string;
  cost: string;
  revenue: string;
  profit: string;
  margin_percent: string;
  budget_consumed_percent: string;
};

export type Project = {
  id: string;
  name: string;
  client_name: string;
  project_code: string;
  description: string;
  manager_id: string;
  manager_name: string | null;
  start_date: string;
  end_date: string | null;
  status: "planned" | "active" | "on_hold" | "completed";
  contract_type: "fixed" | "time_and_material";
  revenue_amount: string;
  revenue_currency: string;
  budgeted_hours: string;
  members: Employee[];
  financials: ProjectFinancials | null;
};

export type Task = {
  id: string;
  project_id: string;
  project_name: string | null;
  title: string;
  description: string;
  priority: "low" | "medium" | "high";
  estimated_hours: string;
  due_date: string | null;
  assignee_id: string | null;
  assignee_name: string | null;
  status: "not_started" | "in_progress" | "paused" | "completed";
  logged_seconds: number;
  remaining_seconds: number;
};

export type RunningTimer = {
  running: boolean;
  task_id: string | null;
  task_title: string | null;
  project_name: string | null;
  entry_id: string | null;
  started_at: string | null;
  remaining_seconds: number;
  estimated_seconds: number;
  logged_seconds: number;
  server_time: string;
  is_overtime: boolean;
};

export type Timesheet = {
  id: string | null;
  employee_id: string;
  employee_name: string | null;
  week_start: string;
  status: "draft" | "submitted" | "approved" | "rejected";
  comment: string;
  rows: {
    task_id: string;
    project_id: string;
    project_name: string;
    task_title: string;
    days: {
      date: string;
      hours: string;
      is_manual: boolean;
      is_holiday: boolean;
      is_weekend: boolean;
      is_leave: boolean;
      exceeds_12h: boolean;
    }[];
  }[];
  daily_totals: string[];
  weekly_total: string;
  warnings: string[];
  locked: boolean;
  extra_work_pending_count?: number;
};

export type ExtraWorkDay = {
  id: string;
  employee_id: string;
  employee_name: string | null;
  work_date: string;
  hours: string;
  kind: "weekend" | "holiday";
  status: "pending" | "approved" | "rejected";
  settlement: "comp_off" | "extra_pay" | null;
  comp_off_days: string;
  extra_pay_amount: string;
  payroll_year: number | null;
  payroll_month: number | null;
  comment: string;
};

export type ExtraWorkDefaults = {
  comp_off_days: string;
  extra_pay_amount: string;
};

export type Holiday = {
  id: string;
  name: string;
  date: string;
  location_id: string | null;
  location_name: string | null;
};

export type PayrollDetails = {
  employee_id: string;
  employee_name: string | null;
  currency: string;
  basic_salary: string;
  hra: string;
  allowances: string;
  tax_percent: string;
  pf_percent: string;
  professional_tax: string;
  hourly_pay_rate: string;
  other_deductions: string;
  bonus?: string;
  reimbursements?: string;
};

export type PayrollLine = {
  employee_id: string;
  name: string;
  employee_code: string;
  location_name: string | null;
  department: string;
  currency: string;
  pay_type: "fixed" | "hourly";
  hourly_rate: string;
  hours: string;
  leave_days: string;
  lwp_days: string;
  reimbursements: string;
  bonus?: string;
  extra_work_pay?: string;
  lwp_amount: string;
  paid_leave_pay: string;
  basic_salary: string;
  hra: string;
  allowances: string;
  time_pay: string;
  tax_percent: string;
  tax_amount: string;
  pf_amount: string;
  professional_tax: string;
  other_deductions: string;
  gross_pay: string;
  total_deductions: string;
  net_pay: string;
  has_details: boolean;
};

export type PayrollRegister = {
  year: number;
  month: number;
  period_label: string;
  location_name: string | null;
  lines: PayrollLine[];
  total_hours: string;
  total_leave_days: string;
  total_gross: string;
  total_tax: string;
  total_pay: string;
  closed: boolean;
};

export type LeaveType = {
  id: string;
  name: string;
  code: string;
  annual_allocation_days: number;
  is_unpaid?: boolean;
  accrual_mode: "lump" | "monthly";
  days_per_month: string;
};

export type Reimbursement = {
  id: string;
  employee_id: string;
  employee_name: string | null;
  project_id: string | null;
  project_name: string | null;
  amount: string;
  category: string;
  spend_date: string;
  note: string;
  status: "submitted" | "approved" | "rejected" | "cancelled";
  comment: string;
  paid_separately?: boolean;
};

export type ProjectBilling = {
  id: string;
  project_id: string;
  project_name: string | null;
  year: number;
  month: number;
  amount: string | null;
  note: string;
  missing: boolean;
};

export type FinanceMonth = {
  year: number;
  month: number;
  period_label: string;
  total_billing: string;
  total_cost: string;
  total_margin: string;
  projects: {
    project_id: string;
    project_name: string;
    client_name: string;
    manager_id: string | null;
    manager_name: string | null;
    billing: string;
    cost: string;
    margin: string;
  }[];
};

export type FinanceYearProject = {
  project_id: string;
  project_name: string;
  client_name: string;
  invoiced: string;
  received: string;
  cost: string;
  profit: string;
};

export type FinanceYearManager = {
  manager_id: string | null;
  manager_name: string;
  invoiced: string;
  received: string;
  cost: string;
  profit: string;
  projects: FinanceYearProject[];
};

export type FinanceYearMonth = {
  month: number;
  label: string;
  invoiced: string;
  received: string;
  cost: string;
  profit: string;
};

export type FinanceYear = {
  year: number;
  invoiced: string;
  received: string;
  cost: string;
  profit: string;
  cash_leftover: string;
  managers: FinanceYearManager[];
  months: FinanceYearMonth[];
};

export type AuditRow = {
  id: string;
  actor_email: string;
  actor_role: string;
  action: string;
  entity_type: string;
  entity_id: string;
  summary: string;
  before_json: string;
  after_json: string;
  created_at: string;
};

export type AdminAccount = {
  id: string;
  email: string;
  is_active: boolean;
  name: string | null;
};

export type CompanyProfile = {
  legal_name: string;
  address: string;
  phone: string;
  website: string;
  signatory_name: string;
  signatory_title: string;
  has_signature: boolean;
};

export type LeaveRequest = {
  id: string;
  employee_id: string;
  employee_name: string | null;
  leave_type_id: string;
  leave_type_name: string | null;
  start_date: string;
  end_date: string;
  is_half_day: boolean;
  days: string;
  reason: string;
  status: "pending" | "approved" | "rejected" | "cancelled";
  reviewer_id: string | null;
  comment: string;
};

export type LeaveBalance = {
  leave_type_id: string;
  leave_type_name: string;
  allocated: string;
  used: string;
  pending: string;
  available: string;
};

export type Notification = {
  id: string;
  type: string;
  title: string;
  body: string;
  is_read: boolean;
  link: string | null;
  created_at: string;
};

export type AdminDashboard = {
  active_employees: number;
  active_projects: number;
  pending_timesheets: number;
  pending_leaves: number;
  hours_this_week: string;
  cost_this_week: string;
  revenue_active_projects: string;
  project_financials: { id: string; name: string; hours: number; cost: number; revenue: number; profit: number }[];
  pending_claims: number;
  missing_billing: number;
};

export type EmployeeDashboard = {
  open_tasks: number;
  hours_this_week: string;
  leave_balances: LeaveBalance[];
  running_task_id: string | null;
  running_task_title: string | null;
  timesheet_status: "draft" | "submitted" | "approved" | "rejected";
  project_count: number;
  is_people_manager: boolean;
  is_project_manager: boolean;
  pending_team_leaves: number;
  pending_team_claims: number;
  pending_team_timesheets: number;
  missing_billing: number;
};
