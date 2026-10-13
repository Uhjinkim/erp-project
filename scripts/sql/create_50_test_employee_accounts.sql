-- Update existing test employees created by the original version of this file.
-- This file now updates existing rows only: no employees/accounts are created.
-- Target: employee910001@example.invalid through employee910050@example.invalid.
-- Changes persons.birth_date and employees.hire_date in one transaction.
-- Fixed dates use 2026-10-08 as reference: 46 hire ages 22-29, plus career hires
-- 910027-910030 aged 32/34/36/38. These are test fixtures, not business policies.
-- Accounts, passwords, roles, departments, positions and emp_history are untouched.
-- Historical assignment scenarios need separate emp_history fixtures.
--
-- Run only against the confirmed development database with write authorization:
--   psql -f scripts/sql/create_50_test_employee_accounts.sql
-- The default execution commits. To preview without saving changes:
--   psql -v preview=true -f scripts/sql/create_50_test_employee_accounts.sql

\set ON_ERROR_STOP on
\if :{?preview}
\else
\set preview false
\endif

BEGIN;
SET LOCAL search_path TO public;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

CREATE TEMP TABLE employee_date_fixture (
    emp_no integer PRIMARY KEY,
    position_code varchar(20) NOT NULL,
    birth_date date NOT NULL,
    hire_date date NOT NULL
) ON COMMIT DROP;

INSERT INTO employee_date_fixture (emp_no, position_code, birth_date, hire_date)
VALUES
    (910001, 'MANAGER', DATE '1989-01-13', DATE '2012-03-01'),
    (910002, 'STAFF', DATE '2001-10-28', DATE '2025-12-31'),
    (910003, 'STAFF', DATE '2000-10-12', DATE '2026-01-01'),
    (910004, 'STAFF', DATE '1999-11-24', DATE '2026-03-01'),
    (910005, 'DIRECTOR', DATE '1978-11-06', DATE '2006-03-01'),
    (910006, 'SENIOR', DATE '1991-02-19', DATE '2019-07-01'),
    (910007, 'STAFF', DATE '1996-03-05', DATE '2025-08-01'),
    (910008, 'STAFF', DATE '2000-03-19', DATE '2022-09-01'),
    (910009, 'STAFF', DATE '2000-04-01', DATE '2023-10-01'),
    (910010, 'STAFF', DATE '2000-04-15', DATE '2024-11-01'),
    (910011, 'MANAGER', DATE '1987-11-27', DATE '2013-07-01'),
    (910012, 'STAFF', DATE '1995-05-12', DATE '2022-01-01'),
    (910013, 'STAFF', DATE '1995-05-26', DATE '2023-02-01'),
    (910014, 'STAFF', DATE '1995-06-07', DATE '2024-03-01'),
    (910015, 'STAFF', DATE '1995-06-21', DATE '2025-04-01'),
    (910016, 'SENIOR', DATE '1998-10-03', DATE '2021-08-01'),
    (910017, 'STAFF', DATE '1999-07-18', DATE '2023-06-01'),
    (910018, 'STAFF', DATE '2000-05-26', DATE '2024-07-01'),
    (910019, 'STAFF', DATE '2000-06-09', DATE '2025-08-01'),
    (910020, 'STAFF', DATE '1996-06-23', DATE '2022-09-01'),
    (910021, 'SENIOR', DATE '1991-01-04', DATE '2018-04-01'),
    (910022, 'STAFF', DATE '1996-07-20', DATE '2024-11-01'),
    (910023, 'STAFF', DATE '1996-08-02', DATE '2025-12-01'),
    (910024, 'STAFF', DATE '1999-08-16', DATE '2022-01-01'),
    (910025, 'STAFF', DATE '1999-08-30', DATE '2023-02-01'),
    (910026, 'MANAGER', DATE '1990-03-13', DATE '2014-09-01'),
    (910027, 'STAFF', DATE '1992-09-24', DATE '2025-04-01'),
    (910028, 'STAFF', DATE '1987-10-08', DATE '2022-05-01'),
    (910029, 'STAFF', DATE '1986-10-21', DATE '2023-06-01'),
    (910030, 'STAFF', DATE '1985-11-03', DATE '2024-07-01'),
    (910031, 'SENIOR', DATE '1990-08-17', DATE '2020-05-01'),
    (910032, 'STAFF', DATE '1999-12-02', DATE '2022-09-01'),
    (910033, 'STAFF', DATE '1999-12-15', DATE '2023-10-01'),
    (910034, 'STAFF', DATE '1999-12-29', DATE '2024-11-01'),
    (910035, 'STAFF', DATE '2000-01-11', DATE '2025-12-01'),
    (910036, 'SENIOR', DATE '1994-11-20', DATE '2021-01-01'),
    (910037, 'STAFF', DATE '1995-12-04', DATE '2023-02-01'),
    (910038, 'MANAGER', DATE '1987-11-17', DATE '2016-02-01'),
    (910039, 'STAFF', DATE '1995-12-30', DATE '2025-04-01'),
    (910040, 'STAFF', DATE '2000-01-12', DATE '2022-05-01'),
    (910041, 'SENIOR', DATE '1995-01-25', DATE '2018-06-01'),
    (910042, 'STAFF', DATE '2000-02-08', DATE '2024-07-01'),
    (910043, 'STAFF', DATE '2000-02-22', DATE '2025-08-01'),
    (910044, 'STAFF', DATE '1996-03-07', DATE '2022-09-01'),
    (910045, 'STAFF', DATE '1996-03-20', DATE '2023-10-01'),
    (910046, 'SENIOR', DATE '1990-07-04', DATE '2019-02-01'),
    (910047, 'STAFF', DATE '1996-04-16', DATE '2025-12-01'),
    (910048, 'STAFF', DATE '1999-04-30', DATE '2022-01-01'),
    (910049, 'STAFF', DATE '2002-12-12', DATE '2026-09-01'),
    (910050, 'STAFF', DATE '2001-12-25', DATE '2026-10-01');

SELECT employee.emp_no
FROM employees AS employee
JOIN employee_date_fixture AS fixture USING (emp_no)
JOIN persons AS person USING (person_id)
ORDER BY employee.emp_no
FOR UPDATE OF employee, person;

DO $validate_targets$
BEGIN
    IF (
        SELECT count(*)
        FROM employee_date_fixture AS fixture
        JOIN employees AS employee USING (emp_no)
        JOIN persons AS person USING (person_id)
        JOIN accounts_users AS account USING (emp_no)
        WHERE employee.email = format('employee%s@example.invalid', fixture.emp_no)
          AND account.email = employee.email
          AND employee.position_code = fixture.position_code
          AND fixture.hire_date >= (fixture.birth_date + INTERVAL '20 years')::date
          AND fixture.hire_date <= DATE '2026-10-08'
          AND NOT EXISTS (
              SELECT 1 FROM employees AS other
              WHERE other.person_id = employee.person_id AND other.emp_no <> employee.emp_no
          )
    ) <> 50 THEN
        RAISE EXCEPTION 'Expected 50 matching test employees/accounts with original positions and unshared persons; no changes applied';
    END IF;
END
$validate_targets$;

UPDATE persons AS person
SET birth_date = fixture.birth_date
FROM employees AS employee
JOIN employee_date_fixture AS fixture USING (emp_no)
WHERE person.person_id = employee.person_id
  AND person.birth_date IS DISTINCT FROM fixture.birth_date;

UPDATE employees AS employee
SET hire_date = fixture.hire_date
FROM employee_date_fixture AS fixture
WHERE employee.emp_no = fixture.emp_no
  AND employee.hire_date IS DISTINCT FROM fixture.hire_date;

DO $validate_result$
BEGIN
    IF EXISTS (
        SELECT 1 FROM employees AS employee
        JOIN employee_date_fixture AS fixture USING (emp_no)
        JOIN persons AS person USING (person_id)
        WHERE employee.hire_date IS DISTINCT FROM fixture.hire_date
           OR person.birth_date IS DISTINCT FROM fixture.birth_date
    ) THEN
        RAISE EXCEPTION 'Date update validation failed; no changes will be committed';
    END IF;
END
$validate_result$;

SELECT employee.emp_no, employee.position_code, employee.hire_date,
       extract(year FROM age(employee.hire_date, person.birth_date))::integer AS age_at_hire
FROM employees AS employee
JOIN employee_date_fixture AS fixture USING (emp_no)
JOIN persons AS person USING (person_id)
ORDER BY employee.emp_no;

\if :preview
ROLLBACK;
\echo 'Preview finished; no changes saved.'
\else
COMMIT;
\echo 'Updated existing test employee birth/hire dates.'
\endif
