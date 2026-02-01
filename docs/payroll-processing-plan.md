# Payroll Processing Plan - NGS (Jan 2026)

## Task Overview
Process payroll for 2 employees, generate documents, and update Obsidian

## Sequential Steps

### Step 1: Data Validation
- [ ] Validate payroll data (salary, tax, deductions)
- [ ] Check for duplicate entries
- [ ] Verify calculations (net pay = gross - tax - soc_sec)

### Step 2: Database Operations
- [ ] Insert payroll records into ngs_finance.db
- [ ] Table: `payroll` or `expenses` (doc_type='expense')
- [ ] Mark as salary expense for Jan 2026

### Step 3: PDF Generation
- [ ] Create payslip PDF for วราวุธ (director)
- [ ] Create payslip PDF for วงศธร (employee)
- [ ] Template: Use NGS document template
- [ ] Save to: 2-Areas/NGS/Documents/Payroll/2026/01/

### Step 4: Obsidian Updates
- [ ] Update monthly_bills_dashboard.md (add salary expenses)
- [ ] Update ngs_finance_dashboard.md (recalculate totals)
- [ ] Create/Update employee payroll tracking

### Step 5: Verification & Git
- [ ] Verify all data inserted correctly
- [ ] Check PDFs generated successfully
- [ ] Git commit all changes

## Parallel Workstreams

### Stream A: Database + PDF (Worker 1)
- Insert payroll data
- Generate PDF payslips

### Stream B: Obsidian Updates (Worker 2)
- Update bills dashboard
- Update finance dashboard
- Update employee records

### Stream C: Verification (Worker 3)
- Verify database entries
- Verify PDFs
- Git commit

## Validation Checklist
- [ ] Database: 2 payroll records inserted
- [ ] PDFs: 2 payslips generated
- [ ] Obsidian: 2+ files updated
- [ ] Git: All changes committed
- [ ] Totals match: 60,000 + 60,000 = 120,000 gross

## Success Criteria
1. Payroll data in database ✓
2. Payslip PDFs created ✓
3. Obsidian dashboards updated ✓
4. Git committed ✓
